from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from puzzles.hunt_config import DONE_SLUG, META_META_SLUGS
from puzzles.models import Puzzle, PuzzleSubmission, Team
from spoilr.hints.models import Hint


class Command(BaseCommand):
    help = "Computes some useful stats for hunt"

    def handle(self, *args, **options):
        teams = Team.objects.annotate(
            num_solves=Count(
                "puzzlesubmission", filter=Q(puzzlesubmission__correct=True)
            )
        )
        with_solves = lambda n: teams.filter(num_solves__gte=n).count()
        self.stdout.write(f"Teams with 1+ solve: {with_solves(1)}")
        self.stdout.write(f"Teams with 10+ solve: {with_solves(10)}")
        self.stdout.write(f"Teams with 50+ solve: {with_solves(50)}")

        teams = Team.objects.annotate(
            num_solves=Count(
                "puzzlesubmission",
                filter=Q(
                    puzzlesubmission__correct=True,
                    puzzlesubmission__puzzle__is_meta=True,
                ),
            )
        ).filter(num_solves__gte=1)
        self.stdout.write(f"Teams with 1+ meta: {teams.count()}")

        teams = Team.objects.annotate(
            num_solves=Count(
                "puzzlesubmission",
                filter=Q(
                    puzzlesubmission__correct=True,
                    puzzlesubmission__puzzle__slug__in=META_META_SLUGS,
                ),
            )
        ).filter(num_solves__gte=1)
        self.stdout.write(f"Teams finished 1+ metameta: {teams.count()}")

        finishers = Team.objects.annotate(
            num_solves=Count(
                "puzzlesubmission",
                filter=Q(
                    puzzlesubmission__correct=True,
                    puzzlesubmission__puzzle__slug=DONE_SLUG,
                ),
            )
        ).filter(num_solves__gte=1)
        self.stdout.write(f"Teams finished hunt: {teams.count()}")

        puzzles = Puzzle.objects.annotate(
            num_solves=Count(
                "puzzlesubmission", filter=Q(puzzlesubmission__correct=True)
            )
        ).filter(num_solves__gte=1)
        self.stdout.write(f"Puzzles solved at least once: {puzzles.count()}")

        solves = PuzzleSubmission.objects.filter(correct=True)
        self.stdout.write(f"Solves: {solves.count()}")

        guesses = PuzzleSubmission.objects.count()
        self.stdout.write(f"Guesses: {guesses}")

        hints = Hint.objects.filter(
            is_request=False,
            status__in=[Hint.ANSWERED, Hint.REQUESTED_MORE_INFO, Hint.REFUNDED],
        )
        self.stdout.write(f"Hints answered: {hints.count()}")

        most_solved = puzzles.order_by("-num_solves").values_list("name", flat=True)[:5]
        self.stdout.write(f"Most solved: {most_solved}")
        least_solved = puzzles.order_by("num_solves").values_list("name", flat=True)[:5]
        self.stdout.write(f"Least solved: {least_solved}")
