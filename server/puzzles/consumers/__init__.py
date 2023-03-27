import asyncio
import functools
import gzip
import logging
from typing import Mapping, Optional, Type
from urllib.parse import parse_qs

import ujson as json
from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from spoilr.utils import json

from puzzles.utils import get_redis_handle, redis_lock, throttleable_task
from tph.constants import IS_PYODIDE
from tph.utils import get_posthunt_user

from .base import BasePuzzleHandler

logger = logging.getLogger(__name__)

if IS_PYODIDE:
    # TODO: AsyncJsonWebsocketConsumer
    from puzzles.consumers.pyodide_consumer import (
        PyodideAsyncJsonWebsocketConsumer as AsyncJsonWebsocketConsumer,
    )
    from puzzles.consumers.pyodide_consumer import get_channel_layer
    from tph.utils import sync_indexeddb

    channel_layer = get_channel_layer()
else:
    from channels.generic.websocket import AsyncJsonWebsocketConsumer
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()


def run_async_to_sync(coroutine, *args, **kwargs):
    """
    async_to_sync fails if attempted in a running event loop. This takes in the
    args as well and runs immediately in either case.
    """
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        if not loop.is_running():
            loop = None
    if loop is None:
        return async_to_sync(coroutine)(*args, **kwargs)
    else:
        return loop.run_until_complete(coroutine(*args, **kwargs))


