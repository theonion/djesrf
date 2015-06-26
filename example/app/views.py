from djesrf.viewsets import SearchableModelViewSet, AggregateableModelViewSet

from example.app.models import Channel, Video
from example.app.serializers import ChannelSerializer, VideoSerializer


class ChannelViewSet(SearchableModelViewSet):
    model = Channel
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer


class VideoViewSet(AggregateableModelViewSet):
    model = Video
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
