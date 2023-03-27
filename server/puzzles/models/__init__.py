import collections
import datetime
import logging
import math
import os
import zoneinfo
from itertools import groupby
from typing import Optional
from uuid import uuid4

import spoilr.core.models
import spoilr.email.models
import spoilr.hints.models
from django import forms
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.db.models import Case, Exists, F, OuterRef, Q, Subquery, Sum, When
from django.db.models.functions import FirstValue
from django.utils import timezone
from puzzles.hunt_config import (
    DEEP_PER_ROUND,
    DEEP_PER_SLUG,
    DONE_SLUG,
    EVENTS_ROUND_SLUG,
    MAX_GUESSES_PER_PUZZLE,
    UNLIMITED_GUESSES,
)
from puzzles.messaging import dispatch_victory_alert, send_mail_wrapper
from spoilr.core.api.events import (
    get_num_extra_a3_event_rewards,
    get_num_extra_event_rewards,
)
from spoilr.core.api.hunt import get_site_end_time, release_puzzle, release_round
from spoilr.utils import generate_url

from .utils import SlugManager, SlugModel

logger = logging.getLogger(__name__)


def random_uuid():
    return uuid4().hex


class Round(spoilr.core.models.Round):
    """A proxy class for tracking rounds."""

    class Meta:
        proxy = True


class PuzzleManager(SlugManager):
    def get_queryset(self, *args, **kwargs):
        # Prefetches the round and event status automatically.
        return (
            super()
            .get_queryset(*args, **kwargs)
            .select_related("round__superround", "event")
        )

    def unlocked_by_team(self, team):
        """Returns a queryset of puzzles that have been unlocked by a given team."""
        if team.is_internal:
            return self.get_queryset()

        return self.filter(
            Exists(PuzzleAccess.objects.filter(team=team, puzzle=OuterRef("pk")))
        )


class Puzzle(spoilr.core.models.Puzzle, SlugModel):
    """A single puzzle in the puzzlehunt."""

    objects = PuzzleManager()

    # this just renames the parent_link for the multi-table inheritance
    spoilr_puzzle = models.OneToOneField(
        spoilr.core.models.Puzzle,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
    )

    canonical_puzzle = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True
    )

    # progress threshold to unlock this puzzle
    deep = models.IntegerField(verbose_name="DEEP threshold")
    # key to use for checking deep. Defaults to round slug
    deep_key = models.CharField(
        max_length=500, verbose_name="DEEP key", null=True, blank=True
    )

    override_hint_unlocked = models.BooleanField(
        default=False,
        help_text="If true, overrides this puzzle to release hints regardless of solve count",
    )

    override_virtual_unlocked = models.BooleanField(
        default=False,
        help_text="If true, overrides this puzzle to release the virtual version regardless of time since unlock",
    )

    def create_icon_filename(instance, filename):
        # Place all icons under a common "icons" subdir for easier management.
        _, extension = os.path.splitext(filename)
        return f"site/icons/{instance.slug}/icon_{random_uuid()}{extension}"

    # Icon for the unsolved version of each puzzle
    unsolved_icon = models.ImageField(
        upload_to=create_icon_filename, max_length=300, blank=True
    )
    # Icons for the solved version of each puzzle
    solved_icon = models.ImageField(
        upload_to=create_icon_filename, max_length=300, blank=True
    )

    # Icon position is offset from center (%) and is defined in percentage of
    # overall round canvas.
    icon_x = models.FloatField(default=0)
    icon_y = models.FloatField(default=0)
    icon_size = models.FloatField(default=0)
    icon_ratio = models.FloatField(default=1)
    text_x = models.FloatField(default=0)
    text_y = models.FloatField(default=0)

    # used in Discord integrations involving this puzzle
    emoji = models.CharField(max_length=500, default=":question:")

    # URL for testsolving (make sure this is empty before releasing!)
    testsolve_url = models.CharField(max_length=500, null=True, blank=True)

    # number of points contributed to leaderboard
    # despite "positive", it actually allows 0 points for hidden puzzles.
    points = models.PositiveSmallIntegerField(default=1)

    @property
    def short_name(self):
        ret = []
        last_alpha = False
        for c in self.name:
            if c.isalpha():
                if not last_alpha:
                    ret.append(c)
                last_alpha = True
            elif c != "'":
                if c != " ":
                    ret.append(c)
                last_alpha = False
        s = "".join(ret)
        if len(s) > 7:
            return s[:6] + "…"
        if len(s) == 1:
            return self.name[:3]
        else:
            return s

    @property
    def url(self):
        if hasattr(self, "event"):
            url = f"/events/{self.slug}"
        else:
            url = f"/puzzles/{self.slug}"

        return generate_url(self.site, url)

    @property
    def hints_url(self):
        if self.round.act == 1:
            url = f"/hints/{self.slug}"
        else:
            round_slug = self.get_round_slug()
            url = f"/{round_slug}/hints/{self.slug}"

        return generate_url("hunt", url)

    def get_hints_url(self, story_state):
        return self.hints_url

    def get_round_slug(self):
        return (self.round.superround or self.round).slug

    def normalize_answer(self, s: str, team=None) -> str:
        from puzzles.rounds import CUSTOM_ROUND_ANSWERS

        if self.round.slug in CUSTOM_ROUND_ANSWERS:
            return CUSTOM_ROUND_ANSWERS[self.round.slug](s, self, team)

        return super().normalize_answer(s)

    def is_correct(self, s: str, team) -> bool:
        from puzzles.rounds import CUSTOM_ROUND_CHECKERS

        if self.round.slug in CUSTOM_ROUND_CHECKERS:
            return CUSTOM_ROUND_CHECKERS[self.round.slug](s, self, team)

        return super().is_correct(s)

    def on_solved(self, team) -> None:
        from puzzles.rounds import CUSTOM_ROUND_SOLVE_CALLBACKS

        if self.round.slug in CUSTOM_ROUND_SOLVE_CALLBACKS:
            CUSTOM_ROUND_SOLVE_CALLBACKS[self.round.slug](self.slug, team)


