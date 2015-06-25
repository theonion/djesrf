from django.db import models
from django.template.defaultfilters import slugify
from elasticsearch_dsl import field

from djesrf.models import Searchable, Aggregateable


class Channel(Searchable):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255)

    class Mapping(object):
        name = field.String(
            analyzer="snowball",
            _boost=2.0,
            fields={
                "raw": field.String(index="not_analyzed"),
                "autocomplete": field.String(analyzer="autocomplete"),
            })

    def save(self, index=True, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Channel, self).save(index, *args, **kwargs)


class Video(Aggregateable):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255)
    published = models.DateTimeField(null=True, blank=True, default=None)
    channel = models.ForeignKey(Channel, related_name="videos")

    class Mapping(object):
        name = field.String(
            analyzer="snowball",
            _boost=2.0,
            fields={
                "raw": field.String(index="not_analyzed"),
                "autocomplete": field.String(analyzer="autocomplete"),
            })

    class Aggregates(object):
        channel = {
            "path": "channel",
            "field": "channel.name.raw"
        }

    def save(self, index=True, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Video, self).save(index, *args, **kwargs)
