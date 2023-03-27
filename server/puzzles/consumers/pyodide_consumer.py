"AsyncJsonWebsocketConsumer replacement for Pyodide"
import functools
import urllib.parse

import js
import pyodide

from tph.utils import POSTHUNT_USERNAME


class PyodideAsyncJsonWebsocketConsumer:
    def __init__(self):
        self.channel_layer = get_channel_layer()
        self.channel_name = "local_channel_singleton"

    async def setup(self, url):
        # simulate setting necessary scope variables set by django for real requests
        route_kwargs = {}
        result = urllib.parse.urlparse(url)
        # parse out slug (following websocket routes in puzzles.routing)
        path_parts = result.path.split("/")
        if len(path_parts) >= 2 and path_parts[-2] in ("puzzles", "story"):
            route_kwargs["slug"] = path_parts[-1]
        self.scope = {
            # query_string is bytes but the rest are str
            "query_string": result.query.encode(),
            "path": result.path,
            "url_route": {
                "kwargs": route_kwargs,
            },
        }
        await self.connect()

    async def send_json(self, data, **kwargs):
        get_sync_channel_layer().broadcast(data)

    async def connect(self):
        pass

    async def accept(self):
        pass


class ChannelLayer:
    def __init__(self):
        self.broadcast_channel = js.globalThis.broadcastChannel

    async def group_add(self, group, channel_name):
        pass

    async def group_discard(self, group, channel_name):
        pass

    # ignore groups and just broadcast all messages
    async def group_send(self, group, channels_data):
        data = {
            "group": group,
            "event": channels_data["event"],
        }
        await self.broadcast(data)

    async def broadcast(self, data):
        js_data = pyodide.ffi.to_js(data, dict_converter=js.Object.fromEntries)
        self.broadcast_channel.postMessage(js_data)


@functools.lru_cache(maxsize=1)
def get_channel_layer():
    return ChannelLayer()
