import contextlib
import re
import time
from functools import lru_cache, wraps

import redis
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse

from puzzles.models import PuzzleUnlock, Team


def normalize_answer(answer):
    normalized = ""
    for c in answer:
        code = ord(c)
        if code >= ord("a") and code <= ord("z"):
            # uppercase any lowercase alpha
            normalized += c.upper()
        elif code >= ord("A") and code <= ord("Z"):
            # pass-through any uppercase alpha
            normalized += c
        elif code <= 255:
            # ignore all other ASCII characters
            pass
        else:
            # pass everything else
            normalized += c
    return normalized


def login_required(function=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            return JsonResponse({}, status=401)

        return _wrapped_view

    if function:
        return decorator(function)
    return decorator


def format_duration(seconds):
    days = seconds // (60 * 60 * 24)
    remaining = seconds % (60 * 60 * 24)

    hours = remaining // (60 * 60)
    remaining = remaining % (60 * 60)

    minutes = remaining // (60)
    seconds = remaining % (60)

    s = f"{days}d, {hours}h, {minutes}m, {seconds}s"
    return s


class RateLimiter:
    def __init__(self, interval):
        self.interval = interval
        self.last_guess = 0

    def is_allowed(self):
        now = time.time()
        if now - self.last_guess > self.interval:
            self.last_guess = now
            return True
        return False


@lru_cache(maxsize=32768)
def get_rate_limiter_for(key, limit=1):
    return RateLimiter(12)


def get_all_emails(unlocked_puzzle=None):
    """Retrieves all emails based on given constraints, grouped by team"""
    if unlocked_puzzle is None:
        teams = Team.objects.all()
    else:
        unlocks = PuzzleUnlock.objects.filter(puzzle=unlocked_puzzle).select_related(
            "team"
        )
        teams = [unlock.team for unlock in unlocks]
    return [(team, team.get_emails()) for team in teams]


_redis_handle = None


def redis_lock(*args, **kwargs):
    """
    Multiprocess lock using redis.

    You almost certainly want to use this as a context manager.
    """
    global _redis_handle
    if settings.IS_PYODIDE:
        return contextlib.nullcontext()
    if _redis_handle is None:
        _redis_handle = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DATABASE_ENUM.REDIS_CLIENT.value,
        )
    return _redis_handle.lock(*args, **kwargs)