class Team(spoilr.core.models.Team):
    # Overrides the get_queryset in SpoilrTeamManager
    objects = models.Manager()

    # this just renames the parent_link for the multi-table inheritance
    spoilr_team = models.OneToOneField(
        spoilr.core.models.Team,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
    )

    # How much earlier this team should start, for early-testing teams
    # Be careful with this!
    start_offset = models.DurationField(default=datetime.timedelta)

    # Number of additional hints to award the team, on top of the 2 per day
    total_hints_awarded = models.IntegerField(default=0)

    # Number of free answers allowed to be used on non-metas.
    # Also includes free unlocks for MH-2023.
    total_free_answers_awarded = models.IntegerField(default=0)

    # Number of free answers usable on any non-meta answer, including A3 feeders,
    # but not A3 metas.
    total_a3_free_answers_awarded = models.IntegerField(default=0)

    # Last solve time
    last_solve_time = models.DateTimeField(null=True, blank=True)

    # If true, team will have access to puzzles before the hunt starts
    is_prerelease_testsolver = models.BooleanField(default=False)

    # If true, team will not be visible to the public
    is_hidden = models.BooleanField(default=False)

    def team_url(self):
        return generate_url("hunt", f"/team/{self.slug}")

    @property
    def story_state(self):
        from .story import StoryState  # Avoid circular import

        return StoryState.get_state(self)

    # This is an expensive function. Use context to cache where available.
    def puzzle_submissions(self, puzzle):
        return [
            submission
            for submission in self.puzzlesubmission_set.filter(
                puzzle=puzzle,
            )
        ]

    # This is a helper function to get the QuerySet of just correct puzzle
    # submissions. It exists in the context cache and should only be used by
    # functions without access to a context.
    def correct_puzzle_submissions(self):
        return list(
            PuzzleSubmission.objects.filter(team=self, correct=True)
            .select_related("puzzle__round")
            .order_by("timestamp")
        )

    def completed_story_sessions(self):
        """Returns set of storycard slugs for which this team has completed an interaction."""
        from .interactive import Session

        slugs = set()
        for session in Session.objects.filter(
            team=self, storycard__isnull=False, is_complete=True
        ).select_related("storycard"):
            slugs.add(session.storycard.slug)
        return slugs

    def compute_min_deep(self):
        round_deep = collections.defaultdict(lambda: 0)
        # Deep from time unlocks
        for deep_floor in DeepFloor.objects.filter(
            Q(team=None) | Q(team=self), enabled=True
        ):
            round_deep[deep_floor.deep_key] = max(
                deep_floor.min_deep, round_deep[deep_floor.deep_key]
            )
        return round_deep

    def compute_internal_num_event_rewards(self):
        # Called by context, lives in team for easier use by spoilr code.
        correct_subs = self.correct_puzzle_submissions()
        events_solved = len(
            [sub for sub in correct_subs if sub.puzzle.round.slug == EVENTS_ROUND_SLUG]
        )
        scavengers_solved = len(
            [
                sub
                for sub in correct_subs
                if sub.puzzle.slug == "touch-grass-challenge-impossible"
            ]
        )
        num_total = (
            2 * events_solved
            + get_num_extra_event_rewards()
            + self.total_free_answers_awarded
        )
        num_a3_total = (
            2 * scavengers_solved
            + get_num_extra_a3_event_rewards()
            + self.total_a3_free_answers_awarded
        )
        # Iterate over free unlocks - only usable by regular rewards.
        free_unlocks = 0
        for eu in ExtraUnlock.objects.filter(team=self):
            free_unlocks += eu.count
        num_total -= free_unlocks
        # Iterate over free non-A3 answers.
        # Some of these may be from A3 rewards. Only deduct those if needed
        # there's a way to do this without the for loop - I am not going to figure it out when I'm tired.
        used_reg = []
        used_a3 = []
        for sub in correct_subs:
            if sub.used_free_answer:
                # Deduct from weakest reward
                if sub.puzzle.round.act < 3 and num_total > 0:
                    num_total -= 1
                    used_reg.append(sub.puzzle.name)
                else:
                    num_a3_total -= 1
                    used_a3.append(sub.puzzle.name)
        return num_total, num_a3_total, used_reg, used_a3

    # Prefer using the context implementation when possible, since that is cached.
    def compute_deep(self, correct_puzzle_subs):
        round_deep = collections.defaultdict(lambda: 0)

        for submission in correct_puzzle_subs:
            if submission.puzzle.slug in DEEP_PER_SLUG:
                for k, v in DEEP_PER_SLUG[submission.puzzle.slug].items():
                    round_deep[k] += v
            # Round should always defined, but do a None check regardless since
            # if this errors it breaks every page.
            elif (
                submission.puzzle.round
                and submission.puzzle.round.slug in DEEP_PER_ROUND
            ):
                for k, v in DEEP_PER_ROUND[submission.puzzle.round.slug].items():
                    round_deep[k] += v
            else:
                logger.warning(
                    f"Puzzle {submission.puzzle.slug} did not have slug or round called out in hunt_config"
                )
                round_deep[submission.puzzle.round.slug] += 100

        # Check for completed story interactions.
        for story_slug in self.completed_story_sessions():
            if story_slug in DEEP_PER_SLUG:
                for k, v in DEEP_PER_SLUG[story_slug].items():
                    round_deep[k] += v

        minimum_deep = self.compute_min_deep()
        for k, v in minimum_deep.items():
            round_deep[k] = max(round_deep[k], v)
        return round_deep

    def puzzle_answer(self, puzzle, puzzle_submissions=None):
        if puzzle_submissions is None:
            puzzle_submissions = self.puzzle_submissions(puzzle)
        assert all(
            submission.puzzle_id == puzzle.id for submission in puzzle_submissions
        )
        return (
            puzzle.answer
            if any(submission.correct for submission in puzzle_submissions)
            else None
        )

    def guesses_remaining(self, puzzle, puzzle_submissions=None):
        if UNLIMITED_GUESSES:
            return 999999

        if puzzle_submissions is None:
            puzzle_submissions = self.puzzle_submissions(puzzle)
        assert all(
            submission.puzzle_id == puzzle.id for submission in puzzle_submissions
        )
        wrong_guesses = sum(
            1 for submission in puzzle_submissions if not submission.correct
        )
        extra_guess_grant = ExtraGuessGrant.objects.filter(
            team_id=self.id, puzzle=puzzle
        ).first()  # will be model or None
        extra_guesses = extra_guess_grant.extra_guesses if extra_guess_grant else 0
        return MAX_GUESSES_PER_PUZZLE + extra_guesses - wrong_guesses

    def unlocked_rounds(self):
        """Returns all available rounds that have been unlocked."""
        rounds = Round.objects
        if not (self.is_internal or self.is_public):
            # self.rounds is a field on the spoilr team that is many-to-many through
            # the RoundAccess model.
            rounds = self.rounds
        return rounds.order_by("order")

    def unlock_story_cards(self, deep):
        """Unlocks and returns all available story cards to a team."""
        from .story import StoryCard, StoryCardAccess

        # Public access and internal teams should see all story cards
        if self.is_internal or self.is_public:
            return StoryCard.objects.order_by("order")

        # TODO: Unlock story cards by deep
        return [
            access.story_card
            for access in StoryCardAccess.objects.filter(team=self)
            .select_related("story_card")
            .select_related("story_card__puzzle")
            .select_related("story_card__puzzle__round")
            .order_by("story_card__order")
        ]

    def unlock_puzzles(self, deep):
        """Unlocks available puzzles to this team."""
        # Internal users should see all puzzles.
        if self.is_internal or self.is_public:
            return list(Puzzle.objects.all())

        # Otherwise, iterate through what the team can access.
        puzzles = []
        unlocked_ids = set()
        for access in self.puzzleaccess_set.all():
            puzzle = access.puzzle.puzzle
            puzzles.append(puzzle)
            unlocked_ids.add(puzzle.id)
        unlocked_round_slugs = set()
        for round in self.unlocked_rounds():
            unlocked_round_slugs.add(round.slug)

        # Round order must be 1st because later code relies on insertion order
        # of the puzzles dict.
        # Deep_key then deep is done such that for a given key, we see all unlocked
        # puzzles then locked ones in order of round progress - this is needed for
        # event unlocks to work.
        # Slug is included because it enforces a consistent ordering in the case of
        # deep ties, which is needed for event unlock functionality.
        all_puzzles = Puzzle.objects.order_by(
            "round__order", "deep_key", "deep", "slug"
        )
        extra_unlocks = collections.defaultdict(int)
        for eu in ExtraUnlock.objects.filter(team=self):
            extra_unlocks[eu.deep_key] = eu.count
        extra_count = collections.defaultdict(int)
        # Consider if we put in work to let us stop checking early - would need to order
        # by (deep_key, deep) but requires resolving deep_key for everything and may not
        # be as flexible.
        for round_slug, puzzles_by_round in groupby(
            all_puzzles, lambda p: p.round.slug
        ):
            for puzzle in puzzles_by_round:
                deep_key = puzzle.deep_key or round_slug
                if puzzle.deep > max(deep[deep_key], deep.get("all", -math.inf)):
                    # Let first N puzzles proceed to unlocking code.
                    extra_count[deep_key] += 1
                    if extra_count[deep_key] > extra_unlocks[deep_key]:
                        continue

                if puzzle.id not in unlocked_ids:
                    release_puzzle(self, puzzle)
                    puzzles.append(puzzle)
                if round_slug not in unlocked_round_slugs:
                    release_round(self, puzzle.round)
                    unlocked_round_slugs.add(round_slug)

        return puzzles

    def compute_next_event_unlocks(self, deep):
        """Generate a list of puzzles that might be the next event unlock.
        This is computed based on deep, ignoring any PuzzleAccess objects,
        such that the first N are always the puzzles that event unlocks
        should trigger.

        As an implication it means that we should always do time unlocks
        based on deep or event unlocks.
        """
        from puzzles.rounds.utils import SKIP_ROUNDS

        # Only allowed to use an event unlock if we have already unlocked
        # that round. Be permissive first then filter it down later.
        # (This code assumes a RoundAccess won't be created until we've unlocked
        # at least 1 puzzle in that round.)
        eligible_rounds = set()
        for round in self.unlocked_rounds():
            eligible_rounds.add(round.slug)
            if round.superround:
                eligible_rounds.add(round.superround.slug)
        rounds_to_exclude = {
            *SKIP_ROUNDS,
        }
        eligible_rounds = eligible_rounds - rounds_to_exclude
        # Iterate through all puzzles by deep_key then deep to guarantee list is
        # sorted order, with slug to get a consistent order if there are ties.
        #
        # Potential puzzles = puzzles that are not already unlocked by deep which
        #  could be unlocked by an event unlock. This needs to be based on deep
        #  rather than PuzzleAccess.
        potential_puzzles = (
            Puzzle.objects.select_related("round")
            .filter(round__slug__in=eligible_rounds, is_meta=False)
            .order_by("round__order", "deep_key", "deep", "slug")
        )
        locked_puzzles = collections.defaultdict(list)
        dk_display_name = {}
        all_display_name = {}
        for puzzle in potential_puzzles:
            deep_key = puzzle.deep_key or puzzle.round.slug
            if not (
                deep_key == puzzle.round.slug
                or (
                    puzzle.round.superround and deep_key == puzzle.round.superround.slug
                )
            ):
                # Weird deep_key, ignore it.
                continue
            # Bad copy-paste for speed. May not need to be implemented this way?
            # Always populate all keys for display names
            # need to be able to display round name if they have used an unlock in a round,
            # and now have nothing left in that round.
            if deep_key != puzzle.round.slug:
                # This case can only occur if superround.
                all_display_name[deep_key] = puzzle.round.superround.name
            else:
                all_display_name[deep_key] = puzzle.round.name
            if puzzle.deep > deep[deep_key]:
                if deep_key != puzzle.round.slug:
                    # This case can only occur if superround.
                    dk_display_name[deep_key] = puzzle.round.superround.name
                else:
                    dk_display_name[deep_key] = puzzle.round.name
                locked_puzzles[deep_key].append(puzzle)
        # These checks shouldn't be necessary if we set up puzzle fixtures
        # correctly, but we set them here anyways.
        # If a team has used N extra unlocks, the locked-puzzles list will have N puzzles,
        # we need to filter the list appropriately.
        # It is important to not check this against PuzzleUnlock objects to enforce the
        # invariant of "deep + N extra"
        extra_unlocks = collections.defaultdict(int)
        for eu in ExtraUnlock.objects.filter(team=self):
            extra_unlocks[eu.deep_key] = eu.count
        unlocked_all = [
            dk for dk in locked_puzzles if len(locked_puzzles[dk]) <= extra_unlocks[dk]
        ]
        for bad_dk in unlocked_all:
            del locked_puzzles[bad_dk]
            del dk_display_name[bad_dk]
        return locked_puzzles, dk_display_name, all_display_name