class ClientConsumer(AsyncJsonWebsocketConsumer):
    @classmethod
    async def decode_json(cls, text_data):
        # uses ujson instead of json
        return json.loads(text_data)

    @classmethod
    async def encode_json(cls, content):
        # uses ujson instead of json
        return json.dumps(content)

    async def send_json(self, content, close=False, compress_gzip=False):
        """
        Encode the given content as JSON and send it to the client.
        """
        payload = await self.encode_json(content)
        if compress_gzip:
            # level is 1-9, use 2 by default
            level = compress_gzip if isinstance(compress_gzip, int) else 2
            payload = gzip.compress(payload.encode(), level)
            await super().send(bytes_data=payload, close=close)
        else:
            await super().send(text_data=payload, close=close)

    @staticmethod
    def get_team_group(user=None, *, id=None, suffix=None):
        if id is None:
            if user is None:
                raise ValueError("must provide user or id")
            if not user.is_authenticated:
                return None
            if not user.team_id:
                return None
            id = user.team_id
        if suffix:
            return f"team.{id}.{suffix}"
        return f"team.{id}"

    @staticmethod
    def get_puzzle_group(user=None, slug=None, *, id=None):
        if id is None:
            if user is None:
                raise ValueError("must provide user or id")
            if not user.is_authenticated:
                return None
            if not user.team_id:
                return None
            id = user.team_id
        if slug is None:
            return None
        return f"team.{id}.puzzle.{slug}"

    @staticmethod
    def get_subpuzzle_group(user=None, slug=None, subpuzzle=None, *, id=None):
        if id is None:
            if user is None:
                raise ValueError("must provide user or id")
            if not user.is_authenticated:
                return None
            if not user.team_id:
                return None
            id = user.team_id
        if slug is None or subpuzzle is None:
            return None
        return f"team.{id}.puzzle.{slug}.subpuzzle.{subpuzzle}"

    @staticmethod
    def get_uuid_group(user=None, uuid=None, *, id=None):
        if id is None:
            if user is None:
                raise ValueError("must provide user or id")
            if not user.is_authenticated:
                return f"anonymoususer.uuid.{uuid}"
            if not user.team_id:
                return None
            id = user.team_id
        if uuid is None:
            return None
        return f"team.{id}.uuid.{uuid}"

    @staticmethod
    def get_session_group(user=None, session_id=None, *, team_id=None):
        if session_id is None:
            return None
        if team_id is None:
            if user is None:
                raise ValueError("must provide user or team_id")
            if not user.is_authenticated or not user.team_id:
                return None
            team_id = user.team_id
        return f"team.{team_id}.session.{session_id}"

    def get_handler(self, puzzle_slug) -> Optional[Type[BasePuzzleHandler]]:
        SLUG_HANDLERS: Mapping[str, Type[BasePuzzleHandler]] = {
            # FIXME: Add handlers for puzzles and story
        }

        return SLUG_HANDLERS.get(puzzle_slug, None)

    @staticmethod
    def decode_qs(qs, key, as_int=False):
        try:
            value = qs[key][0].decode().replace(".", "")
            if as_int:
                return int(value)
            return value
        except (KeyError, UnicodeError, ValueError):
            return None

    @property
    def group_names(self):
        for attr in (
            "team_group",
            "puzzle_group",
            "subpuzzle_group",
            "uuid_group",
            "session_group",
        ):
            value = getattr(self, attr, None)
            if value is not None:
                yield value

    async def connect(self):
        if settings.IS_POSTHUNT:
            self.user = await sync_to_async(get_posthunt_user)()
        else:
            self.user = self.scope["user"]
        qs = parse_qs(self.scope["query_string"])
        # '.' should not exist in any ids or slugs but validate it anyway
        # because we use it as a separator

        self.uuid = self.decode_qs(qs, b"uuid")

        self.round_slug = self.decode_qs(qs, b"round_slug")

        # Fall back to the url route in puzzles/routing.py
        self.puzzle_slug = self.decode_qs(qs, b"slug") or (
            self.scope["url_route"]["kwargs"].get("slug")
        )
        if self.puzzle_slug is not None and not IS_PYODIDE:
            # Check that the puzzle or story is unlocked
            from puzzles.utils import is_unlocked

            async_is_unlocked = sync_to_async(is_unlocked)

            # NB: .startswith is stricter but would need special posthunt handling
            if "/ws/story" in self.scope["path"]:
                unlocked = await async_is_unlocked(
                    user=self.user, story_slug=self.puzzle_slug
                )
            else:
                unlocked = await async_is_unlocked(
                    user=self.user, puzzle_slug=self.puzzle_slug
                )

            if not unlocked:
                return await self.close()

        self.session_id = self.decode_qs(qs, b"session_id", as_int=True)
        self.subpuzzle = self.decode_qs(qs, b"subpuzzle")

        self.team_group = self.get_team_group(self.user)
        self.puzzle_group = self.get_puzzle_group(self.user, self.puzzle_slug)
        self.subpuzzle_group = self.get_subpuzzle_group(
            self.user, self.puzzle_slug, self.subpuzzle
        )
        self.uuid_group = self.get_uuid_group(self.user, self.uuid)
        self.session_group = self.get_session_group(self.user, self.session_id)

        for group in self.group_names:
            await self.channel_layer.group_add(group, self.channel_name)

        await self.accept()

        # Call handler connect
        handler = self.get_handler(self.puzzle_slug)
        if handler:
            await self.call_handler(
                handler.connect,
                user=self.user,
                uuid=self.uuid,
                slug=self.puzzle_slug,
            )

    async def handle_event(self, e):
        await self.send_json(e["event"])

    async def call_handler(self, handler_fn, compress_gzip=False, **kwargs):
        result = await sync_to_async(handler_fn)(**kwargs)
        if IS_PYODIDE:
            sync_indexeddb()
        if result is not None:
            await self.send_json(
                {
                    "key": kwargs.get("puzzle_slug"),
                    "data": result,
                },
                compress_gzip=compress_gzip,
            )

    async def receive_json(self, content, *, puzzle_slug_override=None):
        # NB: puzzle_slug is a bit of a misnomer since we also use it for story
        # interactions. We assume slugs are unique across the two models.
        puzzle_slug = puzzle_slug_override or self.puzzle_slug
        handler = self.get_handler(puzzle_slug)
        if handler:
            compress_gzip = getattr(handler, "COMPRESS_GZIP", False)
            await self.call_handler(
                handler.process_data,
                user=self.user,
                uuid=self.uuid,
                data=content,
                compress_gzip=compress_gzip,
                puzzle_slug=puzzle_slug,
                subpuzzle=self.subpuzzle,
                round_slug=self.round_slug,
                session_id=self.session_id,
            )
        else:
            logger.warning(
                "Received websocket data but no handler for (puzzle: %s) exists",
                puzzle_slug,
            )

    async def disconnect(self, code):
        handler = self.get_handler(self.puzzle_slug)
        if handler:
            await self.call_handler(
                handler.disconnect,
                user=self.user,
                uuid=self.uuid,
                slug=self.puzzle_slug,
            )

        for group in self.group_names:
            await self.channel_layer.group_discard(group, self.channel_name)

    @staticmethod
    def send_event(group, key, data):
        """
        Method to send data from outside to a channels group.
        Parameters:
        group: Identifier from get_team_group(user), get_puzzle_group(user, slug),
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
        run_async_to_sync(channel_layer.group_send, group, channels_data)

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

    @staticmethod
    def batch_send_event(
        throttle_key,
        interval,
        reducer,
        group,
        key,
        data,
    ):
        if settings.IS_PYODIDE:
            # no batching when running pyodide
            ClientConsumer.send_event(group, key, data)
            return
        lock_key = f"batch_event_lock:{throttle_key}"
        data_key = f"batch_event_data:{throttle_key}"
        with redis_lock(lock_key, timeout=settings.REDIS_FAST_TIMEOUT):
            prev_data_serialized = get_redis_handle().get(data_key)
            if prev_data_serialized is not None:
                prev_data = json.loads(prev_data_serialized)
                data = reducer(prev_data, data)
            data_serialized = json.dumps(data)
            get_redis_handle().set(
                data_key, data_serialized, px=int(settings.REDIS_FAST_TIMEOUT * 1000)
            )
            return send_cached_event.throttle(
                throttle_key, interval, args=(lock_key, data_key, group, key)
            )


@throttleable_task
def send_cached_event(
    lock_key,
    data_key,
    group,
    key,
):
    # redis doesn't run when using pyodide
    assert not settings.IS_PYODIDE
    with redis_lock(lock_key):
        serialized = get_redis_handle().getdel(data_key)
    if serialized is not None:
        data = json.loads(serialized)
        ClientConsumer.send_event(group, key, data)
