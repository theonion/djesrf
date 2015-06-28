# `djesrf` Quickstart


## Python Versions

`djesrf` is tested using

* Python 2.7
* Python 3.2
* Python 3.4

We currently do not support Python versions <2.6 and there is no official support for 3.3 (although it will more than 
likely work with 3.3).


## Requirements

`djesrf` requires

* [`djes`](https://github.com/theonion/djes)
* [`djangorestframework`](https://github.com/tomchristie/django-rest-framework)

Each has their own set of dependencies, but these are the only two required to run this.


## Installation

You can install `djesrf` from PyPI using `pip`

```
$ pip install djesrf
```

Next, add the dependencies to your `INSTALLED_APPS` in your project settings

```
INSTALLED_APPS = (
    ...
    "djes",
    "djesrf",
)
```

__NOTE:__ `djes` must be present in your `INSTALLED_APPS` for full compatibility - there are signals and some excellent 
management commands in there that you'll want to have!

`djesrf` uses the underlying configurations of `djes`, therefore it tries to connect to an Elasticsearch instance 
running at `localhost:9200` by default. To configure this, you can set up `ES_CONNECTIONS` in your settings


```
ES_CONNECTIONS = {
    "default": {
        "hosts": "192.168.1.143:9200"
    }
}
```


## Indexing Your Models

To have your models mapped to Elasticsearch and have your records indexed to that mapping, your models must inherit 
from `djes.models.Indexable`, `djesrf.models.Searchable` or `djesrf.models.Aggregateable`. Here's a super 
contrived example

```
from django.db import models
from djes.models import Indexable
from djesrf.models import Searchable, Aggregateable
from elasticsearch_dsl import field


class Tag(Indexable):
    name = models.CharField(max_length=255)
    
    class Mapping(object):  # see djes documentation for more info
        pass


class Author(Searchable):
    full_name = models.CharField(max_length=500)
    
    class Mapping(object):
        full_name = field.String(
            analyzer="snowball",
            _boost=2.0,
            fields={
                "raw": field.String(index="not_analyzed"),
                "autocomplete": field.String(analyzer="autocomplete"),
            })


class Book(Aggregateable):
    title = models.CharField(max_length=255)
    isbn = models.CharField(max_length=255)
    author = models.ForeignKey(Author, related_name="books") 
    tags = models.ManyToManyField(Tag)
    
    class Mapping(object):
        title = field.String(
            analyzer="snowball",
            _boost=2.0,
            fields={
                "raw": field.String(index="not_analyzed"),
                "autocomplete": field.String(analyzer="autocomplete"),
            })
    
    class Aggregates(object):  # explained later
        author = {
            "name": "author",
            "path": "author.full_name.raw"
        }
```

The difference between the three will be explained below.
 

## Synchronizing Your Model Mappings

To sync up your models as Elasticsearch mappings (assuming you've implemented the above mapping pattern)

```
$ python manage.py sync_es
```

This will establish mappings in Elasticsearch as `{app name}_{model name}` and the Indexable model has signals 
that will automatically update and delete documents when you perform comparable actions in Django.


## Searching

The `Searchable` model provides a `search` classmethod for your models. To use it, all you need to do is

```
results = YourSearchableModel.search("query terms")
```

The search results will be _shallow copies_ of Django models - you will be able to operate on them as you would a 
normal Django ORM generated QuerySet.

Given that, searches can also be filtered and ordered. Any field that you have set up in the mapping can be filtered 
against and used for ordering. 

Filters are applied as a dictionary and ordering is a list of field names optionally prefixed with `-` to denote 
descending order of that field.

```
results = YourSearchableModel.search("query", {"field_name": "filter terms"}, ["another_field", "-yet_another_field"])
```

### Nested Fields

Since `djesrf` relies on `djes` and `django-rest-framework`, nested fields can be used for filtering and ordering using 
the Django _dunder_ (double underscore) pattern to access those fields.

Using our above example of `Author` and `Book`, you could filter the books by the author's `full_name` field via

```
books = Book.search("query", {"author__full_name": "their name"})
```


## Aggregating

The `Aggregatable` model extends the `Searchable` model (so you can still `search`) and provides a 
`get_aggregates` classmethod for your models.

### Setting Up Aggregates

Aggregates are best used in cases of `ForeignKey` and `ManyToMany` fields. 

To fully establish an `Aggregateable` model, you must provide an `Aggregates` subclass within the model. The 
`Aggregates` subclass informs the `get_aggregates` method of what buckets it needs to create.

The `name` value is the name of the bucket that will be returned to you when the method executes.

The `path` value is an Elasticsearch dotted path to the field you will be aggregating.

In our example, we want to aggregate a `book`'s `author` field, but we want to return values of the `author`'s 
full name stored in its `raw` subfield.

### Executing Aggregation

Aggregates can be had by simply using the `get_aggregates` class method. This will return all aggregates that 
were set up in the `Aggregates` definition.

```
aggs = Book.get_aggregates()
```

The returned object will be a dictionary with `path` keys and dictionary values. The dictionary values will have 
aggregate value keys and document count values.

```
{
    "author.name.raw": {
        "Some Author": 5,
        "Another Author": 3,
        ...
    }
}
```

### Filtering and Querying

Aggregates can be generated from full queries as well. You can optionally apply `query` and `filters` to the 
`get_aggregates` method to perform a query first and then generate available aggregates from those results.

```
aggs = YourAggregateableModel.get_aggregates("whatever", {"some_field": "filter terms"})
```


## Using the View Sets

`djesrf` provides two view sets that correspond to its two base models: `SearchableModelViewSet` and 
`AggregateableModelViewSet`. These view sets extend the base drf view set `ModelViewSet`.

Both view sets require that you provide an additional `model` attribute to the view set declaration.

```
# serializers.py
from nested_serializers import NestedModelSerializer
from rest_framework import serializers

from .models import Channel, Video


class ChannelSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = Channel


class VideoSerializer(NestedModelSerializer):
    class Meta(object):
        model = Video
        depth = 1


# views.py
from djesrf.viewsets import SearchableModelViewSet, AggregateableModelViewSet

from .models import Channel, Video
from .serializers import ChannelSerializer, VideoSerializer


class ChannelViewSet(SearchableModelViewSet):
    model = Channel
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer


class VideoViewSet(AggregateableModelViewSet):
    model = Video
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
```

All results of the endpoints will follow the usual `django-rest-framework` style: lists will have `count`, `next`, 
`previous` and `results` keys; detail endpoints will use the ORM as the source of truth; and so forth.

### Using `SearchableModelViewSet`

`SearchableModelViewSet` does all the things that the base view set does with the exception that the list 
endpoint uses Elasticsearch to drive its results.

#### Filtering

Filtering is applied using the _dunder_ method as described in the above searching and aggregating sections

```
curl '/api/books/?author__full_name__raw=Their+Name'
```

You can apply as many filters as necessary.

#### The `status` Meta Filter

The Onion uses a publishing pattern for its content, and thus it has been baked into the filters as well. `status` is 
a meta key that is used to handle content in its various states of publishing. Valid keys are `published`, 
`scheduled` and `draft`.

```
curl '/api/books/?status=published'
```

__NOTE:__ if there's a significant blow back from this, this may become deprecated in the future, but for now it 
makes our lives easier in house :\

#### The `search` Meta Filter

Searches can be performed using the `search` filter key

```
curl '/api/books/?search=python'
```

#### The `ordering` Meta Filter
 
Ordering can be applied using the `ordering` filter key
 
```
curl '/api/books/?ordering=-isbn'
```

### Using `AggregateableModelViewSet`

`AggregateableModelViewSet` does all the same things the `SearchableModelViewSet` does and provides an additional 
`/aggregates/` endpoint to obtain aggregates.

The additional endpoint allows for the same functionality as the normal list endpoint.

For example, if you had an API endpoint named `/api/books/`, there would be an additional `/api/books/aggregates/` 
endpoint available if you implemented the view set.
