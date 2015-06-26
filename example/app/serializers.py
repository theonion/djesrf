from nested_serializers import NestedModelSerializer
from rest_framework import serializers

from example.app.models import Channel, Video


class ChannelSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = Channel


class VideoSerializer(NestedModelSerializer):
    class Meta(object):
        model = Video
        depth = 1
