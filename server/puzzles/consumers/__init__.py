import logging
import platform
from urllib.parse import parse_qs

from asgiref.sync import async_to_sync, sync_to_async
from tph.constants import IS_PYODIDE

if IS_PYODIDE:
    from puzzles.consumers.pyodide_consumer import (
        PyodideJsonWebsocketConsumer as JsonWebsocketConsumer,
    )
    from puzzles.consumers.pyodide_consumer import get_sync_channel_layer
    from tph.utils import sync_indexeddb

    channel_layer = get_sync_channel_layer()
else:
    from channels.generic.websocket import JsonWebsocketConsumer
    from channels.layers import get_channel_layer

    class SyncChannelLayerWrapper:
        def __init__(self, channel_layer):
            self.channel_layer = channel_layer

        async def group_add(self, *args, **kwargs):
            return await self.channel_layer.group_add(*args, **kwargs)

        async def group_send(self, *args, **kwargs):
            return await self.channel_layer.group_send(*args, **kwargs)

        @async_to_sync
        async def sync_group_add(self, *args, **kwargs):
            return await self.group_add(*args, **kwargs)

        @async_to_sync
        async def sync_group_send(self, *args, **kwargs):
            return await self.group_send(*args, **kwargs)

    channel_layer = SyncChannelLayerWrapper(get_channel_layer())

logger = logging.getLogger(__name__)


class ClientConsumer(JsonWebsocketConsumer):
    @staticmethod
    def get_user_group(user=None, *, id=None):
        if id is None:
            if user is None:
                raise ValueError("must provide user or id")
            if not user.is_authenticated:
                return None
            id = user.pk
        return f"user.{id}"

    @staticmethod
    def get_puzzle_group(user=None, slug=None, *, id=None):
        if id is None:
            if user is None:
                raise ValueError("must provide user or id")
            if not user.is_authenticated:
                return None
            id = user.pk
        if slug is None:
            return None
        return f"user.{id}.puzzle.{slug}"

    @staticmethod
    def get_uuid_group(user=None, uuid=None, *, id=None):
        if id is None:
            if user is None:
                raise ValueError("must provide user or id")
            if not user.is_authenticated:
                return f"anonymoususer.uuid.{uuid}"
            id = user.pk
        if uuid is None:
            return None
        return f"user.{id}.uuid.{uuid}"

    def connect(self):
        self.channel_layer = SyncChannelLayerWrapper(self.channel_layer)
        self.user = self.scope["user"]
        self.puzzle_slug = self.scope["url_route"]["kwargs"].get("puzzle")
        qs = parse_qs(self.scope["query_string"])
        try:
            self.uuid = parse_qs(self.scope["query_string"])[b"uuid"][0].decode("utf-8")
        except:
            self.uuid = None

        # NB: use user id instead of team id to avoid an extra sync ORM query
        self.user_group = self.get_user_group(self.user)
        self.puzzle_group = self.get_puzzle_group(self.user, self.puzzle_slug)
        self.uuid_group = self.get_uuid_group(self.user, self.uuid)

        if self.user_group is not None:
            self.channel_layer.sync_group_add(self.user_group, self.channel_name)
        if self.puzzle_group is not None:
            self.channel_layer.sync_group_add(self.puzzle_group, self.channel_name)
        if self.uuid_group is not None:
            self.channel_layer.sync_group_add(self.uuid_group, self.channel_name)

        self.accept()

    def handle_event(self, e):
        self.send_json(e["event"])

    def receive_json(self, content, *, puzzle_slug_override=None):
        # NB: import here instead of top of file to avoid circular imports.
        PUZZLE_HANDLERS = {
            # "sample": puzzle.process_data,
        }

        puzzle_slug = puzzle_slug_override or self.puzzle_slug
        if puzzle_slug in PUZZLE_HANDLERS:
            result = PUZZLE_HANDLERS[puzzle_slug](self.user, self.uuid, content)
            if IS_PYODIDE:
                sync_indexeddb()
            if result is not None:
                self.send_json(
                    {
                        "key": puzzle_slug,
                        "data": result,
                    }
                )
        else:
            logger.warning(
                "Received websocket data but no handler for puzzle %s exists",
                puzzle_slug,
            )

    @staticmethod
    def send_event(group, key, data):
        """
        Method to send data from outside to a channels group.
        Parameters:
        group: Identifier from get_user_group(user), get_puzzle_group(user, slug),
            or get_uuid_group(user, uuid). If you have a Team object, you can use
            team.user.
        key: A key to allow for filtering on the client side (but only this
            team will receive this message).
        data: A json serilizable object.
        """
        channels_data = {
            "type": "handle.event",
            "event": {
                "key": key,
                "data": data,
            },
        }
        channel_layer.sync_group_send(group, channels_data)

    @staticmethod
    async def async_send_event(group, key, data):
        channels_data = {
            "type": "handle.event",
            "event": {
                "key": key,
                "data": data,
            },
        }
        await channel_layer.group_send(group, channels_data)
