from django.core import management
import pytest
from model_mommy import mommy

from example.app.models import Channel, Video


@pytest.mark.django_db
def test_searchable_model_has_search():
    management.call_command("sync_es")
    channel = mommy.make(Channel)
    assert hasattr(channel, "search")


@pytest.mark.django_db
def test_aggregateable_model_has_search():
    management.call_command("sync_es")
    video = mommy.make(Video)
    assert hasattr(video, "search")


@pytest.mark.django_db
def test_aggregateable_model_has_get_aggregates():
    management.call_command("sync_es")
    video = mommy.make(Video)
    assert hasattr(video, "get_aggregates")


@pytest.mark.django_db
def test_searchable_model_simple_search():
    management.call_command("sync_es")
    onion = mommy.make(Channel, name="The Onion")
    avc = mommy.make(Channel, name="The A.V. Club")
    results = Channel.search(query="onion")
    assert len(results) == 1
    assert results[0].name == onion.name
