from django.core import management
from django.utils import timezone

import pytest
from elasticsearch_dsl.connections import connections
from model_mommy import mommy

from example.app.models import Channel, Video


@pytest.mark.django_db
def test_searchable_has_search():
    management.call_command("sync_es")
    channel = mommy.make(Channel)
    assert hasattr(channel, "search")


@pytest.mark.django_db
def test_searchable_simple_search():
    management.call_command("sync_es")
    onion = mommy.make(Channel, name="The Onion")
    _ = mommy.make(Channel, _quantity=20)
    results = Channel.search(query="onion")
    assert len(results) == 1
    assert results[0].name == onion.name


@pytest.mark.django_db
def test_searchable_filtered_search():
    management.call_command("sync_es")
    onion = mommy.make(Channel, name="The Onion")
    avc = mommy.make(Channel, name="The A.V. Club")
    _ = mommy.make(Video, channel=onion, _quantity=20)
    _ = mommy.make(Video, channel=avc, _quantity=10)
    Video.search_objects.refresh()
    results = Video.search(filters={"channel__name__raw": onion.name})
    assert len(results) == 20


@pytest.mark.django_db
def test_searchable_ordered_search():
    management.call_command("sync_es")
    _ = mommy.make(Channel, _quantity=10)
    results = Channel.search(ordering=["-name", ])
    current_result = results[0]
    for result in results[1:]:
        assert current_result.name.lower() >= result.name.lower()
        current_result = result


@pytest.mark.django_db
def test_searchable_complete_search():
    management.call_command("sync_es")
    onion = mommy.make(Channel, name="The Onion")
    avc = mommy.make(Channel, name="The A.V. Club")
    video = mommy.make(Video, channel=onion, name="Some Test Video")
    _ = mommy.make(Video, channel=onion, _quantity=20)
    _ = mommy.make(Video, channel=avc, _quantity=10)
    results = Video.search(
        query="test video",
        filters={"channel__name__raw": onion.name},
        ordering=["-name"]
    )
    assert len(results) > 0
    current_result = results[0]
    assert current_result.name == video.name
    for result in results[1:]:
        assert current_result.name.lower() >= result.name.lower()
        current_result = result


@pytest.mark.django_db
def test_searchable_delete_object_es(client):
    management.call_command("sync_es")
    es = connections.get_connection('default')
    onion = mommy.make(Channel, name="The Onion")
    index = Channel.search_objects.mapping.index
    doc_type = Channel.search_objects.mapping.doc_type
    channel_id_query = {
        "query": {
            "ids": {
                "values": [onion.id]
            }
        }
    }
    Channel.search_objects.refresh()
    results = es.search(index=index, doc_type=doc_type, body=channel_id_query)
    hits = results['hits']['hits']
    assert len(hits) == 1
    onion.delete()
    Channel.search_objects.refresh()
    results = es.search(index=index, doc_type=doc_type, body=channel_id_query)
    hits = results['hits']['hits']
    assert len(hits) == 0


@pytest.mark.django_db
def test_aggregateable_has_search():
    management.call_command("sync_es")
    video = mommy.make(Video)
    assert hasattr(video, "search")


@pytest.mark.django_db
def test_aggregateable_has_get_aggregates():
    management.call_command("sync_es")
    video = mommy.make(Video)
    assert hasattr(video, "get_aggregates")


@pytest.mark.django_db
def test_aggregateable_get_aggregates_simple():
    management.call_command("sync_es")
    _ = mommy.make(Channel, _quantity=3)
    results = Video.get_aggregates()
    assert len(results) == 1
    assert "channel__name__raw" in results
    assert len(results["channel__name__raw"]) == 3


@pytest.mark.django_db
def test_aggregateable_get_aggregates_with_query():
    management.call_command("sync_es")
    onion = mommy.make(Channel, name="The Onion")
    avc = mommy.make(Channel, name="The A.V. Club")
    _ = mommy.make(Video, channel=onion, name="Another Test Video")
    _ = mommy.make(Video, channel=onion, _quantity=5)
    _ = mommy.make(Video, channel=avc, _quantity=5)
    Video.search_objects.refresh()
    results = Video.get_aggregates(query="test video")
    assert results == {
        "channel__name__raw": {
            "The Onion": 1
        }
    }


@pytest.mark.django_db
def test_aggregateable_get_aggregates_with_filters():
    management.call_command("sync_es")
    onion = mommy.make(Channel, name="The Onion")
    avc = mommy.make(Channel, name="The A.V. Club")
    _ = mommy.make(Video, channel=onion, name="Another Test Video")
    _ = mommy.make(Video, channel=onion, _quantity=5)
    _ = mommy.make(Video, channel=avc, _quantity=5)
    results = Video.get_aggregates(filters={"channel__name__raw": "barf"})
    assert results == {}


@pytest.mark.django_db
def test_aggregateable_get_aggregates_complete():
    management.call_command("sync_es")
    onion = mommy.make(Channel, name="The Onion")
    avc = mommy.make(Channel, name="The A.V. Club")
    for index in range(10):
        _ = mommy.make(Video, channel=onion, name="Looped Video {}".format(index))
    _ = mommy.make(Video, channel=onion, _quantity=5)
    for index in range(10):
        _ = mommy.make(Video, channel=avc, name="Looped Video {}".format(index+100))
    results = Video.get_aggregates(
        query="looped",
        filters={"channel__name__raw": onion.name}
    )
    assert len(results) == 0


@pytest.mark.django_db
def test_aggregateable_delete_object_es(client):
    management.call_command("sync_es")
    es = connections.get_connection('default')
    onion = mommy.make(Channel, name="The Onion")
    video = mommy.make(Video, published=timezone.now(), channel=onion, _quantity=1)
    index = Video.search_objects.mapping.index
    doc_type = Video.search_objects.mapping.doc_type
    video_id_query = {
        "query": {
            "ids": {
                "values": [video[0].id]
            }
        }
    }
    Video.search_objects.refresh()
    results = es.search(index=index, doc_type=doc_type, body=video_id_query)
    hits = results['hits']['hits']
    assert len(hits) == 1
    video[0].delete()
    Video.search_objects.refresh()
    results = es.search(index=index, doc_type=doc_type, body=video_id_query)
    hits = results['hits']['hits']
    assert len(hits) == 0
