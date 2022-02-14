# Roughly speaking, this module is most important for implementing "global
# variables" that are available in every template with the Django feature of
# "context processors". But it also does some stuff with caching computed
# properties of teams (the caching is only within a single request (?)). See
# https://docs.djangoproject.com/en/3.1/ref/templates/api/#using-requestcontext
import datetime
import inspect
import types

from django.conf import settings
from django.utils import timezone

from puzzles import models
from puzzles.hunt_config import (
    HUNT_TITLE,
    HUNT_ORGANIZERS,
    DAYS_BEFORE_HINTS,
    DEEP_MAX,
    HUNT_CLOSE_TIME,
    HUNT_END_TIME,
    HUNT_START_TIME,
    INTRO_META_SLUGS,
    META_META_SLUG,
)
from puzzles.shortcuts import get_shortcuts


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
        return timezone.localtime()

    def start_time(self):
        return (
            HUNT_START_TIME - self.team.start_offset if self.team else HUNT_START_TIME
        )

    def end_time(self):
        return HUNT_END_TIME

    def close_time(self):
        return HUNT_CLOSE_TIME

    def hint_time(self):
        return self.start_time + datetime.timedelta(days=DAYS_BEFORE_HINTS)

    # XXX do NOT name this the same as a field on the actual Team model or
    # you'll silently be unable to update that field because you'll be writing
    # to this instead of the actual model field!
    def hunt_is_prereleased(self):
        return self.team and self.team.is_prerelease_testsolver

    def hunt_has_started(self):
        return self.hunt_is_prereleased or self.now >= self.start_time

    def hunt_has_almost_started(self):
        return self.start_time - self.now < datetime.timedelta(hours=1)

    def hunt_is_over(self):
        return self.now >= self.end_time

    def hunt_is_closed(self):
        return self.now >= self.close_time

    def deep(self):
        return models.Team.compute_deep(self)

    def metameta_deep(self):
        return models.Team.compute_metameta_deep(self)

    def display_deep(self):
        return "\u221e" if self.deep == DEEP_MAX else int(self.deep)

    def solves_per_round(self):
        return models.Team.compute_solves_per_round(self)


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
        return getattr(self.request.user, "team", None)

    def shortcuts(self):
        return tuple(get_shortcuts(self))

    def num_hints_remaining(self):
        return self.team.num_hints_remaining if self.team else 0

    def num_free_answers_remaining(self):
        return self.team.num_free_answers_remaining if self.team else 0

    def submissions(self):
        return self.team.submissions if self.team else []

    def puzzle_unlocks(self):
        return models.Team.compute_puzzle_unlocks(self)

    def story_unlocks(self):
        return models.Team.compute_story_unlocks(self)

    def unlocks(self):
        unlocks = {}
        unlocks.update(self.puzzle_unlocks)
        unlocks.update(self.story_unlocks)
        return unlocks

    def is_unlocked(self, slug):
        # Only checks for puzzle unlocks, not story unlocks.
        puzzle = None
        if self.hunt_has_started or self.hunt_is_prereleased or self.is_superuser:
            for puzzle_data in self.puzzle_unlocks["puzzles"]:
                _puzzle = puzzle_data["puzzle"]
                if _puzzle.slug == slug:
                    puzzle = _puzzle
                    break
        if puzzle is None and settings.IS_PYODIDE:
            # On static site, unlock on first request.
            # This is primarily needed for Oxford Fiesta.
            if self.team is not None:
                puzzle = models.Puzzle.objects.filter(slug=slug).first()
                if puzzle is not None:
                    models.PuzzleUnlock.objects.get_or_create(
                        team=self.team, puzzle=puzzle
                    )
        return (puzzle is not None, puzzle)

    def is_subpuzzle_unlocked(self, slug, subpuzzle):
        """Whether subpuzzle is unlocked given slug is unlocked"""
        from puzzles.views.puzzles import dc_meet_and_greet

        if slug == dc_meet_and_greet.PUZZLE_SLUG:
            return dc_meet_and_greet.is_subpuzzle_unlocked(self.team, subpuzzle)
        return True

    def is_main_round_unlocked(self):
        if self.is_superuser:
            return True
        team = self.team
        # First condition needed to stop main round from unlocking if 0 objects
        # exist, which might occur depending on DB state in prod.
        return bool(
            INTRO_META_SLUGS
            and models.AnswerSubmission.objects.filter(
                team=team, puzzle__slug__in=INTRO_META_SLUGS, is_correct=True
            ).count()
            == len(INTRO_META_SLUGS)
        )

    def is_hunt_complete(self):
        team = self.team
        return (
            self.is_superuser
            or models.AnswerSubmission.objects.filter(
                team=team, puzzle__slug=META_META_SLUG, is_correct=True
            ).exists()
        )

    def errata(self):
        """Errata for all unlocked puzzles."""
        errata_models = (
            models.Errata.objects.filter(puzzle__id__in=(self.unlocks["ids"]))
            .select_related("puzzle")
            .order_by("creation_time")
        )
        return [err.render_data() for err in errata_models]

    def all_puzzles(self):
        return tuple(models.Puzzle.objects.prefetch_related("metas").order_by("deep"))

    def all_story(self):
        return tuple(
            models.StoryCard.objects.select_related("puzzle").order_by(
                "deep", "unlock_order", "slug"
            )
        )

    def puzzle(self):
        return None  # set by validate_puzzle

    def puzzle_answer(self):
        return self.team and self.puzzle and self.team.puzzle_answer(self.puzzle)

    def guesses_remaining(self):
        return self.team and self.puzzle and self.team.guesses_remaining(self.puzzle)

    def puzzle_submissions(self):
        return self.team and self.puzzle and self.team.puzzle_submissions(self.puzzle)

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
            return models.Email.objects.filter(
                is_from_us=False,
                is_spam=False,
                status=models.Email.RECEIVED_NO_REPLY,
                claimed_datetime__isnull=True,
            ).count()

        return _num_unclaimed_emails(self.request)

    def num_unsent_emails(self):
        # import here to avoid circular dependency
        from puzzles.views.auth import restrict_access

        @restrict_access()
        def _num_unsent_emails(self):
            cooldown = datetime.timedelta(seconds=models.Email.RESEND_COOLDOWN)
            now = timezone.now()
            return (
                models.Email.objects.filter(status=models.Email.SENDING)
                .exclude(scheduled_datetime__gt=now)
                .exclude(attempted_send_datetime__gt=now - cooldown)
                # exclude when all address lists are empty
                .exclude(to_addresses__len=0, cc_addresses__len=0, bcc_addresses__len=0)
                .count()
            )

        return _num_unsent_emails(self.request)
