# Roughly speaking, this module is most important for implementing "global
# variables" that are available in every template with the Django feature of
# "context processors". But it also does some stuff with caching computed
# properties of teams (the caching is only within a single request (?)). See
# https://docs.djangoproject.com/en/3.1/ref/templates/api/#using-requestcontext
import collections
import datetime
import inspect
import logging
import types

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from spoilr.core.api.hunt import get_site_launch_time, is_site_closed, is_site_over
from spoilr.core.models import HQUpdate
from spoilr.email.models import Email

from puzzles import models
from puzzles.hunt_config import (
    DEEP_MAX,
    DEEP_PER_ROUND,
    DEEP_PER_SLUG,
    DONE_SLUG,
    EVENTS_ROUND_SLUG,
    HUNT_ORGANIZERS,
    HUNT_TITLE,
)
from puzzles.models.story import StateEnum
from puzzles.shortcuts import get_shortcuts

User = get_user_model()
logger = logging.getLogger(__name__)


def context_middleware(get_response):
    def middleware(request):
        request.context = Context(request)
        return get_response(request)

    return middleware


# A context processor takes a request and returns a dictionary of (key: value)s
# to merge into the request's context.
def context_processor(request):
    def thunk(name):
        return lambda: getattr(request.context, name)

    return {name: thunk(name) for name in request.context._cached_names}


# Construct a get/set property from a name and a function to compute a value.
# Doing this with name="foo" causes accesses to self.foo to call fn and cache
# the result.
def wrap_cacheable(name, fn):
    def fget(self):
        if not hasattr(self, "_cache"):
            self._cache = {}
        if name not in self._cache:
            self._cache[name] = fn(self)
        return self._cache[name]

    def fset(self, value):
        if not hasattr(self, "_cache"):
            self._cache = {}
        self._cache[name] = value

    return property(fget, fset)


# Decorator for a class, like the `Context` class below but also the `Team`
# model, that replaces all non-special methods that take no arguments other
# than `self` with a get/set property as constructed above, and also gather
# their names into the property `_cached_names`.
def context_cache(cls):
    cached_names = []
    for c in (BaseContext, cls):
        for name, fn in c.__dict__.items():
            if (
                not name.startswith("__")
                and isinstance(fn, types.FunctionType)
                and inspect.getfullargspec(fn).args == ["self"]
            ):
                setattr(cls, name, wrap_cacheable(name, fn))
                cached_names.append(name)
    cls._cached_names = tuple(cached_names)
    return cls


# This object is a request-scoped cache containing data calculated for the
# current request. As a motivating example: showing current DEEP in the top
# bar and rendering the puzzles page both need the list of puzzles the current
# team has solved. This object ensures it only needs to be computed once,
# without explicitly having to pass it around from one place to the other.
# The properties here are accessible both from views and from templates. If
# you're adding something with complicated logic, prefer to put most of it in
# a model method and just leave a stub call here.

# In theory, `BaseContext` properties are things that make sense if all the info
# you have is an optional team (e.g. you don't know about a specific puzzle, or
# a user who might not be specified by the team). (But TODO(gph): this setup
# may currently be overengineered.))
class BaseContext:
    def hunt_title(self):
        return HUNT_TITLE

    def hunt_organizers(self):
        return HUNT_ORGANIZERS

    def now(self):
        return timezone.now()

    def start_time(self):
        return (
            get_site_launch_time() - self.team.start_offset
            if self.team
            else get_site_launch_time()
        )

    def hint_time(self):
        return self.start_time

    # XXX do NOT name this the same as a field on the actual Team model or
    # you'll silently be unable to update that field because you'll be writing
    # to this instead of the actual model field!
    def hunt_is_prereleased(self):
        return self.team and (
            self.team.is_prerelease_testsolver or self.team.is_internal
        )

    def hunt_has_started(self):
        return self.hunt_is_prereleased or self.now >= self.start_time

    def hunt_has_almost_started(self):
        return (
            self.hunt_is_prereleased
            or self.start_time - self.now < datetime.timedelta(hours=1)
        )

    def hunt_is_over(self):
        return is_site_over()

    def hunt_is_closed(self):
        return is_site_closed()

    def correct_puzzle_submissions(self):
        if not self.team:
            return []

        return self.team.correct_puzzle_submissions()

    def deep(self):
        if not self.team:
            # TODO handle end-of-hunt.
            return collections.defaultdict(lambda: -1)
        return self.team.compute_deep(self.correct_puzzle_submissions)