class PuzzleAccess(spoilr.core.models.PuzzleAccess):
    """
    Represents a team having access to a puzzle (and when that occurred)
    Equivalent to PuzzleAccess in spoilr.
    """

    # Overrides the get_queryset in SpoilrPuzzleAccessManager
    objects = models.Manager()

    class Meta:
        proxy = True


class PuzzleSubmission(spoilr.core.models.PuzzleSubmission):
    """
    Represents a team making a solve attempt on a puzzle (right or wrong).
    Extends PuzzleSubmission in spoilr.
    """

    # this just renames the parent_link for the multi-table inheritance
    spoilr_submission = models.OneToOneField(
        spoilr.core.models.PuzzleSubmission,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
    )

    used_free_answer = models.BooleanField()

    def __str__(self):
        return "%s -> %s: %s, %s" % (
            self.team,
            self.puzzle,
            self.answer,
            "correct" if self.correct else "wrong",
        )


def build_guess_data(answer_submission):
    """Returns serialized data for a particular answer submission."""
    from puzzles.views.puzzles import weaver

    if answer_submission.correct:
        response = "Correct!"
    else:
        response = "Incorrect"
    partial = False
    puzzle = answer_submission.puzzle.puzzle
    for message in puzzle.pseudoanswer_set.all():
        if answer_submission.answer == puzzle.normalize_answer(message.answer):
            response = message.response
            partial = True
            break
    if puzzle.slug == "weaver":
        partial_message = weaver.get_partial_answer_message(answer_submission.answer)
        if partial_message is not None:
            response = partial_message
            partial = True

    return {
        "timestamp": str(answer_submission.timestamp or timezone.now()),
        "guess": answer_submission.answer,
        "response": response,
        "isCorrect": answer_submission.correct,
        "partial": partial,
    }


