from django.conf.urls import patterns, url, include

from example.app.routers import router


urlpatterns = patterns(
    "",
    url(r"api/", include(router.urls, namespace="api")),
)
