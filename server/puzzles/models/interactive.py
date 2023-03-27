import datetime

from django.db import models

from puzzles.models import Puzzle, Team
from puzzles.models.story import StoryCard


class Session(models.Model):
    """
    This holds data relevant to a specific session of a puzzle or story
    """

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE, null=True, blank=True)
    storycard = models.ForeignKey(
        StoryCard, on_delete=models.CASCADE, null=True, blank=True
    )
    start_time = models.DateTimeField(auto_now_add=True)
    finish_time = models.DateTimeField(default=None, null=True, blank=True)
    is_complete = models.BooleanField(default=False)
    state = models.JSONField()

    class Meta:
        constraints = [
            # Require that one of puzzle or storycard is set
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_puzzle_or_storycard_required",
                check=(
                    models.Q(puzzle__isnull=True, storycard__isnull=False)
                    | models.Q(puzzle__isnull=False, storycard__isnull=True)
                ),
            )
        ]

    @classmethod
    def get_running_sessions(cls, team, puzzle):
        return Session.objects.filter(team=team, puzzle=puzzle, is_complete=False)


class PuzzleState(models.Model):
    """
    This holds team-wide state that should be synced between different sessions
    """

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    state = models.JSONField()

    class Meta:
        unique_together = ("team", "puzzle")


class PuzzleAction(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    subpuzzle = models.CharField(max_length=255, blank=True, null=True)
    action_text = models.TextField(blank=True, null=True)

    datetime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action}: {self.team} -> {self.puzzle} @ {self.datetime}"


class UserState(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    uuid = models.CharField(max_length=38)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    state = models.JSONField()

    class Meta:
        unique_together = ("team", "uuid", "puzzle")
