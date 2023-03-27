from enum import IntEnum
from typing import Optional, Union

from django.db import models
from puzzles.assets import get_hashed_url
from spoilr.core.models import Team
from spoilr.utils import generate_url

from .utils import SlugModel


class StoryCard(SlugModel):
    """Story text we want to be displayed.

    This represents the story text, puzzle, and unlock mechanism for the story
    information. However, for a given team, auth is handled by the StoryCardAccess
    model.
    """

    title = models.CharField(max_length=255, blank=True)
    text = models.TextField(blank=True)
    slug = models.SlugField(max_length=200, unique=True)
    order = models.IntegerField(default=0, unique=True)
    act = models.IntegerField(default=1)
    url_path = models.CharField(max_length=255, null=True, blank=True)

    # Optional puzzle - unlocks on puzzle is solved.
    puzzle = models.ForeignKey(
        "Puzzle",
        on_delete=models.CASCADE,
        related_name="story_cards",
        null=True,
        blank=True,
    )

    @property
    def image_url(self) -> Optional[str]:
        return get_hashed_url(f"Story/{self.slug}.png")

    @property
    def puzzle_url(self):
        if not self.puzzle:
            return None

        return self.puzzle.url

    @property
    def url(self):
        """The url to see the story card / interaction."""
        if not self.url_path:
            return None

        return generate_url("hunt", self.url_path)

    def __str__(self):
        def abbr(s):
            if len(s) > 50:
                return s[:50] + "..."
            return s

        return f"[{self.slug}]: {abbr(self.text)}"


class StoryCardAccess(models.Model):
    """Represents a team unlocking a new piece of story."""

    story_card = models.ForeignKey(StoryCard, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%s -> %s @ %s" % (self.team, self.story_card, self.timestamp)

    class Meta:
        unique_together = ("team", "story_card")


class StateEnum(IntEnum):
    # It is assumed that this strictly increases with the plot of the hunt.
    DEFAULT = 0
    STORY_MIDPOINT = 500
    STORY_COMPLETE = 1000

    def __str__(self):
        return self.name


class StoryState(models.Model):
    """Overall team progress through the story.

    Represents a strictly increasing set of milestones a team will reach in the
    story. This is a better fit for "big" irreversible events that are not tied to
    a specific puzzle solve.
    """

    team = models.OneToOneField(Team, on_delete=models.CASCADE)
    # Represents the StateEnum value. Using an integer to avoid needless db migrations.
    state = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.team}: {self.state}"

    @classmethod
    def singleton(cls, team: Union[Team, int]) -> "StoryState":
        """Create or get the singleton state for this team"""
        team_id = team if isinstance(team, int) else team.id
        obj, _ = cls.objects.get_or_create(team_id=team_id)
        return obj

    @classmethod
    def set_state(
        cls,
        team: Union[Team, int],
        new_state: Union[StateEnum, int],
        force=False,
    ):
        story_state = cls.singleton(team)
        if force:
            story_state.state = int(new_state)
        else:
            # Don't allow decrementing story state
            story_state.state = max(story_state.state, int(new_state))
        story_state.save()

    @classmethod
    def get_state(cls, team: Team) -> StateEnum:
        story_state = cls.singleton(team)
        return StateEnum(story_state.state)
