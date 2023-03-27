import abc
import datetime
import functools
import math
from spoilr.utils import json

from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import models, transaction

from puzzles.models.interactive import PuzzleState, Session, UserState
from puzzles.utils import get_redis_handle, redis_lock, throttleable_task
from tph.utils import get_task_logger

task_logger = get_task_logger(__name__)


class StateDataHandle:
    """
    Functions to get / set data directly. This does no caching.
    Strongly prefer PuzzleStateCache.

    get_* functions return whether the data was available in the corresponding
    data store in addition to the data.

    Internally, if there are no additional_field, state is the entire data
    value. Otherwise, each field becomes one key of the json dict.
    """

    def __init__(self, model, id_kwargs, additional_fields=()):
        self.model = model
        self.id_kwargs = id_kwargs
        self.additional_fields = additional_fields
        self._key_base = None

    @property
    def key_base(self):
        "Assumes colons are not valid in the arguments"
        if self._key_base is None:
            parts = [
                self.model.__name__,
            ]
            for name in sorted(self.id_kwargs):
                parts.append(f"{name}:{self.id_kwargs[name]}")
            self._key_base = ":".join(parts)
        return self._key_base

    @property
    def key(self):
        return f"cache-state:{self.key_base}"

    @property
    def lock_key(self):
        return f"cache-state-lock:{self.key_base}"

    @property
    def sync_task_key(self):
        return f"cache-state-sync-task:{self.key_base}"

    def serialize(self, data):
        needs_conversion = False
        for field in self.additional_fields:
            if isinstance(data.get(field), datetime.datetime):
                needs_conversion = True
        if needs_conversion:
            data = {
                key: value.isoformat()
                if isinstance(value, datetime.datetime)
                else value
                for key, value in data.items()
            }
        return json.dumps(data)

    def deserialize(self, serialized):
        data = json.loads(serialized)
        for field in self.additional_fields:
            if isinstance(getattr(self.model, field), models.DateTimeField):
                if field in data:
                    data[field] = datetime.datetime.fromisoformat(data[field])
        return data

    def get_redis_state(self):
        serialized = self.get_redis_state_serialized()
        if serialized is None:
            return False, None
        data = self.deserialize(serialized)
        return True, data

    def get_redis_state_serialized(self):
        if settings.IS_PYODIDE:
            return None
        return get_redis_handle().get(self.key)

    def set_redis_state_serialized(self, serialized, nx=False):
        """
        Set Redis state.
        serialized: data as serialized string
        nx: set only if the key does not already exist
        """
        if settings.IS_PYODIDE:
            return
        get_redis_handle().set(self.key, serialized, nx=nx)

    def delete_redis_state(self):
        if settings.IS_PYODIDE:
            # redis DEL returns number of keys deleted
            return 0
        return get_redis_handle().delete(self.key)

    def get_db_state(self):
        instance = self.model.objects.filter(**self.id_kwargs).first()
        if instance is None:
            return False, None
        if self.additional_fields:
            state = {
                field: getattr(instance, field) for field in self.additional_fields
            }
            state["state"] = instance.state
        else:
            state = instance.state
        return True, state

    def set_db_state_serialized(self, serialized):
        data = self.deserialize(serialized)
        if self.additional_fields:
            update_kwargs = data
        else:
            update_kwargs = {
                "state": data,
            }
        # update does not call signals
        if not self.model.objects.filter(**self.id_kwargs).update(**update_kwargs):
            # save does send signals, but we want to disable redis eviction
            instance = self.model(
                **update_kwargs,
                **self.id_kwargs,
            )
            instance._no_evict_redis = True
            instance.save()

    def lock(self):
        "Context manager for a redis lock keyed on this team / puzzle."
        return redis_lock(self.lock_key, timeout=settings.REDIS_FAST_TIMEOUT)


