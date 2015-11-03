from django.utils import timezone
from djes.models import Indexable

from elasticsearch_dsl import aggs
from elasticsearch_dsl.filter import Term, Range, MatchAll, Nested, Missing


class Searchable(Indexable):
    """adds a `.search` class method to the model
    """

    class Meta(object):
        abstract = True

    @staticmethod
    def _handle_status_filter(status):
        """builds a filter around the `published` field based on a given status

        :param status: published|scheduled|draft indicator
        :type status: str

        :return: a filter to set a time range around `published`
        :rtype: elasticsearch_dsl.filter.F
        """
        # build empty filter; set epoch
        f = MatchAll()
        now = timezone.now()

        # match published
        if status.lower() == "published":
            f &= Range(published={"lte": now})

        # match scheduled
        elif status.lower() == "scheduled":
            f &= Range(published={"gte": now})

        # match draft
        elif status.lower() == "draft":
            f &= Missing(field="published")

        # done
        return f

    @classmethod
    def _build_filters(cls, filters):
        """builds filters for all passed key-values

        :param filters: key-value pairs of field name keys and filter term values
        :type filters: dict

        :return: a compounded filter
        :rtype: elasticsearch_dsl.filter.F
        """
        # build empty filter; iterate filters dict
        f = MatchAll()
        for key, value in filters.items():

            # handle status meta filtering
            if key.lower() == "status":
                status_filter = cls._handle_status_filter(value)
                f &= status_filter

            # handle nested filtering -- convert dunders to dots
            elif "__" in key or "." in key:
                nested_key = key.lower().replace("__", ".")
                path = nested_key.split(".")[0]
                f &= Nested(path=path, filter=Term(**{nested_key: value}))

            # regular term filter
            else:
                key = key.lower()
                f &= Term(**{key: value})

        # done
        return f

    @classmethod
    def _build_ordering(cls, ordering):
        """builds the ordering list and properly converts dunders to dots for nested fields

        :param ordering: field names used to order the results
        :type ordering: list

        :return: a proper list of field names
        :rtype: list
        """
        if isinstance(ordering, str):
            ordering = [ordering, ]

        formatted = []
        for key in ordering:
            nested_key = key.lower().replace("__", ".")
            formatted.append(nested_key)

        return formatted

    @classmethod
    def search(cls, query=None, filters=None, ordering=None):
        """performs a query using the model's `.search_objects` manager

        :param query: terms used to perform query
        :type query: str

        :param filters: key-value pairs used to build filters to limit search results
        :type filters: dict

        :param ordering: field names used to order the results
        :type ordering: list

        :return: elasticsearch search results mapped to django model proxies
        :rtype: django.db.models.QuerySet
        """
        # build initial query set
        qs = cls.search_objects.search()

        # add query if exists
        if query:
            qs = qs.query("match", _all=query)

        # add filters if exist
        if filters:
            built_filters = cls._build_filters(filters)
            qs = qs.filter(built_filters)

        # add ordering if exists
        if ordering:
            ordering = cls._build_ordering(ordering)
            qs = qs.sort(*ordering)

        # done
        return qs


class Aggregateable(Searchable):
    """extends the Searchable model type by adding a `.get_aggregates` class method to the model
    """

    class Meta(object):
        abstract = True

    class Aggregates(object):
        """this is where you need to load up your aggregates
        """
        # channel = {
        #     "path": "channel",
        #     "field": "channel.name.raw"
        # }
        pass

    @classmethod
    def _get_aggregate_declarations(cls):
        """parsed an internal Aggregates subclass to help build aggregate declarations

        :return: a list of bucket names and mapping dictionaries tuples
        :rtype: list
        """
        # check for an Aggregates subclass
        if not hasattr(cls, "Aggregates"):
            raise Exception("You must explicitly set an `Aggregates` subclass")

        # get fields
        agg_mapping_fields = [field for field in dir(cls.Aggregates) if not field.startswith("_")]

        # init container; iterate field names; append to container
        agg_mappings = []
        for field in agg_mapping_fields:
            declarations = getattr(cls.Aggregates, field)
            agg_mappings.append((field, declarations))

        # done
        return agg_mappings

    @classmethod
    def _build_aggregates(cls, qs):
        """builds aggregates onto a queryset

        :param qs: elasticsearch search results mapped to django model proxies
        :type qs: django.db.models.QuerySet

        :return: the updated query, a list of bucket names, and a list of paths
        :rtype: tuple
        """
        # get declarations; init containers
        agg_mappings = cls._get_aggregate_declarations()
        names = []
        fields = []

        # iterate declarations
        for name, mapping in agg_mappings:
            try:
                # parse mapping
                path = mapping["path"]
                field = mapping["field"]

                # bolt on aggregate to query
                qs.aggs.bucket(
                    name,
                    aggs.Nested(
                        path=path,
                        aggs={path: aggs.Terms(field=field)}
                    )
                )

                # append values to parse later
                names.append(name)
                fields.append(field)

            # they messed up the subclass
            except KeyError:
                raise Exception("Misconfigured aggregate declaration: {}, {}".format(name, mapping))

        # done
        return qs, names, fields

    @classmethod
    def get_aggregates(cls, query=None, filters=None):
        """performs an aggregation query using the model's `.search` class method

        :param query: terms used to perform query
        :type query: str

        :param filters: key-value pairs used to build filters to limit search results
        :type filters: dict

        :return: a dictionary of field keys and value/count mapped dictionary values
        :rtype: dict
        """
        # get initial query set
        qs = cls.search(query, filters)

        # build aggregates
        qs, buckets, fields = cls._build_aggregates(qs)

        # execute
        raw_aggregates = qs.execute().aggregations

        # parse
        aggregates = {}
        for index, field in enumerate(fields):
            dunder_field = field.lower().replace(".", "__")
            if filters:
                if dunder_field in filters:
                    continue
            bucket = buckets[index]
            parsed_aggregates = dict([(b["key"], b["doc_count"]) for b in raw_aggregates[bucket][bucket]["buckets"]])
            aggregates[dunder_field] = parsed_aggregates

        # done
        return aggregates
