import datetime
import distutils.util
import email
import email.headerregistry
import email.policy
import enum
import html
import os
import re
from collections import defaultdict
from urllib.parse import quote
from uuid import uuid4

import dateutil.parser
import html2text
import pytz
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.db.models import Case, Exists, F, OuterRef, Q, Subquery, Sum, When
from django.db.models.functions import FirstValue
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils import timezone
from django_extensions.db.fields import AutoSlugField
from puzzles.celery import celery_app
from puzzles.consumers import ClientConsumer
from puzzles.context import context_cache
from puzzles.hunt_config import (
    DAYS_BEFORE_FREE_ANSWERS,
    DAYS_BEFORE_HINTS,
    DEEP_MAX,
    FREE_ANSWERS_PER_DAY,
    HUNT_END_TIME,
    HUNT_START_TIME,
    INTRO_HINTS,
    INTRO_META_SLUGS,
    INTRO_ROUND,
    MAIN_ROUND_META_SLUGS,
    MAIN_ROUNDS,
    MAX_GUESSES_PER_PUZZLE,
    META_META_SLUG,
    TEAM_AGE_BEFORE_HINTS,
    TIME_UNLOCKS,
)
from puzzles.messaging import (
    dispatch_bot_alert,
    dispatch_email_alert,
    dispatch_extra_guess_alert,
    dispatch_free_answer_alert,
    dispatch_general_alert,
    dispatch_hint_alert,
    dispatch_spoiler_alert,
    dispatch_submission_alert,
    dispatch_victory_alert,
    send_mail_wrapper,
)
from pwreset.models import Token
from tph.utils import generate_url


# FIXME: replace with new round structure.
@enum.unique
class Dimension(enum.Enum):
    INTRO = "i"
    MATT = "m"
    EMMA = "e"

    @classmethod
    def from_round(cls, puzzle_round: str):
        try:
            return cls[puzzle_round.upper()]
        except KeyError:
            return cls.INTRO


@enum.unique
class Round(enum.Enum):
    INTRO = "i"
    MATT = "m"
    EMMA = "e"
    # Final meta
    META = "z"

    @classmethod
    def from_round(cls, puzzle_round: str):
        try:
            return cls[puzzle_round.upper()]
        except KeyError:
            return cls.INTRO


def get_dimension(request, team) -> Dimension:
    # Must be logged in to see dimensions.
    if not team:
        return Dimension.INTRO

    try:
        return Dimension(request.COOKIES.get("dim", "i"))
    except ValueError:
        return Dimension.INTRO


class SlugManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class SlugModel(models.Model):
    objects = SlugManager()

    def natural_key(self):
        return (self.slug,)

    class Meta:
        abstract = True


class StoryCard(SlugModel):
    """Story text we want to be displayed.

    This represents the story text, puzzle, and unlock mechanism for the story
    information. However, for a given team, auth is handled by the StoryCardUnlock
    model.
    """

    def create_image_filename(instance, filename):
        _, extension = os.path.splitext(filename)
        return f"site/story/{instance.slug}/story_{uuid4().hex}{extension}"

    text = models.TextField(blank=True)
    slug = models.SlugField(max_length=500, unique=True)
    deep = models.IntegerField(default=0)
    # Distinct from deep, which is solely used for unlocking.
    unlock_order = models.IntegerField(default=0)
    min_main_round_solves = models.IntegerField(default=0)

    # Image to display.
    image = models.ImageField(
        upload_to=create_image_filename, max_length=300, blank=True
    )

    puzzle = models.ForeignKey(
        "Puzzle",
        on_delete=models.CASCADE,
        related_name="story_cards",
        null=True,
        blank=True,
    )
    # If false, unlocks when puzzle is unlocked. Otherwise, unlocks when puzzle is solved.
    unlocks_post_solve = models.BooleanField(default=False)

    def get_image_url(self, dimension):
        image = self.image
        return os.path.join(settings.MEDIA_URL, image.name) if image else None

    def __str__(self):
        def abbr(s):
            if len(s) > 50:
                return s[:50] + "..."
            return s

        return f"[{self.slug}]: {abbr(self.text)}"


class Puzzle(SlugModel):
    """A single puzzle in the puzzlehunt."""

    name = models.CharField(max_length=500)

    # slug used in URLs to identify this puzzle
    slug = models.SlugField(max_length=500, unique=True)

    # answer (fine if unnormalized)
    answer = models.CharField(max_length=500)

    # progress threshold to unlock this puzzle
    deep = models.IntegerField(verbose_name="DEEP threshold")
    metameta_deep = models.IntegerField(
        default=0, verbose_name="Metameta DEEP threshold"
    )

    # indicates if this puzzle is a metapuzzle
    is_meta = models.BooleanField(default=False)

    def create_icon_filename(instance, filename):
        # Place all icons under a common "icons" subdir for easier management.
        _, extension = os.path.splitext(filename)
        return f"site/icons/{instance.slug}/icon_{uuid4().hex}{extension}"

    # puzzle icon and position (x, y) -- offset from center
    unsolved_icon = models.ImageField(
        upload_to=create_icon_filename, max_length=300, blank=True
    )
    # Icons for the solved version of each puzzle, for the "default" round (the round the puzzle
    # is in)
    solved_icon = models.ImageField(
        upload_to=create_icon_filename, max_length=300, blank=True
    )
    # And then intro puzzles have a different unsolved icon in the main round.
    main_unsolved_icon = models.ImageField(
        upload_to=create_icon_filename, max_length=300, blank=True
    )
    # And then some puzzles will also have a background icon. This has to be a
    # FileField because ImageField does not support SVG
    bg_icon = models.FileField(
        upload_to=create_icon_filename,
        max_length=300,
        blank=True,
        validators=[FileExtensionValidator(["png", "jpg", "jpeg", "svg"])],
    )

    # Icon position is offset from center (%) in intro round and /1000 in main round.
    icon_x = models.IntegerField(default=0)
    icon_y = models.IntegerField(default=0)
    icon_size = models.IntegerField(default=0)
    text_x = models.IntegerField(default=0)
    text_y = models.IntegerField(default=0)

    # all metas that this puzzle is part of
    metas = models.ManyToManyField(
        "self", limit_choices_to={"is_meta": True}, symmetrical=False, blank=True
    )

    # used in Discord integrations involving this puzzle
    emoji = models.CharField(max_length=500, default=":question:")

    # whether the puzzle is intro or main round
    round = models.CharField(max_length=500, default="main")

    # URL for testsolving (make sure this is empty before releasing!)
    testsolve_url = models.CharField(max_length=500, null=True, blank=True)

    # number of points contributed to leaderboard
    # despite "positive", it actually allows 0 points for hidden puzzles.
    points = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return self.name

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
    def normalized_answer(self):
        return Puzzle.normalize_answer(self.answer)

    @staticmethod
    def normalize_answer(s):
        return s and re.sub(r"[^A-Z]", "", s.upper())

    def is_intro(self):
        """Is this puzzle in the intro round?"""
        return self.round == INTRO_ROUND

    @property
    def solution_slug(self):
        return self.slug