class Minipuzzle(spoilr.core.models.Minipuzzle):
    SINGLETON_REF = "singleton"

    @classmethod
    def singleton(cls, team: Team, puzzle: Puzzle) -> "Minipuzzle":
        """Create or get the singleton minipuzzle for this team on a given puzzle"""
        obj, _ = cls.objects.get_or_create(
            team=team,
            puzzle=puzzle,
            ref=cls.SINGLETON_REF,
        )
        return obj

    class Meta:
        proxy = True


class CustomPuzzleSubmission(spoilr.core.models.MinipuzzleSubmission):
    """Represents a team entering an intermediary submission to an interactive puzzle."""

    # this just renames the parent_link for the multi-table inheritance
    minipuzzle_submission = models.OneToOneField(
        spoilr.core.models.MinipuzzleSubmission,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
    )

    count = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.team} -> {self.puzzle} ({self.minipuzzle}): {self.raw_answer} ({self.count})"

    @classmethod
    def increment(
        cls,
        team: Team,
        puzzle: Puzzle,
        raw_answer: str,
        minipuzzle: Optional[Minipuzzle] = None,
        correct=False,
    ) -> None:
        # If it doesn't exist, create a new submission with count 1.
        minipuzzle = minipuzzle or Minipuzzle.singleton(team, puzzle)
        _, created = cls.objects.get_or_create(
            team=team,
            puzzle=puzzle,
            minipuzzle=minipuzzle,
            raw_answer=raw_answer,
            defaults={
                "count": 1,
                "correct": correct,
            },
        )
        # If it already exists, update it to current count + 1.
        if not created:
            cls.objects.filter(
                team=team, puzzle=puzzle, minipuzzle=minipuzzle, raw_answer=raw_answer
            ).update(count=F("count") + 1)

    @classmethod
    def histogram(cls, puzzle: Puzzle):
        return (
            cls.objects.filter(puzzle=puzzle, timestamp__lt=get_site_end_time())
            .values("raw_answer")
            .annotate(counts=Sum("count"))
        )

    @classmethod
    def histogram_by_minipuzzle(cls, puzzle: Puzzle):
        return (
            cls.objects.filter(puzzle=puzzle, timestamp__lt=get_site_end_time())
            .values("raw_answer", "minipuzzle")
            .annotate(counts=Sum("count"))
        )

    @classmethod
    def histogram_by_team(cls, puzzle: Puzzle):
        return (
            cls.objects.filter(puzzle=puzzle, timestamp__lt=get_site_end_time())
            .values("raw_answer", "team")
            .annotate(counts=Sum("count"))
        )


