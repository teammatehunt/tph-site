import datetime
import os
import re
import typing
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.fields import AutoSlugField
from spoilr.utils import generate_url

slug_validator = RegexValidator(
    r"^[\w-]*$", "Only letters, numbers, underscores, and hyphens are allowed."
)

### Section: Hunt solving teams and users.


class TeamType(models.TextChoices):
    # Whether the team is a team controlled by the hunt setters.
    INTERNAL = "internal", "Internal Team"

    # Whether the team is for public access.
    PUBLIC = "public", "Public Team"


class InteractionType(models.TextChoices):
    # The team is submitting extra content for a puzzle. HQ needs to grade the
    # content and respond if needed.
    # This interaction is automatically created when the team sends us an email with a
    # specific subject, with the interaction's `email_key` field.
    # NB (2023): This interaction type is unused and unimplemented, primarily because
    # we do not collect emails from all team members and we can't route an email
    # to an interaction for a team if we don't know which team the email is from.
    SUBMISSION = "submission", "Submission for puzzle"

    # The team has unlocked a story interaction. HQ needs to schedule a live
    # interaction, or send a fallback email with the interaction content.
    # This interaction is automatically created either when the team solves the
    # puzzle in the `puzzle` field.
    STORY = "story", "Story"

    # The team is requesting a physical puzzle, or access to a staffed room.
    # HQ needs to coordinate a time/location for the team to retrieve the puzzle
    # or go to the staffed room.
    PHYSICAL = "physical", "Physical"

    # The team has become eligible for automatically unlocking some hunt content.
    # HQ needs to approve giving the team access, and send an email to the
    # captain with an unlock link.
    UNLOCK = "unlock", "Unlock"

    # The team has requested a free answer for a puzzle.
    # HQ needs to contact the captain and get them to approve spending the free
    # answer token.
    ANSWER = "answer", "Answer"


class SpoilrTeamManager(models.Manager):
    def get_queryset(self, *args, **kwargs):
        # Prefetches the associated hunt team automatically.
        # You may wish to delete this if you use spoilr directly.
        return super().get_queryset(*args, **kwargs).select_related("team")


# TODO(sahil): Use Django 4 unique constraint with expressions to make sure usernames are case-insensitive unique.
class Team(models.Model):
    objects = SpoilrTeamManager()

    username = models.CharField(max_length=50, unique=True, validators=[slug_validator])
    name = models.CharField(max_length=200, unique=True)
    # Public slug for use in URLs (autogenerated from name) -- not
    # necessarily the same as the username
    slug = AutoSlugField(max_length=200, unique=True, populate_from=("name",))
    creation_time = models.DateTimeField(auto_now_add=True, null=True)

    rounds = models.ManyToManyField("Round", through="RoundAccess")
    puzzles = models.ManyToManyField("Puzzle", through="PuzzleAccess")
    interactions = models.ManyToManyField("Interaction", through="InteractionAccess")

    type = models.CharField(
        max_length=20, choices=TeamType.choices, null=True, blank=True
    )

    def user_profile_filename(instance, filename):
        _, extension = os.path.splitext(filename)
        return f"team/{instance.user.username}/profile_picture{extension}"

    profile_pic = models.ImageField(
        upload_to=user_profile_filename, max_length=300, blank=True
    )
    # Whether profile picture is allowed.
    profile_pic_approved = models.BooleanField(default=False)

    @property
    def is_internal(self):
        return self.type == TeamType.INTERNAL

    @property
    def is_public(self):
        return self.type == TeamType.PUBLIC

    @property
    def shared_account(self):
        return self.user_set.filter(team_role=UserTeamRole.SHARED_ACCOUNT).first()

    @property
    def contact_email(self):
        return (
            self.teamregistrationinfo.contact_email
            if hasattr(self, "teamregistrationinfo")
            else None
        )

    # The teamwide email if it exits, else the contact email
    @property
    def team_email(self):
        email = ""
        if hasattr(self, "teamregistrationinfo"):
            email = self.teamregistrationinfo.bg_emails
        return email or self.contact_email

    @property
    def all_emails(self):
        team_email = self.team_email
        contact_email = self.contact_email
        emails = [team_email]
        if team_email != contact_email:
            emails.append(contact_email)
        return [email for email in emails if email]

    # TODO(sahil): Remove this property and work with the request.user.is_staff directly instead.
    @property
    def is_admin(self):
        return self.shared_account.is_staff

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_type_valid",
                check=models.Q(type__in=TeamType.values),
            ),
            models.UniqueConstraint(
                fields=["type"],
                name="%(app_label)s_%(class)s_public_unique",
                condition=models.Q(type=TeamType.PUBLIC),
            ),
        ]


