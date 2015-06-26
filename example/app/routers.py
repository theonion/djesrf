from rest_framework.routers import DefaultRouter

from example.app.views import ChannelViewSet, VideoViewSet


router = DefaultRouter()
router.register("channels", ChannelViewSet, "channel")
router.register("videos", VideoViewSet, "video")
