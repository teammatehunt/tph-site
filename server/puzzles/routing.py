from channels.routing import URLRouter
from django.conf import settings
from django.urls import path, re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"^ws/events$", consumers.ClientConsumer.as_asgi()),
    re_path(r"^ws/puzzles/(?P<slug>[^//]+)$", consumers.ClientConsumer.as_asgi()),
    re_path(r"^ws/story/(?P<slug>[^//]+)$", consumers.ClientConsumer.as_asgi()),
]
