from django.core.management.base import BaseCommand
from puzzles.models import Hint, Team


class Command(BaseCommand):
    help = "Takes away all awarded hints from teams"

    def handle(self, *args, **options):
        teams = Team.objects.all()
        for team in teams:
            team.total_hints_awarded = 0
            team.save()
        self.stdout.write(self.style.SUCCESS("Successfully taken away hints"))
