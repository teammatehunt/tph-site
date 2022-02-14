import datetime

from django.db import models
from puzzles.models import Puzzle, Team


class PuzzleState(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    state = models.JSONField()

    class Meta:
        unique_together = ("team", "puzzle")


class PuzzleAction(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)

    datetime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action}: {self.team} -> {self.puzzle} @ {self.datetime}"