class UserTeamRole(models.TextChoices):
    SHARED_ACCOUNT = "shared", "Shared Account"
    # Note: In future hunts, we could support each solver having their own
    # user, and it's linked to the team. That could be implemented by adding
    # more roles here, like Captain and Member, along with some team admin
    # pages to browse and add team members.


class User(AbstractUser):
    """
    Custom Django user model to use for the hunt. It includes hunt team related
    metadata.
    """

    username_validator = slug_validator
    username = models.CharField(
        "Username",
        max_length=150,
        unique=True,
        help_text=(
            "Required. 150 characters or fewer. Letters, numbers, underscores, and hyphens only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": ("A user with that username already exists."),
        },
    )

    team = models.ForeignKey(Team, on_delete=models.PROTECT, null=True, blank=True)
    team_role = models.CharField(
        max_length=20, choices=UserTeamRole.choices, null=True, blank=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_team_role_valid",
                check=models.Q(team_role__in=UserTeamRole.values),
            ),
            models.UniqueConstraint(
                fields=["team"],
                condition=models.Q(team_role=UserTeamRole.SHARED_ACCOUNT),
                name="%(app_label)s_%(class)s_unique_team_shared_account",
            ),
            models.CheckConstraint(
                check=models.Q(team__isnull=True, team_role__isnull=True)
                | models.Q(team__isnull=False, team_role__isnull=False),
                name="%(app_label)s_%(class)s_is_captain_if_team",
            ),
            models.UniqueConstraint(
                fields=["email"],
                condition=~models.Q(email__exact=""),
                name="%(app_label)s_%(class)s_unique_email_or_blank",
            ),
        ]


class UserAuth(models.Model):
    """Authentication metadata for users."""

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    token = models.CharField(max_length=128)
    create_time = models.DateTimeField(auto_now_add=True)
    delete_time = models.DateTimeField(blank=True, null=True)


### Section: Modeling the hunt.


class Round(models.Model):
    act = models.IntegerField(default=1)
    slug = models.SlugField(max_length=200, unique=True)
    name = models.CharField(max_length=200, unique=True)
    order = models.IntegerField(unique=True)
    superround = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="subrounds",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name

    @property
    def site(self) -> str:
        return "hunt"

    @property
    def url(self):
        return generate_url("hunt", f"/rounds/{self.slug}")

    class Meta:
        ordering = ["order"]


class Puzzle(models.Model):
    # Deterministic ID for the puzzle, so that code and configuration can reliably
    # refer to a puzzle.
    external_id = models.IntegerField(unique=True)
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    slug = models.SlugField(max_length=200, unique=True)
    name = models.CharField(max_length=200)
    answer = models.TextField()
    credits = models.TextField(default="")
    order = models.IntegerField()
    is_meta = models.BooleanField(default=False, db_index=True)

    # all metas that this puzzle is part of
    metas = models.ManyToManyField(
        "self",
        limit_choices_to={"is_meta": True},
        symmetrical=False,
        blank=True,
        related_name="feeders",
    )

    def __str__(self):
        prefix = "metapuzzle" if self.is_meta else "puzzle"
        return f"{prefix} “{self.name}” ({self.round})"

    def get_teams_unlocked(self):
        """Returns list of teams who have unlocked this puzzle"""
        unlocks = PuzzleAccess.objects.filter(puzzle_id=self.id).select_related("team")
        return [unlock.team for unlock in unlocks]

    @property
    def is_multi_answer(self) -> bool:
        return "," in self.answer

    @property
    def all_answers(self) -> typing.List[str]:
        return list(sorted(x.strip() for x in self.answer.split(",")))

    def normalize_answer(self, s: str) -> str:
        return s and re.sub(r"[^A-Z]", "", s.upper())

    @property
    def normalized_answer(self) -> str:
        return self.normalize_answer(self.answer)

    def is_correct(self, s: str) -> bool:
        return self.normalized_answer == s

    class Meta:
        unique_together = ("round", "order")
        ordering = ["round__order", "order"]