# Sends a Discord alert, we'll construct the finisher emails manually.
def handle_victory(submission):
    if submission.correct and submission.puzzle.slug == DONE_SLUG:
        team = submission.team
        emails = team.all_emails
        dispatch_victory_alert(
            "Team **%s** has finished the clickaround!" % team
            + "\n**Emails:** "
            + ", ".join(emails)
        )


class ExtraGuessGrant(models.Model):
    """Extra guesses granted to a particular team."""

    NO_RESPONSE = "NR"
    GRANTED = "GR"

    STATUSES = {
        NO_RESPONSE: "No response",
        GRANTED: "Granted",
    }

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    status = models.CharField(
        choices=tuple(STATUSES.items()), default=NO_RESPONSE, max_length=3
    )

    extra_guesses = models.IntegerField(default=20)

    def __str__(self):
        return "%s has %d extra guesses for puzzle %s" % (
            self.team,
            self.extra_guesses,
            self.puzzle,
        )

    def granted_discord_message(self):
        return f"{self.team} was granted {self.extra_guesses} guesses on {self.puzzle.emoji} {self.puzzle}"

    def requested_discord_message(self):
        hint_answer_url = generate_url(
            "internal", f"/internal/extraguessgrant/{self.id}"
        )
        return (
            f"{self.team} is rate-limited on {self.puzzle.puzzle.emoji} {self.puzzle} and requested more guesses. "
            f"You may view past guesses and approve or deny the request here:\n"
            f"{hint_answer_url}\n"
            f"React to this Discord message when done."
        )

    class Meta:
        unique_together = ("team", "puzzle")