@context_cache
class Team(models.Model):
    """
    A team participating in the puzzlehunt.

    This model has a one-to-one relationship to Users -- every User created
    through the register flow will have a "Team" created for them.
    """

    # The associated User -- note that not all users necessarily have an
    # associated team.
    user = models.OneToOneField(User, on_delete=models.PROTECT)

    # Public team name for scoreboards and comms -- not necessarily the same as
    # the user's name from the User object
    team_name = models.CharField(max_length=100, unique=True)

    # Public slug for use in URLs (autogenerated from team_name) -- not
    # necessarily the same as the user's username from the User object
    slug = AutoSlugField(max_length=100, unique=True, populate_from=("team_name",))

    def user_profile_filename(instance, filename):
        _, extension = os.path.splitext(filename)
        return f"team/{instance.user.username}/profile_picture{extension}"

    def user_profile_victory_filename(instance, filename):
        _, extension = os.path.splitext(filename)
        return f"team/{instance.user.username}/profile_picture_victory{extension}"

    # Optional profile picture for team, displayed on their team page.
    profile_pic = models.ImageField(
        upload_to=user_profile_filename, max_length=300, blank=True
    )
    profile_pic_victory = models.ImageField(
        upload_to=user_profile_victory_filename, max_length=300, blank=True
    )

    # Whether profile picture is allowed.
    profile_pic_approved = models.BooleanField(default=False)

    # Time of creation of team
    creation_time = models.DateTimeField(auto_now_add=True)

    # How much earlier this team should start, for early-testing teams
    # Be careful with this!
    start_offset = models.DurationField(default=datetime.timedelta)

    # Number of additional hints to award the team, on top of the 2 per day
    total_hints_awarded = models.IntegerField(default=0)
    total_free_answers_awarded = models.IntegerField(default=0)

    # Last solve time
    last_solve_time = models.DateTimeField(null=True, blank=True)

    # If true, team will have access to puzzles before the hunt starts
    is_prerelease_testsolver = models.BooleanField(default=False)

    # If true, team will not be visible to the public
    is_hidden = models.BooleanField(default=False)

    def __str__(self):
        return self.team_name

    def team_url(self):
        return generate_url(f"/team/{quote(self.team_name)}")

    def get_emails(self, with_names=False):
        return [
            ((member.email, str(member)) if with_names else member.email)
            for member in self.teammember_set.all()
            if member.email
        ]

    def get_members(self, with_emails=False):
        if with_emails:
            return [
                {
                    "name": member.name,
                    "email": member.email,
                    "rejected": member.reason,
                }
                for member in self.teammember_set.annotate(
                    reason=Subquery(
                        BadEmailAddress.objects.filter(email=OuterRef("email")).values(
                            "reason"
                        )[:1]
                    )
                )
            ]
        return [{"name": member.name} for member in self.teammember_set.all()]

    def puzzle_submissions(self, puzzle):
        return [
            submission for submission in self.submissions if submission.puzzle == puzzle
        ]

    def puzzle_answer(self, puzzle):
        return (
            puzzle.answer
            if any(
                submission.is_correct for submission in self.puzzle_submissions(puzzle)
            )
            else None
        )

    def guesses_remaining(self, puzzle):
        wrong_guesses = sum(
            1
            for submission in self.puzzle_submissions(puzzle)
            if not submission.is_correct
        )
        extra_guess_grant = ExtraGuessGrant.objects.filter(
            team=self, puzzle=puzzle
        ).first()  # will be model or None
        extra_guesses = extra_guess_grant.extra_guesses if extra_guess_grant else 0
        return MAX_GUESSES_PER_PUZZLE + extra_guesses - wrong_guesses

    @staticmethod
    def leaderboard(current_team):
        """
        Returns a list of all teams in order they should appear on the
        leaderboard. Some extra fields are annotated to each team:
          - is_current: true if the team is the current team
          - total_solves: number of non-free solves (before hunt end)
          - last_solve_time: last non-free solve (before hunt end)
          - metameta_solve_time: time of finishing the hunt (if before hunt end)
        This depends on the viewing team for hidden teams
        """
        q = Q(is_hidden=False)
        if current_team:
            q |= Q(id=current_team.id)

        all_teams = Team.objects.filter(q, creation_time__lt=HUNT_END_TIME)

        total_solves = defaultdict(int)
        meta_times = {}
        for team_id, slug, time in AnswerSubmission.objects.filter(
            used_free_answer=False,
            is_correct=True,
            submitted_datetime__lt=HUNT_END_TIME,
        ).values_list("team_id", "puzzle__slug", "submitted_datetime"):
            total_solves[team_id] += 1
            if slug == META_META_SLUG:
                meta_times[team_id] = time

        # For testing teams, last_solve_time can be defined, even if they have
        # 0 solves, depending on whether we cleaned the field up correctly. To
        # avoid weird reporting, ignore it if it's set for teams with 0 solves.
        sorted_teams = sorted(
            [
                {
                    "user_id": team.user_id,
                    "team_name": team.team_name,
                    "slug": team.slug,
                    "is_current": team == current_team,
                    "total_solves": total_solves[team.id],
                    "last_solve_time": None
                    if total_solves[team.id] == 0
                    else team.last_solve_time,
                    "creation_time": team.creation_time,
                    "metameta_solve_time": meta_times.get(team.id),
                    "has_pic": team.profile_pic.name or team.profile_pic_victory.name,
                }
                for team in all_teams
            ],
            key=Team.team_sort_key,
        )
        return sorted_teams

    @staticmethod
    def team_sort_key(team_info):
        return (
            team_info["metameta_solve_time"] or HUNT_END_TIME,
            -team_info["total_solves"],
            team_info["last_solve_time"] or HUNT_END_TIME,
            team_info["creation_time"],
        )

    def team(self):
        return self

    def team_created_after_hunt_start(self):
        return max(0, (self.creation_time - self.start_time).days)

    def num_hints_total(self):  # used + remaining
        """
        Compute the total number of hints (used + remaining) available to this team.
        """
        now = min(self.now, HUNT_END_TIME)
        days_since_hunt_start = (now - self.start_time).days
        time_since_team_created = now - self.creation_time
        if time_since_team_created < TEAM_AGE_BEFORE_HINTS:
            # No hints available for first 2h
            return self.total_hints_awarded
        return (
            max(0, days_since_hunt_start - DAYS_BEFORE_HINTS + 1) * 2
            + self.total_hints_awarded
        )

    def num_hints_used(self):
        return (
            self.hint_set.filter(
                root_ancestor_request__isnull=True,
                is_request=True,
            )
            .exclude(status__in=(Hint.REFUNDED, Hint.OBSOLETE))
            .count()
        )

    def num_hints_remaining(self):
        return self.num_hints_total - self.num_hints_used

    def num_intro_hints_used(self):
        intro_used = (
            self.hint_set.filter(
                root_ancestor_request__isnull=True,
                is_request=True,
                puzzle__round=INTRO_ROUND,
            )
            .exclude(status__in=(Hint.REFUNDED, Hint.OBSOLETE))
            .count()
        )

        return min(INTRO_HINTS, intro_used)

    def num_intro_hints_remaining(self):
        return min(self.num_hints_remaining, INTRO_HINTS - self.num_intro_hints_used)

    def num_nonintro_hints_remaining(self):
        return self.num_hints_remaining - self.num_intro_hints_remaining

    def num_awarded_hints_remaining(self):
        return self.total_hints_awarded - self.num_hints_used

    def num_free_answers_total(self):
        days_since_hunt_start = (self.now - self.start_time).days
        if self.team_created_after_hunt_start >= DAYS_BEFORE_FREE_ANSWERS - 1:
            # No free answers at all for late-created teams.
            return 0
        return (
            sum(
                h
                for (i, h) in enumerate(FREE_ANSWERS_PER_DAY)
                if days_since_hunt_start >= DAYS_BEFORE_FREE_ANSWERS + i
            )
            + self.total_free_answers_awarded
        )

    def num_free_answers_used(self):
        return sum(1 for submission in self.submissions if submission.used_free_answer)

    def num_free_answers_remaining(self):
        return self.num_free_answers_total - self.num_free_answers_used

    def submissions(self):
        return tuple(
            self.answersubmission_set.select_related("puzzle")
            .prefetch_related(
                "puzzle__metas",
                "puzzle__puzzlemessage_set",
            )
            .order_by("-submitted_datetime")
        )

    def solves(self):
        return {
            submission.puzzle_id: submission.puzzle
            for submission in self.submissions
            if submission.is_correct
        }

    def db_unlocks(self):
        return tuple(
            self.puzzleunlock_set.select_related("puzzle").order_by("-unlock_datetime")
        )

    def db_story_unlocks(self):
        # Returns unlocked story cards from earliest to latest (deep). Note this is opposite of puzzle unlocks!
        # Excludes story cards with deep <= 0 because these are always shown.
        return tuple(
            self.storycardunlock_set.filter(story_card__deep__gt=0)
            .order_by(
                "story_card__deep", "story_card__unlock_order", "story_card__slug"
            )
            .select_related("story_card")
            .select_related("story_card__puzzle")
        )

    def unlock_puzzle(self, context, puzzle):
        # Don't create if it already exists, in case of a race condition with another teammate.
        unlock, created = PuzzleUnlock.objects.get_or_create(team=self, puzzle=puzzle)
        if created and not context.hunt_has_started:
            # Set the unlock time to the start time.
            unlock.unlock_datetime = context.start_time
            unlock.save()

        # If this puzzle was newly unlocked and it has a StoryCard, unlock that too.
        if created:
            for story_card in puzzle.story_cards.filter(unlocks_post_solve=False):
                StoryCardUnlock.objects.get_or_create(team=self, story_card=story_card)

    @staticmethod
    def compute_solves_per_round(context):
        """Computes number of regular puzzle solves per round.

        This excludes metas solved in that round. Those should be checked
        separately.
        """
        solves_dict = defaultdict(int)
        if not context.team:
            return solves_dict
        for _, puzzle in context.team.solves.items():
            if puzzle.slug in MAIN_ROUND_META_SLUGS:
                continue
            if puzzle.slug in INTRO_META_SLUGS:
                continue
            solves_dict[puzzle.round] += 1
        return solves_dict

    @classmethod
    def has_unlocked_main_round(cls, context):
        # TODO: keep performant while not requiring being synced with fixtures
        return cls.compute_deep(context) >= 100

    @classmethod
    def has_unlocked_final_meta(cls, context):
        # TODO: keep performant while not requiring being synced with fixtures
        return cls.compute_metameta_deep(context) >= 100

    @staticmethod
    def compute_deep(context):
        if context.hunt_is_prereleased or context.hunt_is_closed:
            return DEEP_MAX
        # Time unlocks do not apply unless you are logged in.
        if context.team is None:
            if context.hunt_is_over:
                return DEEP_MAX
            return 0
        if context.is_superuser:
            return DEEP_MAX

        # FIXME: implement deep
        return 10

    @staticmethod
    def compute_metameta_deep(context):
        # This is basically a binary condition, but to reflect the condition,
        # setting the deep to 100000 if met.
        if context.hunt_is_prereleased or context.hunt_is_closed:
            return DEEP_MAX
        if context.team is None:
            if context.hunt_is_over:
                return DEEP_MAX
            return 0
        if context.is_superuser:
            return DEEP_MAX

        # FIXME: implement
        return 0

    # NOTE: This method creates unlocks with the current time; in other words,
    # time-based unlocks are not correctly backdated. This is because the DEEP
    # over time algorithm is nonlinear and unlocks are not important enough to
    # warrant calculating the inverse function. This method will be called the
    # next time a puzzle or the puzzles list is loaded, so solvers should not
    # be affected, but it may be worth keeping in mind if you're doing analysis.
    @staticmethod
    def compute_puzzle_unlocks(context):
        team = context.team
        deep = context.deep
        metameta_deep = context.metameta_deep

        unlocks = None
        if team and not team.is_prerelease_testsolver:
            unlocks = {unlock.puzzle_id for unlock in team.db_unlocks}

        out = {"puzzles": [], "ids": set(), "story": []}
        for puzzle in context.all_puzzles:
            if puzzle.deep > deep:
                # We can break early since all_puzzles is ordered by deep
                break
            # Check the non-standard deeps and continue if not met.
            if puzzle.metameta_deep > metameta_deep:
                continue
            # We're going to unlock.
            if deep != DEEP_MAX and unlocks is not None and puzzle.id not in unlocks:
                team.unlock_puzzle(context, puzzle)

            out["puzzles"].append({"puzzle": puzzle})
            out["ids"].add(puzzle.id)

        return out

    @staticmethod
    def compute_story_unlocks(context):
        team = context.team
        deep = context.deep
        metameta_deep = context.metameta_deep

        out = {"story": []}

        story_unlocks = set()
        # Always show story cards with deep <= 0.
        for story_card in StoryCard.objects.filter(deep__lte=0).select_related(
            "puzzle"
        ):
            story_unlocks.add(story_card.id)
            out["story"].append(story_card)

        if team and not team.is_prerelease_testsolver:
            for story_unlock in team.db_story_unlocks:
                story_unlocks.add(story_unlock.story_card_id)
                out["story"].append(story_unlock.story_card)

        # Check all story not tied to a puzzle to see if it should be unlocked.
        # Note: It is important that this checks story unlocks in increasing deep order.
        # This guarantees that if muliple conditions are met, the "latest" one is added last.
        # This happens when the last main round meta is solved, which triggers both the meta
        # solve and metameta unlock events.
        if (team and context.hunt_has_started) or context.hunt_is_over:
            if (context.hunt_is_over and not team) or context.is_superuser:
                # Logged-out teams or superusers get infinite deep for story unlocks.
                deep = DEEP_MAX

            for story in context.all_story:
                if story.deep > deep:
                    # We can break early since all_story is ordered by deep
                    break
                if story.id in story_unlocks:
                    continue

                # If it has a puzzle, it will be unlocked by the puzzle logic.
                # See the unlock_puzzle and process_guess methods.
                if story.puzzle_id and deep != DEEP_MAX:
                    continue

                # Looks good, we're going to unlock.
                # Note that unlike puzzles, the order of the list is important, so we need to use
                # slightly different logic.
                if deep != DEEP_MAX:
                    # Don't create if it's already created.
                    StoryCardUnlock.objects.get_or_create(team=team, story_card=story)
                # If deep == DEEP_MAX, this will make story viewable without
                # adding a story unlock to the DB (true for testing teams and
                # teams in a post-hunt state.)

                out["story"].append(story)
        return out


