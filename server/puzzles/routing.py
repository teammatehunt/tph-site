from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"^ws/events$", consumers.ClientConsumer.as_asgi()),
    re_path(r"^ws/puzzles/(?P<puzzle>[\w-]+)$", consumers.ClientConsumer.as_asgi()),
]
