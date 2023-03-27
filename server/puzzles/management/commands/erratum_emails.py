from django.core.management.base import BaseCommand
from puzzles.models import PuzzleAccess, Team


class Command(BaseCommand):
    help = "List all email addresses of players on teams that have unlocked a certain puzzle"

    def add_arguments(self, parser):
        parser.add_argument("puzzle_slug", nargs=1, type=str)

    def handle(self, *args, **options):
        slug = options["puzzle_slug"][0]
        self.stdout.write("Getting email addresses for puzzle {}...\n\n".format(slug))
        teams = PuzzleAccess.objects.filter(puzzle__puzzle__slug=slug).values_list(
            "team", flat=True
        )
        members = []
        for team in teams:
            members.extend(team.all_emails)
        if len(members) > 0:
            self.stdout.write(", ".join(members))
            self.stdout.write(
                self.style.SUCCESS("\n\nFound {} team members.".format(len(members)))
            )
        else:
            self.stdout.write(
                self.style.FAILURE("Found {} team members.".format(len(members)))
            )