class StateCacheManager(abc.ABC):
    """
    Context manager for redis cached state values. Use for performance.
    """

    # subclasses must override these
    MODEL = None
    ID_FIELDS = ()
    SYNC_STATE_TO_DB = None

    # subclasses can override to track additional fields
    ADDITIONAL_FIELDS = ()

    def __init__(
        self,
        *,
        lock=True,
        lock_write=False,
        initial_data=None,
        throttle_interval=None,
        **id_kwargs,
    ):
        """
        lock: acquire lock on enter
        lock_write: keep lock when writing back to the database
        initial_data: data to return if the data does not exist
        throttle_interval: number of seconds to wait before syncing to the db
            again. These db syncs happen asynchronously via Celery.
        id_kwargs: kwargs to instantiate the model. This should be the
        complete set of fields to uniquely specify the instance
        """
        assert all(fieldname in id_kwargs for fieldname in self.ID_FIELDS)
        self.id_kwargs = id_kwargs
        self.lock = lock
        self.lock_write = lock_write
        self.initial_data = initial_data
        self.throttle_interval = throttle_interval

        self.data_handle = StateDataHandle(
            self.MODEL, self.id_kwargs, self.ADDITIONAL_FIELDS
        )
        self._state = None
        # use serialized state for immutable semantics
        self._serialized = None

        # State handling flags
        self._context_activated = False
        # cache manager state can be updated before pushing back to data stores
        self._state_is_set = False
        self._redis_dirty = False
        self._db_dirty = False
        # whether the state is finalized (no more writes)
        self._sealed = False

    def __enter__(self):
        if self.lock:
            self.lock = self.data_handle.lock()
            self.lock.acquire()
        self._context_activated = True
        return self

    def __exit__(self, *args, **kwargs):
        try:
            self.seal()
            if self._db_dirty:
                self.flush(redis=False, db=True)
        finally:
            if self.lock:
                self.lock.release()
            self._context_activated = False

    def seal(self, check_db_sync=True):
        """
        Push state back to redis and release lock.
        You will not be able to set the state again after this.

        Main use case for using this directly is if we want to do something
        before pushing to the db. In some of these cases, using
        throttle_interval might be preferred instead.
        """
        assert self._context_activated
        self.flush(redis=True, db=False)
        if self.lock and not self.lock_write:
            self.lock.release()
            self.lock = False
        self._sealed = True

    def get_no_create(self, override_default=None):
        return self._get(create=False, override_default=override_default)

    def get_or_create(self, override_default=None):
        return self._get(create=True, override_default=override_default)

    def _get(self, create, override_default=None):
        assert self._context_activated
        if self._serialized is None:
            # check redis first
            self._serialized = self.data_handle.get_redis_state_serialized()
            if self._serialized is not None:
                data = self.data_handle.deserialize(self._serialized)
            else:
                found, data = self.data_handle.get_db_state()
                if create:
                    if not found:
                        data = override_default
                        if data is None:
                            data = self.initial_data
                        self._db_dirty = True
                    self._serialized = self.data_handle.serialize(data)
                    self._redis_dirty = True
            self._state = data
        return self._state

    def set(self, data):
        assert self._context_activated
        assert not self._sealed
        self._state = data
        self._serialized = self.data_handle.serialize(data)
        self._state_is_set = True
        self._redis_dirty = True
        self._db_dirty = True

    def flush(self, redis=True, db=True):
        assert self._context_activated
        if redis and self._redis_dirty:
            self.data_handle.set_redis_state_serialized(
                self._serialized, nx=not self._state_is_set
            )
            self._redis_dirty = False
        if db and self._db_dirty:
            if self.throttle_interval is None:
                # set db now directly
                self.data_handle.set_db_state_serialized(self._serialized)
                self._db_dirty = False
            else:
                # set db async
                self.SYNC_STATE_TO_DB.throttle(
                    self.data_handle.sync_task_key,
                    self.throttle_interval,
                    kwargs=self.id_kwargs,
                )


def sync_state_to_db_maker(get_model_and_fields):
    @functools.wraps(get_model_and_fields)
    def wrapper(**kwargs):
        model, additional_fields = get_model_and_fields()
        data_handle = StateDataHandle(model, kwargs, additional_fields)
        serialized = data_handle.get_redis_state_serialized()
        if serialized is not None:
            data_handle.set_db_state_serialized(serialized)

    return throttleable_task(wrapper)


# these should be module functions not class functions
@sync_state_to_db_maker
def sync_puzzle_state_to_db():
    return PuzzleState, PuzzleStateCacheManager.ADDITIONAL_FIELDS


@sync_state_to_db_maker
def sync_session_state_to_db():
    return Session, SessionCacheManager.ADDITIONAL_FIELDS


"""
Easy to do for UserState too, but quandle is the only thing using UserState,
which it does not need Redis caching.
"""
# @sync_state_to_db_maker
# def sync_user_state_to_db():
#     return UserState, UserStateCacheManager.ADDITIONAL_FIELDS


class PuzzleStateCacheManager(StateCacheManager):
    MODEL = PuzzleState
    ID_FIELDS = ("team_id", "puzzle_id")
    SYNC_STATE_TO_DB = sync_puzzle_state_to_db


class SessionCacheManager(StateCacheManager):
    MODEL = Session
    ID_FIELDS = ("team_id", "puzzle_id", "storycard_id")
    SYNC_STATE_TO_DB = sync_session_state_to_db
    ADDITIONAL_FIELDS = (
        "start_time",
        "finish_time",
        "is_complete",
    )


# class UserStateCacheManager(StateCacheManager):
#     MODEL = UserState
#     SYNC_STATE_TO_DB = sync_user_state_to_db
#     ID_FIELDS = ("puzzle_id", "team_id", "uuid")


@receiver(post_save, sender=PuzzleState)
@receiver(post_delete, sender=PuzzleState)
@receiver(post_save, sender=Session)
@receiver(post_delete, sender=Session)
# @receiver(post_save, sender=UserState)
# @receiver(post_delete, sender=UserState)
def maybe_evict_redis_key(sender, instance, **kwargs):
    if sender is PuzzleState:
        keys = PuzzleStateCacheManager.ID_FIELDS
    elif sender is Session:
        keys = SessionCacheManager.ID_FIELDS
    # elif sender is UserState:
    # keys = UserStateCacheManager.ID_FIELDS
    else:
        # should not get here
        assert False
    id_kwargs = {key: getattr(instance, key) for key in keys}
    if not getattr(instance, "_no_evict_redis", False):
        transaction.on_commit(
            StateDataHandle(
                sender,
                id_kwargs,
            ).delete_redis_state
        )
