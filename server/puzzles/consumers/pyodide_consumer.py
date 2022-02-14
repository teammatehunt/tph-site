"AsyncJsonWebsocketConsumer replacement for Pyodide"
import functools

from django.contrib.auth.models import User, AnonymousUser
import js
import pyodide


class PyodideJsonWebsocketConsumer:
    def __init__(self):
        self.uuid = "default"
        self.user = User.objects.filter(username="default").first() or AnonymousUser()
        self.puzzle_slug = None

    def send_json(self, data):
        get_sync_channel_layer().broadcast(data)


class ChannelLayer:
    def __init__(self):
        self.broadcast_channel = js.globalThis.broadcastChannel

    def sync_group_add(self, group, channel_name):
        pass

    # ignore groups and just broadcast all messages
    def sync_group_send(self, group, channels_data):
        self.broadcast(channels_data["event"])

    def broadcast(self, data):
        js_data = pyodide.to_js(data, dict_converter=js.Object.fromEntries)
        self.broadcast_channel.postMessage(js_data)


@functools.lru_cache(maxsize=1)
def get_sync_channel_layer():
    return ChannelLayer()
