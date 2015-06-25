from copy import deepcopy

from rest_framework import viewsets, status
from rest_framework.decorators import list_route
from rest_framework.response import Response

from djesrf.models import Searchable, Aggregateable


class SearchableModelViewSet(viewsets.ModelViewSet):
    """moves all list functionality to Elasticsearch and off the ORM
    """

    model = object

    def __init__(self, **kwargs):
        if not issubclass(self.model, Searchable):
            raise Exception("You must explicitly supply a `model` attribute of this viewset "
                            "and it must subclass `djesrf.models.Searchable`")
        super(SearchableModelViewSet, self).__init__(**kwargs)

    def list(self, request, *args, **kwargs):
        # get params
        params = deepcopy(request.QUERY_PARAMS)

        if "search" in params:
            query = params["search"]
            del params["search"]
        else:
            query = None

        if "ordering" in params:
            ordering = params["ordering"]
            del params["ordering"]
        else:
            ordering = None

        if "page" in params:
            del params["page"]

        if "page_size" in params:
            del params["page_size"]

        results = self.model.search(query, params, ordering)

        page = self.paginate_queryset(results)
        if page:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data)


class AggregateableModelViewSet(SearchableModelViewSet):

    def __init__(self, **kwargs):
        if not issubclass(self.model, Aggregateable):
            raise Exception("You must explicitly supply a `model` attribute of this viewset "
                            "and it must subclass `djesrf.models.Aggregateable`")
        super(AggregateableModelViewSet, self).__init__(**kwargs)

    @list_route(methods=["get"])
    def aggregates(self, request):
        # get params
        params = deepcopy(request.QUERY_PARAMS)

        if "search" in params:
            query = params["search"]
            del params["search"]
        else:
            query = None

        if "ordering" in params:
            del params["ordering"]

        if "page" in params:
            del params["page"]

        if "page_size" in params:
            del params["page_size"]

        results = self.model.get_aggregates(query, params)

        response = {
            "count": len(results),
            "next": None,
            "previous": None,
            "results": [],
        }

        for path, obj in results.items():
            name = path.split(".")[0].title()
            path = path.replace(".", "__")
            result = {
                "name": name,
                "path": path,
                "aggregates": [],
            }
            for value, count in obj.items():
                result["aggregates"].append({"value": value, "count": count})
            response["results"].append(result)
        return Response(response)