class Interaction(models.Model):
    slug = models.SlugField(max_length=200, unique=True)
    name = models.CharField(max_length=200, unique=True)
    order = models.IntegerField(unique=True)
    instructions = models.TextField(
        null=True,
        blank=True,
        help_text="Text that is shown to the solving team when they are requesting this interaction",
    )
    interaction_type = models.CharField(
        max_length=50,
        choices=InteractionType.choices,
        default=InteractionType.SUBMISSION,
    )
    puzzle = models.ForeignKey(Puzzle, on_delete=models.PROTECT, null=True, blank=True)
    required_pseudoanswer = models.ForeignKey(
        "PseudoAnswer",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Set to a pseudoanswer if this interaction requires a partial submission before it can be unlocked",
    )
    unlocks_with_puzzle = models.BooleanField(
        default=True,
        help_text="Set if this interaction should be available as soon as its puzzle unlocks (or a pseudo-answer is submitted). If false, requires backend code to unlock manually. No-op if not associated with a puzzle.",
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["order"]


class RoundAccess(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%s can see %s" % (self.team, self.round)

    class Meta:
        unique_together = ("team", "round")
        verbose_name_plural = "Round access"


class SpoilrPuzzleAccessManager(models.Manager):
    def get_queryset(self, *args, **kwargs):
        # Prefetches the associated puzzle automatically.
        return (
            super()
            .get_queryset(*args, **kwargs)
            .select_related(
                "puzzle__puzzle__round__superround", "puzzle__puzzle__event"
            )
        )


class PuzzleAccess(models.Model):
    objects = SpoilrPuzzleAccessManager()

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    solved = models.BooleanField(default=False)
    solved_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        summary = "can see"
        if self.solved:
            summary = "has solved"
        return "%s %s %s" % (self.team, summary, self.puzzle)

    class Meta:
        unique_together = ("team", "puzzle")
        verbose_name_plural = "Puzzle access"


# Note to future hunt teams.
# This model is badly named. Interactions model that HQ needs to take some action,
# so "access" (implying the solvers have access to the interaction) is the wrong
# metaphor. Maybe something like `TeamInteraction` is a better name?
class InteractionAccess(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    interaction = models.ForeignKey(Interaction, on_delete=models.CASCADE)
    create_time = models.DateTimeField(auto_now_add=True)
    accomplished = models.BooleanField(default=False)
    accomplished_time = models.DateTimeField(null=True, blank=True)
    request_comments = models.TextField(
        null=True,
        blank=True,
        help_text="Comments from the team requesting this interaction",
    )

    def __str__(self):
        summary = "can accomplish"
        if self.accomplished:
            summary = "has accomplished"
        return "%s %s %s" % (self.team, summary, self.interaction)

    @property
    def task(self):
        return self.interactionaccesstask.tasks.first()

    @property
    def handler(self):
        task = self.task
        return None if task is None else task.handler

    @property
    def url(self):
        return generate_url(
            "internal",
            f"/spoilr/interaction/{self.interaction.slug}/{self.team.username}",
        )

    # these methods are somewhat hunt / discord specific
    def created_discord_message(self):
        return (
            f"Interaction #{self.pk} triggered by {self.team} for {self.interaction} {self.interaction.interaction_type}\n"
            f"**Claim and resolve:** {self.url}\n"
        )

    def claimed_discord_message(self, claimer):
        return f"Interaction #{self.pk} claimed by {claimer}"

    def unclaimed_discord_message(self):
        return f"Interaction #{self.pk} was unclaimed"

    @classmethod
    def responded_discord_message(cls, interaction):
        return f"Interaction #{interaction.pk} resolved by {interaction.handler}\n"

    class Meta:
        unique_together = ("team", "interaction")
        verbose_name_plural = "Interaction access"


### Section: Extra puzzle behavior.


class Minipuzzle(models.Model):
    """
    The model for a team's progress on minipuzzles within a puzzle.
    """

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    ref = models.CharField(max_length=128)
    solved = models.BooleanField(default=False)

    create_time = models.DateTimeField(auto_now_add=True)
    solved_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [["team", "puzzle", "ref"]]


class PseudoAnswer(models.Model):
    """
    Possible answers a solver might input that don't mark the puzzle as correct,
    but need handling.

    For example, they might provide a nudge for teams that are on the right
    track, or special instructions for how to obtain the correct answer.
    """

    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    answer = models.CharField(max_length=100)
    response = models.TextField()

    def __str__(self):
        return '"%s" (%s)' % (self.puzzle.name, self.answer)

    class Meta:
        unique_together = ("puzzle", "answer")
        ordering = ["puzzle", "answer"]

    def natural_key(self):
        return (self.puzzle.slug, self.answer)

    @property
    def normalized_answer(self):
        return Puzzle.normalize_answer(self.answer)


class PseudoAnswerManager(models.Manager):
    def get_by_natural_key(self, puzzle_slug, answer):
        return self.get(puzzle__slug=puzzle_slug, answer=answer)


### Section: Puzzle and minipuzzle submission.


class PuzzleSubmission(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    raw_answer = models.TextField()
    answer = models.CharField(max_length=500)
    correct = models.BooleanField(default=False)
    partial = models.BooleanField(default=False)

    def __str__(self):
        return "%s: %s submitted for %s" % (self.timestamp, self.team, self.puzzle)

    class Meta:
        unique_together = ("team", "puzzle", "answer")
        ordering = ["-timestamp"]


class MinipuzzleSubmission(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)

    minipuzzle = models.ForeignKey(Minipuzzle, on_delete=models.CASCADE)
    raw_answer = models.TextField()
    answer = models.CharField(max_length=100)
    correct = models.BooleanField(default=False)

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.team} -> {self.puzzle} ({self.minipuzzle}): {self.raw_answer}"

    class Meta:
        unique_together = ("team", "puzzle", "minipuzzle", "raw_answer")
        ordering = ["-timestamp"]


### Section: Hunt glue models.


class HuntSetting(models.Model):
    """
    Settings that describe the hunt's current state.

    This is a shared repository for spoilr and hunt-specific code, so be careful
    to namespace settings to avoid collisions.
    """

    name = models.CharField(max_length=200, unique=True)

    # Only one of the following fields should be set.
    text_value = models.TextField(null=True, blank=True)
    boolean_value = models.BooleanField(null=True, blank=True)
    date_value = models.DateTimeField(null=True, blank=True)

    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Setting {self.name}"

    def save(self, *args, **kwargs):
        # To allow editing in admin
        if not self.text_value:
            self.text_value = None
        super(HuntSetting, self).save(*args, **kwargs)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(
                        text_value__isnull=False,
                        boolean_value__isnull=True,
                        date_value__isnull=True,
                    )
                    | models.Q(
                        text_value__isnull=True,
                        boolean_value__isnull=False,
                        date_value__isnull=True,
                    )
                    | models.Q(
                        text_value__isnull=True,
                        boolean_value__isnull=True,
                        date_value__isnull=False,
                    )
                    | models.Q(
                        text_value__isnull=True,
                        boolean_value__isnull=True,
                        date_value__isnull=True,
                    )
                ),
                name="%(app_label)s_%(class)s_one_value",
            ),
        ]