@receiver(post_save, sender=Token)
def send_password_reset_email(sender, instance: Token, created: bool, **kwargs):
    if created:
        team = instance.user.team
        url = generate_url(
            "/reset_password",
            {"token": instance.token, "username": instance.user.username},
        )
        send_mail_wrapper(
            "Password reset requested",
            "password_reset_email",
            {"team_name": team.team_name, "reset_link": url},
            team.get_emails(),
        )


@receiver(post_save, sender=Team)
def notify_on_team_creation(sender, instance, created, **kwargs):
    if created:
        dispatch_general_alert(f"Team created: {instance.team_name}")


class TeamMember(models.Model):
    """A person on a team."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.email})" if self.email else self.name


class PuzzleUnlock(models.Model):
    """Represents a team having access to a puzzle (and when that occurred)."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)

    unlock_datetime = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.team} -> {self.puzzle} @ {self.unlock_datetime}"

    class Meta:
        unique_together = ("team", "puzzle")


class AnswerSubmission(models.Model):
    """Represents a team making a solve attempt on a puzzle (right or wrong)."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)

    submitted_answer = models.CharField(max_length=500)
    is_correct = models.BooleanField()
    submitted_datetime = models.DateTimeField(auto_now_add=True)
    used_free_answer = models.BooleanField()

    def __str__(self):
        return "%s -> %s: %s, %s" % (
            self.team,
            self.puzzle,
            self.submitted_answer,
            "correct" if self.is_correct else "wrong",
        )

    class Meta:
        unique_together = ("team", "puzzle", "submitted_answer")


def build_guess_data(answer_submission, include_partial=False):
    """Returns serialized data for a particular answer submission."""
    if answer_submission.is_correct:
        response = "Correct!"
    else:
        response = "Incorrect"
    partial = False
    for message in answer_submission.puzzle.puzzlemessage_set.all():
        if answer_submission.submitted_answer == message.semicleaned_guess:
            response = message.response
            partial = True
            break

    result = {
        "timestamp": str(answer_submission.submitted_datetime),
        "guess": answer_submission.submitted_answer,
        "response": response,
        "isCorrect": answer_submission.is_correct,
    }
    if include_partial:
        result["partial"] = partial
    return result


@receiver(post_save, sender=AnswerSubmission)
def notify_on_answer_submission(sender, instance, created, **kwargs):
    if created:
        now = timezone.localtime()
        guess_data = build_guess_data(instance, include_partial=True)
        guess_data["puzzle"] = instance.puzzle.slug
        partial = guess_data.pop("partial")

        def format_time_ago(timestamp):
            if not timestamp:
                return ""
            diff = now - timestamp
            parts = ["", "", "", ""]
            if diff.days > 0:
                parts[0] = "%dd" % diff.days
            seconds = diff.seconds
            parts[3] = "%02ds" % (seconds % 60)
            minutes = seconds // 60
            if minutes:
                parts[2] = "%02dm" % (minutes % 60)
                hours = minutes // 60
                if hours:
                    parts[1] = "%dh" % hours
            return " {} ago".format("".join(parts))

        hints = list(
            Hint.objects.filter(
                team=instance.team, puzzle=instance.puzzle, is_request=True
            ).select_related("response")
        )
        hint_line = ""
        if hints:
            hint_line = "\nHints:" + ",".join(
                "%s (%s%s)"
                % (
                    format_time_ago(hint.submitted_datetime),
                    hint.status,
                    format_time_ago(
                        hint.response.submitted_datetime
                        if hint.response is not None
                        else None
                    ),
                )
                for hint in hints
            )
        if instance.used_free_answer:
            dispatch_free_answer_alert(
                ":question: {} Team **{}** used a free answer on {}!{}".format(
                    instance.puzzle.emoji, instance.team, instance.puzzle, hint_line
                )
            )
        else:
            sigil = ":x:"
            if instance.is_correct:
                sigil = {
                    1: ":first_place:",
                    2: ":second_place:",
                    3: ":third_place:",
                }.get(
                    AnswerSubmission.objects.filter(
                        puzzle=instance.puzzle,
                        is_correct=True,
                        used_free_answer=False,
                        team__is_hidden=False,
                    ).count(),
                    ":white_check_mark:",
                )
            # Determine the message reply.
            # Since we need to filter on the semicleaned_guess which is a Python
            # property, we can't use Django filters for that field. Loading all
            # the messages should be fine though, there are very few for each
            # puzzle.
            discord_message = "Correct!" if instance.is_correct else "Incorrect!!"
            discord_username = "TPH WinBot" if instance.is_correct else "TPH FailBot"
            if partial:
                discord_message = guess_data["response"]
                # If we have custom messages for success, do not change to
                # right arrow for correct guesses.
                if not instance.is_correct:
                    discord_username = "TPH KeepGoingBot"
                    sigil = ":arrow_right:"
            if not instance.team.is_hidden:
                dispatch_submission_alert(
                    "{} {} Team **{}** submitted `{}` for {}: {}{}".format(
                        sigil,
                        instance.puzzle.emoji,
                        instance.team,
                        instance.submitted_answer,
                        instance.puzzle,
                        discord_message,
                        hint_line,
                    ),
                    username=discord_username,
                )

        from puzzles.views.puzzles import get_ratelimit

        ratelimit_data = get_ratelimit(instance.puzzle, instance.team)
        websocket_data = {
            "puzzle": {
                "slug": instance.puzzle.slug,
                "name": instance.puzzle.name,
                "round": instance.puzzle.round,
            },
            "guess": guess_data,
            "rateLimit": ratelimit_data,
        }
        if instance.is_correct:
            channels_group = ClientConsumer.get_user_group(id=instance.team.user_id)
            if instance.puzzle.slug == META_META_SLUG:
                # order by negative deep and then reverse to grab just highest 2
                story_cards = StoryCard.objects.all().order_by("-deep")[:2:-1]
                if story_cards:
                    websocket_data["hasFinished"] = True
                    websocket_data["storycards"] = []
                    for story_card in story_cards:
                        websocket_data["storycards"].append(
                            {
                                "slug": story_card.slug,
                                "text": story_card.text,
                                "url": StoryCard.get_image_url(
                                    story_card, Dimension.INTRO
                                ),
                                "deep": story_card.deep,
                                "modal": True,
                            }
                        )
        else:
            channels_group = ClientConsumer.get_puzzle_group(
                id=instance.team.user_id, slug=instance.puzzle.slug
            )
        ClientConsumer.send_event(channels_group, "submission", websocket_data)

        if not instance.is_correct:
            return
        handle_victory(instance)

        obsolete_hints = Hint.objects.filter(
            team=instance.team,
            puzzle=instance.puzzle,
            status=Hint.NO_RESPONSE,
        )
        # Trigger postsave
        for hint in obsolete_hints:
            hint.status = Hint.OBSOLETE
            hint.save()


class CustomPuzzleSubmission(models.Model):
    """Represents a team entering an intermediary submission to an interactive puzzle."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)

    subpuzzle = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="The name of the subpuzzle this belongs to, if in a minihunt style puzzle.",
    )
    is_correct = models.BooleanField(default=False)

    submission = models.CharField(max_length=500)
    submitted_datetime = models.DateTimeField(auto_now_add=True, null=True)
    count = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.team} -> {self.puzzle} ({self.subpuzzle}): {self.submission} ({self.count})"

    class Meta:
        unique_together = ("team", "puzzle", "subpuzzle", "submission")

    @classmethod
    def increment(cls, team, puzzle, submission, subpuzzle=None, is_correct=False):
        # If it doesn't exist, create a new submission with count 1.
        _, created = cls.objects.get_or_create(
            team=team,
            puzzle=puzzle,
            subpuzzle=subpuzzle,
            submission=submission,
            defaults={
                "count": 1,
                "is_correct": is_correct,
            },
        )
        # If it already exists, update it to current count + 1.
        if not created:
            cls.objects.filter(
                team=team, puzzle=puzzle, subpuzzle=subpuzzle, submission=submission
            ).update(count=F("count") + 1)

    @classmethod
    def histogram(cls, puzzle):
        return (
            cls.objects.filter(puzzle=puzzle, submitted_datetime__lt=HUNT_END_TIME)
            .values("submission")
            .annotate(counts=Sum("count"))
        )

    @classmethod
    def histogram_by_subpuzzle(cls, puzzle):
        return (
            cls.objects.filter(puzzle=puzzle, submitted_datetime__lt=HUNT_END_TIME)
            .values("submission", "subpuzzle")
            .annotate(counts=Sum("count"))
        )

    @classmethod
    def histogram_by_team(cls, puzzle):
        return (
            cls.objects.filter(puzzle=puzzle, submitted_datetime__lt=HUNT_END_TIME)
            .values("submission", "team")
            .annotate(counts=Sum("count"))
        )