class RatingField(models.PositiveSmallIntegerField):
    """Represents a single numeric rating (either fun or difficulty) of a puzzle."""

    def __init__(self, max_rating, adjective, **kwargs):
        self.max_rating = max_rating
        self.adjective = adjective
        super().__init__(**kwargs)

    def formfield(self, **kwargs):
        choices = [(i, i) for i in range(1, self.max_rating + 1)]
        return super().formfield(
            **{
                "min_value": 1,
                "max_value": self.max_rating,
                "widget": forms.RadioSelect(
                    choices=choices,
                    attrs={"adjective": self.adjective},
                ),
                **kwargs,
            }
        )

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["max_rating"] = self.max_rating
        kwargs["adjective"] = self.adjective
        return name, path, args, kwargs


class Survey(models.Model):
    """A rating given by a team to a puzzle after solving it."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)

    fun = RatingField(6, "fun")
    difficulty = RatingField(6, "hard")
    comments = models.TextField(blank=True, verbose_name="Anything else:")

    def __str__(self):
        return "%s: %s" % (self.puzzle, self.team)

    class Meta:
        unique_together = ("team", "puzzle")

    @classmethod
    def fields(cls):
        return [
            field for field in cls._meta.get_fields() if isinstance(field, RatingField)
        ]


class Feedback(models.Model):
    """A rating given by a team to a puzzle after solving it."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)

    comments = models.TextField(blank=True)

    def __str__(self):
        return "%s: %s" % (self.puzzle, self.team)


