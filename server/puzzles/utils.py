import contextlib
import enum
import functools
import hashlib
import math
import re
from datetime import datetime
from functools import cache, lru_cache, wraps
from typing import Tuple

import redis
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Prefetch
from django.http import JsonResponse
from django.utils import timezone
from spoilr.core.api.hints import (
    get_hints_enabled,
    get_max_open_hints,
    get_solves_before_hint_unlock,
)
from spoilr.core.api.hunt import is_site_over
from spoilr.core.models import TeamType
from spoilr.hints.models import Hint
from spoilr.utils import json

from puzzles.celery import celery_app
from puzzles.models import Puzzle, PuzzleAccess, Team
from puzzles.models.story import StoryCard, StoryCardAccess


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


def is_unlocked(*, puzzle_slug=None, story_slug=None, user=None, team_id=None):
    if team_id is None:
        team_id = user.team_id
    team = Team.objects.filter(id=team_id)
    if puzzle_slug:
        team = team.prefetch_related(
            Prefetch(
                "puzzleaccess_set",
                queryset=PuzzleAccess.objects.filter(puzzle__slug=puzzle_slug),
            )
        )
    if story_slug:
        team = team.prefetch_related(
            Prefetch(
                "storycardaccess_set",
                queryset=StoryCardAccess.objects.filter(story_card__slug=story_slug),
            )
        )

    team = team.first()
    if not team:
        return False
    if puzzle_slug and team.puzzleaccess_set.first():
        return True
    if story_slug and team.storycardaccess_set.first():
        return True
    if team.is_internal or team.is_public:
        return (puzzle_slug and Puzzle.objects.filter(slug=puzzle_slug).exists()) or (
            story_slug and StoryCard.objects.filter(slug=story_slug).exists()
        )
    return False


@cache
def get_encryption_key(slug):
    "Get symmetric key for encrypting/decrypting a js file."
    m = hashlib.sha256()
    m.update(slug.encode())
    hashname = m.hexdigest()[:8]
    m = hashlib.sha256()
    m.update((hashname + settings.JS_ENCRYPTION_KEY).encode())
    key = m.hexdigest()
    return {hashname: key}


def get_encryption_keys(names):
    "Get key dict for a list of names."
    d = {}
    # encryption keys not used for the archive site
    if not settings.IS_POSTHUNT:
        for kv in map(get_encryption_key, names):
            d.update(kv)
    return d


@cache
def get_redis_handle():
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DATABASE_ENUM.REDIS_CLIENT.value,
    )


def redis_lock(*args, timeout=settings.REDIS_LONG_TIMEOUT, **kwargs):
    """
    Multiprocess lock using redis.

    You almost certainly want to use this as a context manager.
    Lock is automatically released after 60 seconds by default.
    """
    if settings.IS_PYODIDE:
        # skip lock when running in pyodide locally
        class FakeLock(contextlib.nullcontext):
            # provide noop handler for .acquire(), .release(), etc
            def __getattr__(self, k):
                return lambda *args, **kwargs: None

        return FakeLock()
    redis_handle = get_redis_handle()
    return redis_handle.lock(*args, timeout=timeout, **kwargs)