# In theory, `Context` properties are things that don't make sense if all the
# info you have is a team. They might make sense for a specific Django request
# that specifies a puzzle.
@context_cache
class Context:
    def __init__(self, request):
        self.request = request

    def is_superuser(self):
        return self.request.user.is_superuser

    def team(self):
        # user is a spoilr User. Its team field is the spoilr Team. To get the tph
        # Team, follow the 1:1 created implicitly by Django's concrete inheritance.
        if not self.request.user or self.request.user.is_anonymous:
            return None

        spoilr_team = self.request.user.team
        if not spoilr_team:
            return None

        return spoilr_team.team

    def site(self):
        """One of None, 'hunt', 'registration'"""
        from tph.utils import get_site

        return get_site(self.request)

    def story_state(self):
        if settings.IS_POSTHUNT:
            return StateEnum.STORY_COMPLETE

        if self.team:
            return self.team.story_state

        return StateEnum.DEFAULT

    def _internal_num_event_rewards(self):
        # Logic similar to intro hints - returns normal + strong events and expects client to
        # handle displaying the diff.
        if not self.team:
            return 0, 0, [], []
        return self.team.compute_internal_num_event_rewards()

    def num_event_rewards(self):
        # Context weirdness makes this a property function automatically.
        normal, _, _, _ = self._internal_num_event_rewards
        return normal

    def num_a3_event_rewards(self):
        # Context weirdness makes this a property function automatically.
        _, a3, _, _ = self._internal_num_event_rewards
        return a3

    def shortcuts(self):
        return tuple(get_shortcuts(self))

    def puzzle_unlocks(self):
        """May unlock new puzzles or advance story state as a side effect."""
        if not self.team:
            return []

        return self.team.unlock_puzzles(self.deep)

    def is_unlocked(self, slug):
        # Only checks for puzzle unlocks
        puzzle = None
        if (
            self.hunt_has_started
            or self.is_superuser
            or (self.team and self.team.is_internal)
        ):
            if settings.SERVER_ENVIRONMENT == "test_branch":
                from puzzles.debug import load_puzzle_from_branch_fixture

                # Dynamically load puzzle from branch fixture
                # TODO: Currently the request will fail if the fixture
                # conflicts with unique constraints. Determine if we want
                # to handle this differently.
                load_puzzle_from_branch_fixture(self.request, slug)
            for _puzzle in self.puzzle_unlocks:
                if _puzzle.slug == slug:
                    puzzle = _puzzle
                    break
        if puzzle is None and settings.IS_PYODIDE:
            # On static site, unlock on first request.
            if self.team is not None:
                puzzle = models.Puzzle.objects.filter(slug=slug).first()
                if puzzle is not None:
                    models.PuzzleAccess.objects.get_or_create(
                        team=self.team, puzzle=puzzle
                    )
        return (puzzle is not None, puzzle)

    def is_minipuzzle_unlocked(self, slug, minipuzzle):
        """Whether minipuzzle is unlocked given slug is unlocked"""
        # TODO: Add mapping for minipuzzles?
        return True

    def is_hunt_complete(self):
        team = self.team
        return self.is_superuser or (
            team
            and models.PuzzleSubmission.objects.filter(
                team_id=team.id, puzzle__slug=DONE_SLUG, correct=True
            ).exists()
        )

    def errata(self):
        """Errata for all unlocked puzzles."""
        errata_models = (
            HQUpdate.objects.filter(puzzle__in=self.puzzle_unlocks)
            .select_related("puzzle")
            .order_by("creation_time")
        )
        return [err.render_data() for err in errata_models]

    def all_puzzles(self):
        return tuple(models.Puzzle.objects.prefetch_related("metas").order_by("deep"))

    def puzzle(self):
        return None  # set by validate_puzzle

    def puzzle_answer(self):
        """Returns the puzzle answer only if it's solved."""
        return (
            self.team
            and self.puzzle
            and self.team.puzzle_answer(self.puzzle, self.puzzle_submissions)
        )

    def guesses_remaining(self):
        return (
            self.team
            and self.puzzle
            and self.team.guesses_remaining(self.puzzle, self.puzzle_submissions)
        )

    def puzzle_submissions(self):
        if not (self.team and self.puzzle):
            return []
        return self.team.puzzle_submissions(self.puzzle)

    def num_unclaimed_hints(self):
        # import here to avoid circular dependency
        from puzzles.views.auth import restrict_access

        @restrict_access()
        def _num_unclaimed_hints(self):
            return (
                models.Hint.objects.filter(
                    is_request=True,
                    response__isnull=True,
                    claimed_datetime__isnull=True,
                )
                .exclude(status__in=(models.Hint.OBSOLETE, models.Hint.RESOLVED))
                .annotate(
                    db_original_request_id=models.Case(
                        models.When(root_ancestor_request__isnull=True, then="id"),
                        default="root_ancestor_request_id",
                    )
                )
                .values("db_original_request_id")
                .distinct()
                .count()
            )

        return _num_unclaimed_hints(self.request)

    def num_unclaimed_emails(self):
        # import here to avoid circular dependency
        from puzzles.views.auth import restrict_access

        @restrict_access()
        def _num_unclaimed_emails(self):
            # This will count multiple emails in the same thread. A complicated
            # query to count threads is probably not worth it and could have
            # detrimental runtime effects.
            return Email.objects.filter(
                is_from_us=False,
                is_spam=False,
                status=Email.RECEIVED_NO_REPLY,
                claimed_datetime__isnull=True,
            ).count()

        return _num_unclaimed_emails(self.request)

    def num_unsent_emails(self):
        # import here to avoid circular dependency
        from puzzles.views.auth import restrict_access

        @restrict_access()
        def _num_unsent_emails(self):
            cooldown = datetime.timedelta(seconds=Email.RESEND_COOLDOWN)
            now = timezone.now()
            return (
                Email.objects.filter(status=Email.SENDING)
                .exclude(scheduled_datetime__gt=now)
                .exclude(attempted_send_datetime__gt=now - cooldown)
                # exclude when all address lists are empty
                .exclude(to_addresses__len=0, cc_addresses__len=0, bcc_addresses__len=0)
                .count()
            )

        return _num_unsent_emails(self.request)