@receiver(post_save, sender=CustomPuzzleSubmission)
def notify_on_custom_puzzle_submission(sender, instance, created, **kwargs):
    if created:
        pass
        # FIXME: can run custom logic on puzzle submission.
        # if instance.puzzle and instance.puzzle.slug == "sample":
        #   pass


# Sends a Discord alert, we'll construct the finisher emails manually.
def handle_victory(submission):
    if submission.is_correct and submission.puzzle.slug == META_META_SLUG:
        team = submission.team
        emails = team.get_emails()
        dispatch_victory_alert(
            "Team **%s** has finished the hunt!" % team
            + "\n**Emails:** "
            + ", ".join(emails)
        )

        if team.profile_pic_victory.name:
            profile_pic = team.profile_pic_victory.name
        elif team.profile_pic.name:
            profile_pic = team.profile_pic.name
        else:
            profile_pic = ""

        send_mail_wrapper(
            f"Congratulations!",
            "victory_email",
            {
                "team_name": team.team_name,
                "profile_pic": profile_pic,
            },
            emails,
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
        hint_answer_url = generate_url(f"/internal/extraguessgrant/{self.id}")
        return (
            f"{self.team} is rate-limited on {self.puzzle.emoji} {self.puzzle} and requested more guesses. "
            f"You may view past guesses and approve or deny the request here:\n"
            f"{hint_answer_url}\n"
            f"React to this Discord message when done."
        )

    class Meta:
        unique_together = ("team", "puzzle")


class PuzzleMessageManager(models.Manager):
    def get_by_natural_key(self, puzzle_slug, guess):
        return self.get(puzzle__slug=puzzle_slug, guess=guess)


class PuzzleMessage(models.Model):
    """A "keep going" message shown on submitting a specific wrong answer."""

    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)

    guess = models.CharField(max_length=500)
    response = models.TextField()

    objects = PuzzleMessageManager()

    def natural_key(self):
        return (self.puzzle.slug, self.guess)

    class Meta:
        unique_together = ("puzzle", "guess")

    def __str__(self):
        return "%s: %s" % (self.puzzle, self.guess)

    @property
    def semicleaned_guess(self):
        return PuzzleMessage.semiclean_guess(self.guess)

    @staticmethod
    def semiclean_guess(s):
        return s and re.sub(r"[^A-Z]", "", s.upper())


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