def throttleable_task(func):
    """
    Decorator to make a task that can be throttled.

    Send a task to Celery, throttled at most once per interval.
    Other calls will be dropped.

    func.throttle(key, interval, args=args, kwargs=kwargs)

    key: All tasks with the same key will be throttled together
    interval: seconds to wait between function calls
    """

    def get_lock_key(key):
        return f"throttle_task_lock:{key}"

    def get_state_key(key):
        return f"throttle_task_state:{key}"

    @functools.wraps(func)
    def wrapper(*args, _throttle_data=None, **kwargs):
        if not settings.IS_PYODIDE and _throttle_data is not None:
            key, prev_serialized, timeout = _throttle_data
            state_key = get_state_key(key)
            now = datetime.utcnow().timestamp()
            with redis_lock(get_lock_key(key), timeout=timeout):
                serialized = get_redis_handle().get(state_key)
                if serialized is not None:
                    serialized = serialized.decode()
                if serialized == prev_serialized:
                    now = datetime.utcnow().timestamp()
                    new_state = json.dumps([now, False])
                    get_redis_handle().set(state_key, new_state, px=int(timeout * 1000))
        return func(*args, **kwargs)

    task = celery_app.task(wrapper)

    def throttle(key, interval, *, args=None, kwargs=None):
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        if settings.IS_PYODIDE:
            task(*args, **kwargs)
            return
        timeout = settings.REDIS_FAST_TIMEOUT + interval
        with redis_lock(get_lock_key(key), timeout=timeout):
            state_key = get_state_key(key)
            now = datetime.utcnow().timestamp()
            ts = -math.inf
            pending = False
            state = get_redis_handle().get(state_key)
            if state is not None:
                ts, pending = json.loads(state)
            if pending:
                # throttled
                pass
            else:
                next_state_serialized = json.dumps([ts, True])
                get_redis_handle().set(
                    state_key, next_state_serialized, px=int(timeout * 1000)
                )
                countdown = max(0, ts + interval - now)
                task.apply_async(
                    args=args,
                    kwargs={
                        **kwargs,
                        "_throttle_data": (key, next_state_serialized, timeout),
                    },
                    countdown=countdown,
                    expires=countdown + settings.REDIS_FAST_TIMEOUT,
                )

    task.throttle = throttle
    return task


def get_puzzle_solve_count(puzzle):
    """Number of teams who solved this puzzle."""
    return (
        PuzzleAccess.objects.exclude(team__type=TeamType.INTERNAL)
        .filter(solved=True, solved_time__isnull=False, puzzle_id=puzzle.id)
        .count()
    )


class HintVisibility(enum.IntEnum):
    LOCKED = 0
    CAN_VIEW = 1
    CAN_REQUEST = 2


def num_open_hints(team):
    """Number of hints by this team that are still open."""
    return Hint.all_requiring_response().filter(team=team).count()


def hint_availability(puzzle, team) -> Tuple[HintVisibility, str]:
    if not team:
        return HintVisibility.LOCKED, "You must be signed in to request a hint."

    if team.is_public:
        return HintVisibility.LOCKED, "Public access team cannot request hints."

    if not get_hints_enabled():
        return HintVisibility.LOCKED, "Hints have not been released yet."

    if is_site_over():
        return (
            HintVisibility.CAN_VIEW,
            "HQ has closed and is no longer accepting hints.",
        )

    if puzzle.canonical_puzzle:
        puzzle = puzzle.canonical_puzzle
        if puzzle.canonical_puzzle:
            raise RuntimeError(f"Canonical puzzle chain longer than 2: {puzzle.slug}")

    if not (
        puzzle.override_hint_unlocked
        or get_puzzle_solve_count(puzzle) >= get_solves_before_hint_unlock()
    ):
        return HintVisibility.LOCKED, "Hints are not yet available for this puzzle."

    num_open = num_open_hints(team)
    if num_open >= get_max_open_hints():
        hints = "hint request" if num_open == 1 else "hint requests"
        return (
            HintVisibility.CAN_VIEW,
            f"You have {num_open} outstanding {hints}. Please wait for us to get back to you before requesting more hints.",
        )
    return HintVisibility.CAN_REQUEST, "Hints are available for this puzzle!"


def random_permutation(count):
    """
    Generate a pseudorandom permutation of range(count).

    Uses numpy when available since we did so during Hunt but fallback to the
    random module with Pyodide.
    """
    if settings.IS_PYODIDE:
        import random

        arr = list(range(count))
        random.shuffle(arr)
        return arr
    else:
        import numpy as np

        return np.random.permutation(count)
