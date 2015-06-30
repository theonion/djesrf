import json

from django.core import management
from model_mommy import mommy
import pytest
from six import string_types

from example.app.models import Channel, Video


class Response(object):
    def __init__(self, wsgi_response):
        self.status = wsgi_response.status_code
        self._parsed_response = json.loads(wsgi_response.content.decode("utf8"))
        self.count = self._parsed_response.get("count")
        self.next = self._parsed_response.get("next")
        self.previous = self._parsed_response.get("previous")
        self.results = self._parsed_response.get("results")


@pytest.mark.django_db
def test_searchable_result_keys(client):
    management.call_command("sync_es")
    _ = mommy.make(Channel, _quantity=10)
    response = client.get("/api/channels/")
    response = Response(response)
    assert response.status == 200
    assert response.count is not None
    assert response.next is None or isinstance(response.next, string_types)
    assert response.previous is None or isinstance(response.previous, string_types)
    assert isinstance(response.results, list)


@pytest.mark.django_db
def test_searchable_simple_search(client):
    management.call_command("sync_es")
    onion = mommy.make(Channel, name="The Onion")
    _ = mommy.make(Channel, _quantity=20)
    response = client.get("/api/channels/?search=The+Onion")
    response = Response(response)
    assert response.count == 1
    assert response.results[0]["name"] == onion.name


@pytest.mark.django_db
def test_searchable_filtered_search(client):
    management.call_command("sync_es")
    onion = mommy.make(Channel, name="The Onion")
    avc = mommy.make(Channel, name="The A.V. Club")
    _ = mommy.make(Video, channel=onion, _quantity=20)
    _ = mommy.make(Video, channel=avc, _quantity=10)
    response = client.get("/api/videos/?channel__name__raw=The+Onion")
    response = Response(response)
    assert response.count == 20


@pytest.mark.django_db
def test_searchable_ordered_search(client):
    management.call_command("sync_es")
    _ = mommy.make(Channel, _quantity=10)
    response = client.get("/api/channels/?ordering=-name")
    response = Response(response)
    current_result = response.results[0]
    for result in response.results[1:]:
        assert current_result["name"].lower() >= result["name"].lower()
        current_result = result


@pytest.mark.django_db
def test_aggregateable_result_keys(client):
    management.call_command("sync_es")
    channel = mommy.make(Channel)
    _ = mommy.make(Video, channel=channel, _quantity=5)
    response = client.get("/api/videos/aggregates/")
    response = Response(response)
    assert response.status == 200
    assert response.count is not None
    assert response.next is None or isinstance(response.next, string_types)
    assert response.previous is None or isinstance(response.previous, string_types)
    assert isinstance(response.results, list)


@pytest.mark.django_db
def test_aggregateable_simple_aggregates(client):
    management.call_command("sync_es")
    onion = mommy.make(Channel, name="The Onion")
    avc = mommy.make(Channel, name="The A.V. Club")
    _ = mommy.make(Video, channel=onion, _quantity=20)
    _ = mommy.make(Video, channel=avc, _quantity=10)
    response = client.get("/api/videos/aggregates/")
    response = Response(response)
    assert response.count == 1
    agg_group = response.results[0]
    assert isinstance(agg_group, dict)
    assert "name" in agg_group
    assert "path" in agg_group
    assert "aggregates" in agg_group