class SystemLog(models.Model):
    """Audit log for any changes to the hunt state."""

    timestamp = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(max_length=50)
    team = models.ForeignKey(Team, blank=True, null=True, on_delete=models.SET_NULL)
    object_id = models.CharField(max_length=200, blank=True, null=True)
    message = models.TextField()

    def __str__(self):
        prefix = f"[{self.team}] " if self.team else ""
        return f"{prefix} {self.timestamp}: {self.message}"

    class Meta:
        verbose_name_plural = "System log"


# TODO(sahil): Rewrite updates - could use a better model, and move it to its own spoilr app.
class HQUpdate(models.Model):
    """
    Represent a message from headquarters to all teams. Shows up on an "updates" page as well as going out by
    email
    """

    subject = models.CharField(max_length=200)
    body = models.TextField()
    published = models.BooleanField(default=False)
    creation_time = models.DateTimeField(auto_now_add=True)
    modification_time = models.DateTimeField(blank=True, auto_now=True)
    publish_time = models.DateTimeField(blank=True, null=True)
    team = models.ForeignKey(Team, blank=True, null=True, on_delete=models.SET_NULL)
    puzzle = models.ForeignKey(
        Puzzle,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        verbose_name="Errata for Puzzle",
        help_text="Select if this update is an erratum that should appear on the puzzle page. Leave blank for general updates.",
    )
    send_email = models.BooleanField(default=True)
    notify_emails = models.TextField(
        default="none",
        help_text="Who should receive this update via email. Use 'all' for everyone, 'captain' for team captain, or a comma-separated list of emails.",
    )

    def __str__(self):
        return "%s" % (self.subject)

    def render_data(self):
        return {
            "text": self.body,
            "time": self.creation_time,
            "puzzleName": self.puzzle.name if self.puzzle else None,
        }

    # Mostly copied from hints/models.
    def get_emails(self, team):
        if self.notify_emails == "captain":
            return [team.contact_email] if team.contact_email else []
        return team.all_emails

    @property
    def recipients(self):
        if self.notify_emails == "none":
            return []

        if self.notify_emails in ("all", "captain"):
            if self.team:
                teams = [self.team]
            elif self.puzzle:
                teams = self.puzzle.get_teams_unlocked()
            else:
                teams = Team.objects.all()

            return [(team, self.get_emails(team)) for team in teams]

        return [([], [s.strip() for s in self.notify_emails.split(",")])]
