import functools, hashlib

from django.conf import settings
from django.core.cache import caches

SERVER_CACHE_TIMEOUT_S = 60 * 60

cache = caches[settings.SPOILR_CACHE_NAME]


def memoized_cache(bucket, timeout=None):
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped(*args):
            key = f"memoized:{bucket}:{view_func.__name__}:{_hash_args(*args)}"
            return _memoized_cache(view_func, key, *args, timeout=timeout)

        return wrapped

    return decorator


def clear_memoized_cache(bucket):
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped(*args):
            delete_memoized_cache_entry(view_func, bucket, *args)
            return view_func(*args)

        return wrapped

    return decorator


def _memoized_cache(result_factory, key, *args, timeout=None, **kwargs):
    if timeout is None:
        timeout = SERVER_CACHE_TIMEOUT_S
    result = cache.get(key)
    if not result:
        result = result_factory(*args, **kwargs)
        cache.set(key, result, timeout=timeout)
    return result


def delete_memoized_cache_entry(func, bucket, *args):
    key = f"memoized:{bucket}:{func.__name__}:{_hash_args(*args)}"
    cache.delete(key)


def nuke_cache():
    cache.clear()


def _hash_args(*args):
    hasher = hashlib.sha256()
    for arg in args:
        str_arg = arg if isinstance(arg, str) else str(arg)
        hasher.update(str_arg.encode("utf-8"))
    return hasher.hexdigest()