class StoryCardUnlock(models.Model):
    """Represents a team unlocking a new piece of story."""

    story_card = models.ForeignKey(StoryCard, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    unlock_datetime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%s -> %s @ %s" % (self.team, self.story_card, self.unlock_datetime)

    class Meta:
        unique_together = ("team", "story_card")


class Errata(models.Model):
    """Puzzle errata, displayed on puzzle page and central errata page."""

    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    creation_time = models.DateTimeField(default=timezone.now)
    text = models.TextField()

    def render_data(self):
        data = {
            "text": self.text,
            "time": self.creation_time,
            "puzzleName": self.puzzle.name,
        }
        if self.puzzle.slug == SPOILER_ERRATUM_PUZZLE:
            data["formattedTime"] = self.formatted_time
        return data

    @property
    def formatted_time(self):
        return self.creation_time.replace(tzinfo=pytz.utc).strftime(
            "%a, %m/%d/%y, %I:%M GMT"
        )


class BadEmailAddress(models.Model):
    "Email addresses we should not be emailing."
    UNSUBSCRIBED = "UNS"
    BOUNCED = "BOU"

    REASONS = {
        UNSUBSCRIBED: "Unsubscribed",
        BOUNCED: "Bounced",
    }

    email = models.EmailField(primary_key=True)
    reason = models.CharField(choices=tuple(REASONS.items()), max_length=3)


class EmailTemplate(models.Model):
    """Template for a mass email."""

    SCHEDULED = "SCHD"
    SENDING = "SOUT"
    SENT = "SENT"
    DRAFT = "DRFT"
    CANCELLED = "CANC"

    STATUSES = {
        SCHEDULED: "Scheduled",
        SENDING: "Sending",
        SENT: "Sent",
        DRAFT: "Draft",
        CANCELLED: "Cancelled",
    }

    RECIPIENT_BATCH_USERS = "BU"
    RECIPIENT_TEAMS = "TE"
    RECIPIENT_USERS = "US"
    RECIPIENT_BATCH_ADDRESSES = "AD"
    RECIPIENT_OPTIONS = {
        RECIPIENT_BATCH_USERS: "batch_all_users",  # send to batches of users (bcc)
        RECIPIENT_TEAMS: "all_teams",  # send to teams individually (teammembers to)
        RECIPIENT_USERS: "all_users",  # send to users individually (to)
        RECIPIENT_BATCH_ADDRESSES: "batch_addresses",  # send to batches of addresses (bcc)
    }

    subject = models.TextField(blank=True)
    text_content = models.TextField(blank=True)
    html_content = models.TextField(blank=True)
    from_address = models.TextField()
    scheduled_datetime = models.DateTimeField()
    status = models.CharField(
        choices=tuple(STATUSES.items()), max_length=4, default=DRAFT
    )
    recipients = models.CharField(
        choices=tuple(RECIPIENT_OPTIONS.items()), max_length=2
    )
    addresses = models.JSONField(blank=True, default=list)
    batch_size = models.IntegerField(default=50)  # for batch_users
    # Delay in ms between batches. Does not include the time to make the SMTP
    # request for each batch.
    batch_delay_ms = models.IntegerField(default=100)
    # for internal idempotency checks
    last_user_pk = models.IntegerField(default=-1)
    last_team_pk = models.IntegerField(default=-1)
    last_address_index = models.IntegerField(default=-1)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        update_fields = kwargs.get("update_fields")
        if (
            update_fields is None
            or "status" in update_fields
            or "scheduled_datetime" in update_fields
        ):
            if self.status == self.SCHEDULED:
                super().save(*args, **kwargs)
                pk = self.pk
                scheduled_datetime = self.scheduled_datetime
                transaction.on_commit(
                    lambda: celery_app.send_task(
                        "puzzles.emailing.task_send_email_template",
                        args=[pk],
                        eta=scheduled_datetime,
                    )
                )


class Email(models.Model):
    """Model for each individual email sent or received."""

    class Meta:
        unique_together = ("uidvalidity", "uid")

    SENDING = "SOUT"  # if sending via SMTP server but haven't read it back with IMAP
    SENT = "SENT"
    RECEIVED_NO_REPLY = "RNR"
    RECEIVED_ANSWERED = "RANS"
    RECEIVED_NO_REPLY_REQUIRED = "RNRR"
    RECEIVED_HINT = "RH"
    RECEIVED_BOUNCE = "RB"
    RECEIVED_UNSUBSCRIBE = "RUNS"
    RECEIVED_RESUBSCRIBE = "RSUB"
    DRAFT = "DRFT"  # is this useful?

    STATUSES = {
        SENDING: "Sending",
        SENT: "Sent",
        RECEIVED_NO_REPLY: "Received - No reply",
        RECEIVED_ANSWERED: "Received - Answered",
        RECEIVED_NO_REPLY_REQUIRED: "Received - No reply required",
        RECEIVED_HINT: "Received - Hint",
        RECEIVED_BOUNCE: "Received - Bounce",
        RECEIVED_UNSUBSCRIBE: "Received - Unsubscribe",
        RECEIVED_RESUBSCRIBE: "Received - Resubscribe",
        DRAFT: "Draft",
    }

    DEFERRED = object()  # sentinel to detect comparisons against deferred fields
    HEADER_BODY_SEPARATOR_REGEX = re.compile(rb"\r?\n\r?\n|\r\n?\r\n?")
    RESEND_COOLDOWN = 30  # seconds

    raw_content = models.BinaryField(blank=True)
    # derived from email raw_content
    subject = models.TextField(blank=True)
    text_content = models.TextField(blank=True)
    header_content = models.BinaryField(blank=True)
    has_attachments = models.BooleanField(default=False)
    message_id = models.TextField(db_index=True, blank=True)
    in_reply_to_id = models.TextField(
        db_index=True, blank=True
    )  # previous email in chain
    root_reference_id = models.TextField(
        db_index=True, blank=True
    )  # initial email in chain
    reference_ids = models.JSONField(blank=True, default=list)  # all emails in chain
    from_address = models.TextField(blank=True)
    # to, cc, bcc addresses are lists
    to_addresses = models.JSONField(blank=True, default=list)
    cc_addresses = models.JSONField(blank=True, default=list)
    # Date header
    sent_datetime = models.DateTimeField(null=True, blank=True)
    # Spam detection
    is_spam = models.BooleanField(default=False)
    is_authenticated = models.BooleanField(default=False)  # check for DMARC

    # other email info
    # This will be blank on emails we receive.
    bcc_addresses = models.JSONField(blank=True, default=list)
    attempted_send_datetime = models.DateTimeField(
        null=True, blank=True
    )  # used internally
    received_datetime = models.DateTimeField(
        default=timezone.now,
    )  # will be updated with timestamp from SMTP server
    uidvalidity = models.IntegerField(null=True, blank=True)  # set by IMAP
    uid = models.IntegerField(null=True, blank=True)  # set by IMAP
    modseq = models.IntegerField(null=True, blank=True)  # set by IMAP
    status = models.CharField(choices=tuple(STATUSES.items()), max_length=4)
    is_from_us = models.BooleanField()
    created_via_webapp = models.BooleanField()  # otherwise was found by IMAP
    scheduled_datetime = models.DateTimeField(
        default=timezone.now,
    )  # for emails we are sending
    template = models.ForeignKey(
        EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True
    )
    opened = models.BooleanField(default=False)  # if we want to set tracking pixels
    # we can set the team if it is known but in general emails won't have a team
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True, default=None
    )
    claimed_datetime = models.DateTimeField(null=True, blank=True)
    claimer = models.CharField(null=False, blank=True, default="", max_length=255)
    response = models.ForeignKey(
        "self",
        related_name="request_set",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __init__(self, *args, **kwargs):
        """
        Prefer to instantiate via FromRawContent, FromEmailMessage, or
        ReplyEmail, plus non-RFC822 email attributes (such as bcc and all our
        custom metadata).

        This saves the initial values of some attributes so that we can check
        if it changed during save().
        """
        super().__init__(*args, **kwargs)
        # check against __dict__ to test for deferred fields
        for field in ("raw_content", "header_content"):
            if field in self.__dict__:
                if isinstance(getattr(self, field), memoryview):
                    setattr(self, field, getattr(self, field).tobytes())
        self._original_claimer = self.__dict__.get("claimer", self.DEFERRED)

    def save(self, *args, active_connection=None, **kwargs):
        """
        Save with an active_connection to send the email in this thread.
        Otherwise, will add to the task queue.
        """
        assert self._original_claimer is not self.DEFERRED
        super().save(*args, **kwargs)
        # TODO: post save / on_commit actions
        if not self.is_from_us:
            if self.claimer != self._original_claimer:
                transaction.on_commit(
                    lambda: dispatch_bot_alert(self.claimed_discord_message())
                )

        # queue up sending the email if SENDING
        update_fields = kwargs.get("update_fields")
        if update_fields is None or "status" in update_fields:
            if self.status == self.SENDING:
                pk = self.pk
                scheduled_datetime = self.scheduled_datetime
                if active_connection is None:
                    transaction.on_commit(
                        lambda: celery_app.send_task(
                            "puzzles.emailing.task_send_email",
                            args=[pk],
                            eta=scheduled_datetime,
                        )
                    )
                else:
                    import puzzles.emailing

                    transaction.on_commit(
                        lambda: puzzles.emailing.task_send_email(
                            pk,
                            active_connection=active_connection,
                        )
                    )

    @classmethod
    def FromRawContent(cls, raw_content, **kwargs):
        email_kwargs = cls.parse_fields_from_message(
            raw_content=raw_content,
        )
        email_kwargs.update(kwargs)
        return cls(**email_kwargs)

    @classmethod
    def make_message_id(cls):
        return email.utils.make_msgid(domain=settings.EMAIL_USER_DOMAIN)

    @classmethod
    def FromEmailMessage(
        cls,
        email_message,
        add_defaults=True,
        check_addresses=True,
        include_unsubscribe_header=False,
        exclude_bounced_only=False,
        **kwargs,
    ):
        """
        If add_defaults is set, will add default fields like Message-ID.
        """
        email_kwargs = {}
        is_from_us = cls.check_is_from_us(email_message, check_authentication=False)
        if add_defaults:
            if not email_message.get("Message-ID"):
                email_message["Message-ID"] = cls.make_message_id()
            email_kwargs["is_authenticated"] = is_from_us or cls.check_authentication(
                email_message
            )
            email_kwargs["is_from_us"] = is_from_us
            email_kwargs["is_spam"] = not is_from_us and cls.check_is_spam(
                email_message
            )
            email_kwargs["created_via_webapp"] = True
            if is_from_us and include_unsubscribe_header:
                unsubscribe_mailto = f"{settings.EMAIL_UNSUBSCRIBE_LOCALNAME}@{settings.EMAIL_USER_DOMAIN}"
                unsubscribe_link = cls.get_unsubscribe_link(email_message["Message-ID"])
                email_message[
                    "List-Unsubscribe"
                ] = f"<mailto:{unsubscribe_mailto}>, <{unsubscribe_link}>"
        if check_addresses and is_from_us:
            recipients = []
            email_to = email_message.get("To")
            email_cc = email_message.get("Cc")
            to_addresses = kwargs.get("to_addresses")
            recipients.extend(cls.parseaddrs(email_to) or [])
            recipients.extend(cls.parseaddrs(email_cc) or [])
            recipients.extend(kwargs.get("to_addresses", []))
            recipients.extend(kwargs.get("cc_addresses", []))
            recipients.extend(kwargs.get("bcc_addresses", []))
            if recipients:
                bad_recipients = set(
                    BadEmailAddress.objects.filter(
                        email__in=recipients,
                        **(
                            {"reason": BadEmailAddress.BOUNCED}
                            if exclude_bounced_only
                            else {}
                        ),
                    ).values_list("email", flat=True)
                )
                if email_to is not None:
                    del email_message["To"]
                    email_message["To"] = (
                        address
                        for address in email_to.addresses
                        if cls.parseaddr(address) not in bad_recipients
                    )
                if email_cc is not None:
                    del email_message["Cc"]
                    email_message["Cc"] = (
                        address
                        for address in email_cc.addresses
                        if cls.parseaddr(address) not in bad_recipients
                    )
                for key in ("to_addresses", "cc_addresses", "bcc_addresses"):
                    addresses = kwargs.get(key)
                    if addresses is not None:
                        kwargs[key] = [
                            address
                            for address in addresses
                            if address not in bad_recipients
                        ]
        email_kwargs.update(
            cls.parse_fields_from_message(
                email_message=email_message,
            )
        )
        email_kwargs.update(kwargs)
        return cls(**email_kwargs)

    @classmethod
    def ReplyEmail(cls, reply_to_obj, plain=None, html=None, reply_all=False, **kwargs):
        "Create a reply response for another email. Sets status to SENDING by default."
        assert plain is not None or html is not None
        if plain is None and html is not None:
            plain = Email.html2text(html)
        if html is None and plain is not None:
            html = Email.text2html(plain)
        reply_to_message = reply_to_obj.parse()
        reply_to_plain = reply_to_message.get_body("plain")
        reply_to_plain = reply_to_plain and reply_to_plain.get_content()
        reply_to_html = reply_to_message.get_body("html")
        reply_to_html = reply_to_html and reply_to_html.get_content()
        if reply_to_plain is None and reply_to_html is not None:
            reply_to_plain = Email.html2text(reply_to_html)
        if reply_to_html is None and reply_to_plain is not None:
            reply_to_html = Email.text2html(reply_to_plain)

        reply_to_from = reply_to_message.get("From")
        reply_to_to = reply_to_message.get("To")
        reply_to_to = [] if reply_to_to is None else reply_to_to.addresses
        reply_to_cc = reply_to_message.get("Cc")
        reply_to_cc = [] if reply_to_cc is None else reply_to_cc.addresses
        us = kwargs.get("from_address")
        reply_all_recipients = []
        for recipient in reply_to_to:
            if us is None and Email.check_is_address_us(recipient):
                us = recipient
            elif recipient != us:
                reply_all_recipients.append(recipient)
        reply_to_reply_to = reply_to_message.get("Reply-To", reply_to_from)
        reply_to_message_id = reply_to_message.get("Message-ID")
        reference_ids = reply_to_message.get("References")
        if reply_to_message_id or reference_ids:
            if reference_ids is None:
                reference_ids = reply_to_message_id
            else:
                reference_ids += f", {reply_to_message_id}"
        subject = reply_to_obj.subject
        if not subject.startswith("Re:"):
            subject = f"Re: {subject}"

        reply_to_date = reply_to_obj.sent_datetime or reply_to_obj.received_datetime
        if reply_to_date is None:
            wrote_str = f"{reply_to_from} wrote:"
        else:
            datestr = reply_to_date.strftime("%a, %b %d, %Y at %I:%M %p").replace(
                " 0", " "
            )
            wrote_str = f"On {datestr}, {reply_to_from} wrote:"

        plain += (
            "\n\n"
            + wrote_str
            + "\n\n"
            + "\n".join(f"> {line}" for line in reply_to_plain.strip().split("\n"))
        )
        html = f'<div>{html}</div><div><br/><div>{wrote_str}<br/></div><blockquote style="border-left: 1px solid rgb(204,204,204); padding-left:1ex">{reply_to_html}</blockquote></div>'

        email_message = email.message.EmailMessage()
        email_message["Subject"] = subject
        # this webapp is not set up to send mail from an external domain (eg. gmail)
        if cls.check_is_address_us(us, allow_external=False):
            email_message["From"] = us
        else:
            email_message["From"] = f"info@{settings.EMAIL_USER_DOMAIN}"
        to_addresses = kwargs.get("to_addresses")
        if to_addresses is not None:
            email_message["To"] = to_addresses
        else:
            email_message["To"] = reply_to_reply_to
            if reply_all and reply_all_recipients:
                email_message["Cc"] = reply_all_recipients
        if reply_to_message_id is not None:
            email_message["In-Reply-To"] = reply_to_message_id
        if reference_ids is not None:
            email_message["References"] = reference_ids
        email_message.set_content(plain)
        email_message.add_alternative(html, subtype="html")

        email_kwargs = {}
        email_kwargs["status"] = Email.SENDING
        if reply_to_obj.team is not None:
            email_kwargs["team"] = reply_to_obj.team
        email_kwargs.update(kwargs)
        # When replying, only exclude bounced, not unsubscribed
        return cls.FromEmailMessage(
            email_message, exclude_bounced_only=True, **email_kwargs
        )

    @classmethod
    def parse_fields_from_message(
        cls, raw_content=None, email_message=None, populate_text_content=True
    ):
        email_kwargs = {
            "raw_content": raw_content,
        }
        if raw_content is not None:
            email_message = email.message_from_bytes(
                raw_content, policy=email.policy.default
            )
        if email_message is not None:
            if raw_content is None:
                raw_content = email_message.as_bytes()
                email_kwargs["raw_content"] = raw_content
            email_kwargs["subject"] = email_message.get("Subject")
            if populate_text_content:
                email_kwargs["text_content"] = cls.make_text_content(email_message)
            email_kwargs["header_content"] = cls.HEADER_BODY_SEPARATOR_REGEX.split(
                raw_content.strip(), 1
            )[0].strip()
            # has_attachments will be true if the email has images or attached
            # files or other parts that are not understood
            has_attachments = False
            for part in email_message.walk():
                if part.is_attachment():
                    has_attachments = True
                if part.get_content_maintype() not in ("text", "multipart"):
                    has_attachments = True
            email_kwargs["has_attachments"] = has_attachments
            email_kwargs["message_id"] = cls.parseaddr(email_message.get("Message-ID"))
            email_kwargs["in_reply_to_id"] = cls.parseaddr(
                email_message.get("In-Reply-To")
            )
            for reference_ids in email_message.get_all("References", []):
                for reference_id in reference_ids.strip().split():
                    reference_id = cls.parseaddr(reference_id)
                    if reference_id:
                        email_kwargs.setdefault("root_reference_id", reference_id)
                        email_kwargs.setdefault("reference_ids", []).append(
                            reference_id
                        )
            email_kwargs["from_address"] = cls.parseaddr(email_message.get("From"))
            email_kwargs["to_addresses"] = cls.parseaddrs(email_message.get("To"))
            email_kwargs["cc_addresses"] = cls.parseaddrs(email_message.get("Cc"))
            try:
                # fails on ill-formatted date
                date = email_message.get("Date")
            except:
                date = None
            if date is not None:
                email_kwargs["sent_datetime"] = date.datetime
            # no bcc in email headers
            for key, value in list(email_kwargs.items()):
                if value is None:
                    del email_kwargs[key]
        return email_kwargs

    @classmethod
    def parseaddrs(cls, addresses):
        if addresses is None:
            return []
        return list(filter(None, map(cls.parseaddr, addresses.addresses)))

    @classmethod
    def parseaddr(cls, address):
        if isinstance(address, email.headerregistry.AddressHeader):
            addresses = cls.parseaddrs(address)
            return addresses[0] if addresses else None
        if isinstance(address, email.headerregistry.Address):
            return address.addr_spec if address.domain else None
        return None if address is None else email.utils.parseaddr(address)[1]

    def parse(self):
        return email.message_from_bytes(self.raw_content, policy=email.policy.default)

    def headers(self):
        return email.parser.BytesHeaderParser(policy=email.policy.default).parsebytes(
            self.header_content
        )

    def recipients(self, bcc=True):
        recipients = []
        recipients.extend(self.to_addresses)
        recipients.extend(self.cc_addresses)
        if bcc:
            recipients.extend(self.bcc_addresses)
        return recipients

    @property
    def all_recipients(self):
        return self.recipients()

    @property
    def requires_response(self):
        return self.status == Email.RECEIVED_NO_REPLY

    @property
    def long_status(self):
        return self.STATUSES.get(self.status)

    @property
    def is_unsent(self):
        return self.status == Email.SENDING

    @staticmethod
    def Address(*args, **kwargs):
        try:
            return email.headerregistry.Address(*args, **kwargs)
        except email.errors.MessageError:
            return email.headerregistry.Address()

    @classmethod
    def check_authentication(cls, email_message, preauthentication=None):
        """
        Check the authentication results header to verify that the FROM header
        is not being forged.
        """
        if preauthentication is not None:
            return preauthentication
        authentication_results = email_message.get("Authentication-Results")
        if authentication_results is None:
            return False
        authentication_parts = authentication_results.split(";")
        if authentication_parts[0].strip() != settings.EMAIL_HOST:
            return False
        passed = False
        for part in authentication_parts[1:]:
            result = part.strip().split()[0]
            if result in ("auth=pass", "dmarc=pass"):
                passed = True
        if not passed:
            return False
        return True

    @classmethod
    def check_is_from_us(
        cls, email_message, check_authentication=True, preauthentication=None
    ):
        "Check the FROM header and authentication results of an EmailMessage."
        from_address = email_message.get("From")
        if from_address is None:
            return False
        if not cls.check_is_address_us(from_address):
            return False
        if check_authentication and not cls.check_authentication(
            email_message, preauthentication=preauthentication
        ):
            return False
        return True

    @classmethod
    def check_is_address_us(cls, address, allow_external=True):
        address = cls.parseaddr(address)
        if address is None:
            return False
        if settings.IS_TEST:
            # treat dev testing emails as external
            if address in settings.DEV_EMAIL_WHITELIST:
                return False
        domain_match = (
            Email.Address(addr_spec=address).domain == settings.EMAIL_USER_DOMAIN
        )
        is_external_us = address in settings.EXTERNAL_EMAIL_ADDRESSES
        return domain_match or (allow_external and is_external_us)

    @classmethod
    def check_is_spam(cls, email_message):
        raw_value = email_message.get("X-Spam", "False")
        try:
            value = distutils.util.strtobool(raw_value)
        except ValueError:
            value = False
        return value

    @classmethod
    def get_bounced_address(cls, email_message):
        """
        Determine if the email was sent to our bounce receiver and parse the
        offending address. Returns None if not a bounce.
        """
        for address in cls.parseaddrs(email_message.get("To")):
            addr = cls.Address(addr_spec=address)
            if addr.domain != settings.EMAIL_USER_DOMAIN:
                continue
            parts = addr.username.split("+", 1)
            if len(parts) != 2:
                continue
            localname, alias = parts
            if localname != settings.EMAIL_BOUNCES_LOCALNAME:
                continue
            bounced_address = "@".join(alias.rsplit("=", 1))
            if bounced_address != Email.Address(addr_spec=bounced_address).addr_spec:
                continue
            return bounced_address
        return None

    @classmethod
    def _get_from_if_sent_to(
        cls,
        to_address,
        email_message,
        check_authentication=True,
        preauthentication=None,
    ):
        is_match = False
        for address in cls.parseaddrs(email_message.get("To")):
            if address == to_address:
                is_match = True
        if not is_match:
            return None
        if check_authentication and not cls.check_authentication(
            email_message, preauthentication=preauthentication
        ):
            return None
        from_address = cls.parseaddr(email_message.get("From"))
        return from_address

    @classmethod
    def get_resubscribed_address(
        cls, email_message, check_authentication=True, preauthentication=None
    ):
        """
        Determine if the email was sent to our resubscribe receiver and parse the
        offending address. Returns None if not a resubscribe.
        """
        resubscribe_to = (
            f"{settings.EMAIL_RESUBSCRIBE_LOCALNAME}@{settings.EMAIL_USER_DOMAIN}"
        )
        return cls._get_from_if_sent_to(
            resubscribe_to,
            email_message,
            check_authentication=check_authentication,
            preauthentication=preauthentication,
        )

    @classmethod
    def get_unsubscribed_address(
        cls, email_message, check_authentication=True, preauthentication=None
    ):
        """
        Determine if the email was sent to our resubscribe receiver and parse the
        offending address. Returns None if not a resubscribe.
        """
        unsubscribe_to = (
            f"{settings.EMAIL_UNSUBSCRIBE_LOCALNAME}@{settings.EMAIL_USER_DOMAIN}"
        )
        return cls._get_from_if_sent_to(
            unsubscribe_to,
            email_message,
            check_authentication=check_authentication,
            preauthentication=preauthentication,
        )

    def get_emails_in_thread_filter(self):
        """
        Makes an intermidiary query to check which of the reference emails were
        from a template (ie, mass email).
        """
        template_ids = set(
            Email.objects.filter(
                message_id__in=self.reference_ids,
                template_id__isnull=False,
            ).values_list("message_id", flat=True)
        )
        if not template_ids:
            root_reference_id = self.root_reference_id or self.message_id
            return Email.objects.filter(
                Q(message_id=root_reference_id) | Q(root_reference_id=root_reference_id)
            )
        for i, _id in enumerate((*self.reference_ids, self.message_id)):
            if _id not in template_ids:
                return Email.objects.filter(
                    Q(message_id=_id) | Q(**{f"reference_ids__{i}": _id})
                )
        return Email.objects.filter(pk=self.pk)

    @staticmethod
    def text2html(plain):
        content = html.escape(plain).replace("\n", "<br/>")
        return f"<div>{content}</div>"

    @staticmethod
    def html2text(html):
        text_maker = html2text.HTML2Text()
        text_maker.ignore_links = True
        return text_maker.handle(html).strip()

    @classmethod
    def make_text_content(cls, email_message, reply_to_obj=None, find_reply_to=True):
        """
        Parse email contents and extract out text, removing content from an
        email being replied to.

        Because different email clients format replies differently, we try to
        match against alpha characters only when filtering out the replied to
        message. Additionally, we try to detect and remove a date line before
        the quoted text (On DATE, PERSON wrote:).
        """
        text_content = None
        html = email_message.get_body("html")
        if html is not None:
            text_content = Email.html2text(html.get_content())
        if text_content is None:
            plain = email_message.get_body("plain")
            if plain is not None:
                text_content = plain.get_content()
        if text_content is None:
            return None
        # remove instances of "mailto:" links if any appear raw
        text_content = re.sub(r"\bmailto:", r"", text_content)
        if find_reply_to and reply_to_obj is None:
            in_reply_to_id = cls.parseaddr(email_message.get("In-Reply-To"))
            if in_reply_to_id is not None:
                reply_to_obj = (
                    Email.objects.filter(message_id=in_reply_to_id)
                    .only(
                        "text_content",
                        "header_content",
                        "from_address",
                    )
                    .first()
                )
        if reply_to_obj is not None:
            reply_to_email_message = email.message_from_bytes(
                reply_to_obj.raw_content,
                policy=email.policy.default,
            )
            reply_to_all_text_content = Email.make_text_content(
                reply_to_email_message, find_reply_to=False
            )
            if reply_to_all_text_content is not None:
                full_from_address = reply_to_obj.headers().get("From")
                lines = text_content.split("\n")
                line_letters = [
                    "".join(c.lower() for c in line if c.isalpha()) for line in lines
                ]
                line_starts = {}
                length = 0
                for i, line in enumerate(line_letters):
                    line_starts[length] = i
                    length += len(line)
                line_starts[length] = len(line_letters)
                letters = "".join(line_letters)
                reply_to_letters = "".join(
                    c.lower() for c in reply_to_all_text_content if c.isalpha()
                )
                last_match = len(letters)
                if reply_to_letters:
                    while last_match != -1:
                        last_match = letters.rfind(reply_to_letters, 0, last_match)
                        start_line = line_starts.get(last_match)
                        end_line = line_starts.get(last_match + len(reply_to_letters))
                        if start_line is not None and end_line is not None:
                            while start_line and not line_letters[start_line - 1]:
                                start_line -= 1
                            if start_line:
                                # check for a "On [DATE], [SENDER] wrote:" line
                                line = lines[start_line - 1]
                                realname, address = email.utils.parseaddr(
                                    full_from_address
                                )
                                for address_part in (address, realname):
                                    if address_part is not None:
                                        line = line.replace(address_part, "")
                                try:
                                    _, tokens = dateutil.parser.parse(
                                        line, fuzzy_with_tokens=True
                                    )
                                except ValueError:
                                    pass
                                else:
                                    line = " ".join(tokens)
                                has_only_filler_words = True
                                line = "".join(
                                    c.lower() if c.isalpha() else " " for c in line
                                )
                                for word in line.split():
                                    if word not in (
                                        "on",
                                        "at",
                                        "wrote",
                                    ):
                                        has_only_filler_words = False
                                if has_only_filler_words:
                                    start_line -= 1
                                    while (
                                        start_line and not line_letters[start_line - 1]
                                    ):
                                        start_line -= 1
                            text_content = "\n".join(
                                lines[:start_line] + lines[end_line:]
                            )
                            break
        return text_content.strip()

    def created_discord_message(self):
        email_answer_url = generate_url(f"/internal/single_email/{self.id}")
        if self.team:
            _from = f"{self.team} ({self.from_address})"
        else:
            _from = f"{self.from_address}"
        return (
            f"Email #{self.pk} sent by {_from}\n"
            f"**Subject:** ```{self.subject[:1500]}```\n"
            f"**Question:** ```{self.text_content[:1500]}```\n"
            f"**Claim email reply:** {email_answer_url}\n"
        )

    def claimed_discord_message(self):
        if self.claimer:
            return f"Email #{self.pk} [{self.subject}] claimed by {self.claimer}"
        else:
            return f"Email #{self.pk} [{self.subject}] was unclaimed"

    @classmethod
    def responded_discord_message(cls, email_request, email_response=None):
        if email_request.team:
            _from = f"{email_request.team} ({email_request.from_address})"
        else:
            _from = f"{email_request.from_address}"
        if email_request.status == Email.RECEIVED_NO_REPLY_REQUIRED:
            response_text = "(No response required)"
        elif email_response is None:
            response_text = "(email_response was unexpectedly None, check logs)"
        else:
            response_text = email_response.text_content

        return (
            f"Email #{email_request.pk} resolved by {email_request.claimer}\n"
            f"Email was requested by {_from}\n"
            f"**Subject:** ```{email_request.subject[:1500]}```\n"
            f"**Request:** ```{email_request.text_content[:1500]}```\n"
            f"**Response:** {response_text}\n"
        )

    @classmethod
    def get_unsubscribe_link(cls, message_id):
        return f"https://{settings.DOMAIN}/unsubscribe?mid={cls.parseaddr(message_id).split('@')[0]}"


@receiver(post_save, sender=Email)
def notify_on_new_email(sender, instance, created, update_fields, **kwargs):
    # Only send the alert for emails that may need a response.
    if created and instance.requires_response:
        dispatch_email_alert(instance.created_discord_message())


class Hint(models.Model):
    """Same model for a hint request or a hint response."""

    NO_RESPONSE = "NR"
    ANSWERED = "ANS"
    REQUESTED_MORE_INFO = "MOR"
    REFUNDED = "REF"
    OBSOLETE = "OBS"
    RESOLVED = "RES"

    STATUSES = {
        NO_RESPONSE: "No response",
        ANSWERED: "Answered",
        REQUESTED_MORE_INFO: "Request more info",  # we asked the team for more info
        REFUNDED: "Refund",  # we can't answer for some reason. refund
        OBSOLETE: "Obsolete",  # puzzle was solved while waiting for hint
        RESOLVED: "Resolved without response",  # requesters are not expecting an additional reply
    }

    DEFERRED = object()  # sentinel to detect comparisons against deferred fields

    EMAIL_ADDRESS = f"hints@{settings.EMAIL_USER_DOMAIN}"

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    root_ancestor_request = models.ForeignKey(
        "self",
        related_name="hint_thread_set",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )  # field is null if hint is the original request
    is_request = models.BooleanField(default=True)

    submitted_datetime = models.DateTimeField(auto_now_add=True)
    text_content = models.TextField(blank=True)
    notify_emails = models.TextField(default="none")
    email = models.OneToOneField(
        Email, on_delete=models.SET_NULL, null=True, blank=True
    )

    claimed_datetime = models.DateTimeField(null=True, blank=True)
    claimer = models.CharField(null=False, blank=True, default="", max_length=255)

    response = models.ForeignKey(
        "self",
        related_name="request_set",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    # Status for original hint of thread determines status of whole thread.
    # Individual statuses OBSOLETE and RESOLVED will also resolve a request
    # that doesn't have a response associated with it, but most followup hints
    # should have the status NO_RESPONSE because their status is tracked by the
    # original hint.
    status = models.CharField(
        choices=tuple(STATUSES.items()), default=NO_RESPONSE, max_length=3
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # check against __dict__ to test for deferred fields
        self._original_claimer = self.__dict__.get("claimer", self.DEFERRED)

    def save(self, *args, **kwargs):
        assert self._original_claimer is not self.DEFERRED
        super().save(*args, **kwargs)
        if self.is_request:
            if self.claimer != self._original_claimer:
                transaction.on_commit(
                    lambda: dispatch_bot_alert(self.claimed_discord_message())
                )

    def get_or_populate_response(self):
        "Get the response object for a hint request or create an empty one."
        if not self.is_request:
            raise ValueError("Hint responding to is not a request")
        if self.response is not None:
            response = self.response
        else:
            # keep this list up to date with views.puzzles.hint()
            response = Hint(
                team=self.team,
                puzzle=self.puzzle,
                root_ancestor_request_id=self.original_request_id,
                is_request=False,
                notify_emails=self.notify_emails,
            )
        response.status = self.original_request.status
        return response

    def get_prior_requests_needing_response(self):
        "Get unanswered hint requests in the same thread."
        return list(
            Hint.objects.filter(
                self.original_request_filter(),
                submitted_datetime__lte=self.submitted_datetime,
                is_request=True,
                response__isnull=True,
            ).exclude(status__in=(Hint.OBSOLETE, Hint.RESOLVED))
        )

    def populate_response_and_update_requests(self, text_content):
        """
        Create empty hint response object. Returns {
            response: Hint, # response hint
            requests: List[Hint], # list of requests whose response need to be updated
            response_email: Email, # response email to be sent (can be None if no email)
        }
        These objects are not yet saved when returned.
        """
        requests = self.get_prior_requests_needing_response()
        reply_to = (
            Hint.objects.filter(
                self.original_request_filter(),
                submitted_datetime__lte=self.submitted_datetime,
                email__isnull=False,
            )
            .select_related("email")
            .last()
        )
        reply_to_email = reply_to.email if reply_to else None

        response = Hint(
            team=self.team,
            puzzle=self.puzzle,
            root_ancestor_request_id=self.original_request_id,
            is_request=False,
            text_content=text_content,
            claimed_datetime=self.claimed_datetime,
            claimer=self.claimer,
        )

        notify_emails = "none"

        for request in requests:
            request.response = response

            if request.notify_emails == "none":
                pass
            elif request.notify_emails == "all":
                notify_emails = "all"
            else:
                if notify_emails == "none":
                    notify_emails = set()
                if notify_emails != "all":
                    notify_emails.update(request.recipients())

        if isinstance(notify_emails, set):
            notify_emails = ", ".join(notify_emails)
        response.notify_emails = notify_emails

        context = {
            "hint_response": response,
        }
        request_text = ("\n\n".join(request.text_content for request in requests),)
        if request_text:
            context["hint_request"] = {
                "text_content": "\n\n".join(
                    request.text_content for request in requests
                ),
            }

        recipients = response.recipients()

        if not recipients:
            response_email = None
        else:
            plain = render_to_string("hint_answered_email.txt", context)
            html = render_to_string("hint_answered_email.html", context)

            if reply_to_email:
                response_email = Email.ReplyEmail(
                    reply_to_email,
                    plain=plain,
                    html=html,
                    from_address=self.EMAIL_ADDRESS,
                    to_addresses=recipients,
                    team=self.team,
                )
            else:
                response_email_message = email.message.EmailMessage()
                response_email_message[
                    "Subject"
                ] = f"{settings.EMAIL_SUBJECT_PREFIX}Hint answered for {self.puzzle}"
                response_email_message["From"] = self.EMAIL_ADDRESS
                response_email_message["To"] = recipients
                response_email_message.set_content(plain)
                response_email_message.add_alternative(html, subtype="html")
                response_email = Email.FromEmailMessage(
                    response_email_message,
                    status=Email.SENDING,
                    team=self.team,
                )
            if response_email.recipients():
                response.email = response_email
            else:
                response_email = None

        return {
            "response": response,
            "requests": requests,
            "response_email": response_email,
        }

    def __str__(self):
        def abbr(s):
            if len(s) > 50:
                return s[:50] + "..."
            return s

        o = '{}, {}: "{}"'.format(
            self.team.team_name,
            self.puzzle.name,
            abbr(self.text_content),
        )
        if self.status != self.NO_RESPONSE:
            o = o + " {}".format(self.status)
        return o

    def recipients(self):
        if self.notify_emails == "all":
            return self.team.get_emails()
        if self.notify_emails == "none":
            return []
        return [s.strip() for s in self.notify_emails.split(",")]

    @property
    def original_request_id(self):
        "Like root_ancestor_request_id but also for root request"
        return (
            self.pk
            if self.root_ancestor_request_id is None
            else self.root_ancestor_request_id
        )

    @property
    def original_request(self):
        return (
            self
            if self.root_ancestor_request_id is None
            else self.root_ancestor_request
        )

    def original_request_filter(self):
        "Filter to filter by original request"
        original_request_id = self.original_request_id
        return Q(pk=original_request_id) | Q(
            root_ancestor_request_id=original_request_id
        )

    @property
    def requires_response(self):
        return all(
            (
                self.is_request,
                self.response_id is None,
                self.status not in (Hint.OBSOLETE, Hint.RESOLVED),
            )
        )

    @property
    def puzzle_hint_url(self):
        "url for teams to view their hints for this puzzle."
        return f"https://{settings.DOMAIN}/hints/{self.puzzle.slug}"

    @property
    def long_status(self):
        return self.STATUSES.get(self.status)

    def created_discord_message(self):
        team_hints = generate_url(
            "/admin/puzzles/hint/", {"team__id__exact": self.team_id}
        )
        solution_url = generate_url(f"/solutions/{self.puzzle.slug}")
        hints_for_this_puzzle = generate_url(
            "/admin/puzzles/hint/", {"puzzle__id__exact": self.puzzle_id}
        )
        hint_answer_url = generate_url(f"/internal/single_hint/{self.id}")
        return (
            f"Hint #{self.pk} requested on {self.puzzle.emoji} {self.puzzle} by {self.team}\n"
            f"**Question:** ```{self.text_content[:1500]}```\n"
            f"**Puzzle:** {solution_url} ({hints_for_this_puzzle})\n"
            f"**Claim and answer hint:** {hint_answer_url}\n"
        )

    def claimed_discord_message(self):
        if self.claimer:
            return f"Hint #{self.pk} claimed by {self.claimer}"
        else:
            return f"Hint #{self.pk} was unclaimed"

    @classmethod
    def responded_discord_message(cls, hint_request, hint_response):
        status_name = cls.STATUSES[hint_request.status]
        return (
            f"Hint #{hint_request.pk} resolved by {hint_request.claimer}\n"
            f"Hint was requested on {hint_request.puzzle.emoji} {hint_request.puzzle} by {hint_request.team}\n"
            f"**Question:** ```{hint_request.text_content[:1500]}```\n"
            f"**Response:** {hint_response.text_content}\n"
            f"**Marked as:** {status_name}\n"
        )


@receiver(post_save, sender=Hint)
def notify_on_new_hint(sender, instance, created, update_fields, **kwargs):
    # Only send alert for hints requested by teams, not responses.
    if created and instance.is_request:
        dispatch_hint_alert(instance.created_discord_message())


@receiver(post_save, sender=ExtraGuessGrant)
def notify_on_extra_guess_grant_update(
    sender, instance, created, update_fields, **kwargs
):
    from puzzles.views.puzzles import get_ratelimit

    ratelimit_data = get_ratelimit(instance.puzzle, instance.team)
    websocket_data = {
        "puzzle": {
            "slug": instance.puzzle.slug,
            "name": instance.puzzle.name,
            "round": instance.puzzle.round,
        },
        "rateLimit": ratelimit_data,
    }
    channels_group = ClientConsumer.get_puzzle_group(
        id=instance.team.user_id, slug=instance.puzzle.slug
    )
    ClientConsumer.send_event(channels_group, "submission", websocket_data)

    # Handle status = GRANTED inside API call.
    if instance.status == ExtraGuessGrant.NO_RESPONSE:
        dispatch_extra_guess_alert(instance.requested_discord_message())