class DeepFloor(models.Model):
    """Minimum deep to make it easier to locally unlock rounds."""

    team = models.ForeignKey(
        Team,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text="The team to create a time unlock for, leaving it blank will apply it to all teams.",
    )
    # A team may not want time unlocks, allows for self-serve.
    enabled = models.BooleanField(default=False)
    # Used in URL emailed to team, expected to be randomly generated.
    # Unlike the team state, this is entirely controlled by the server rather than
    # the browser, so we can generate it
    uuid = models.CharField(default=random_uuid, max_length=64)
    # This is not unique for (team, deep_key) to handle the case where a team may
    # accept a time unlock the 1st time and reject it the 2nd - this is easier to
    # manage if we assume multiple instances can exist and we resolve it later.
    deep_key = models.CharField(max_length=500, verbose_name="DEEP key")
    min_deep = models.IntegerField(verbose_name="min DEEP")
    timestamp = models.DateTimeField(auto_now_add=True)


class ExtraUnlock(models.Model):
    """Tracks where a team has used event unlocks."""

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
    )
    deep_key = models.CharField(max_length=500, verbose_name="DEEP key")
    # Same key can be used multiple times.
    count = models.PositiveIntegerField(default=1)

    @classmethod
    def increment(
        cls,
        team: Team,
        deep_key: str,
    ) -> None:
        # If it doesn't exist, create a new ExtraUnlock with count 1.
        _, created = cls.objects.get_or_create(
            team=team,
            deep_key=deep_key,
            defaults={
                "count": 1,
            },
        )
        # If it already exists, update it to current count + 1.
        if not created:
            cls.objects.filter(
                team=team,
                deep_key=deep_key,
            ).update(count=F("count") + 1)

    class Meta:
        unique_together = ("team", "deep_key")
