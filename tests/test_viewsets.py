import json

from django.core import management
from model_mommy import mommy
import pytest

from example.app.models import Channel, Video


@pytest.mark.django_db
def test_searchable(client):
    management.call_command("sync_es")
    _ = mommy.make(Channel, _quantity=10)
    response = client.get("/api/channels/")
    results = json.loads(response.content.decode("utf8"))
    assert len(results) == 10


@pytest.mark.django_db
def test_aggregateable(client):
    management.call_command("sync_es")
    c1 = mommy.make(Channel)
    c2 = mommy.make(Channel)
    c3 = mommy.make(Channel)
    _ = mommy.make(Video, channel=c1)
    _ = mommy.make(Video, channel=c2)
    _ = mommy.make(Video, channel=c3)
    response = client.get("/api/videos/aggregates/")
    results = json.loads(response.content.decode("utf8"))
    assert len(results["results"]) == 1
    assert len(results["results"][0]["aggregates"])
