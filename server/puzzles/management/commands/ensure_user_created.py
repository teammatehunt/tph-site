# Command to create a user / team if it doesn't exist
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from puzzles.models import Team


class Command(BaseCommand):
    help = "Creates a user if it doesn't exist."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("--password", type=str, required=True)
        parser.add_argument("--teamname", type=str)
        parser.add_argument("--admin", action="store_true", help="make a superuser")
        parser.add_argument(
            "--prerelease",
            action="store_true",
            help="team will have early access to puzzles",
        )
        parser.add_argument(
            "--unhidden",
            action="store_true",
            help="do not make the team hidden from the leaderboard",
        )
        parser.add_argument(
            "--user-only", action="store_true", help="do not create a team"
        )

    def handle(self, *args, **options):
        if options["teamname"] is None:
            options["teamname"] = options["username"]
        user = User.objects.filter(username=options["username"]).first()
        if user is None:
            if options["admin"]:
                user = User.objects.create_superuser(
                    options["username"], password=options["password"]
                )
                self.stdout.write(f"Created superuser '{options['username']}'")
            else:
                user = User.objects.create_user(
                    options["username"], password=options["password"]
                )
                self.stdout.write(f"Created user '{options['username']}'")
        else:
            dirty = False
            if not user.check_password(options["password"]):
                user.set_password(options["password"])
                dirty = True
            if user.is_superuser != options["admin"]:
                user.is_superuser = options["admin"]
                user.is_staff = options["admin"]
                dirty = True
            if dirty:
                user.save()
                self.stdout.write(f"Updated user '{options['username']}'")
        if not options["user_only"]:
            team, created = Team.objects.get_or_create(
                user=user,
                team_name=options["teamname"],
                defaults={
                    "is_prerelease_testsolver": options["prerelease"],
                    "is_hidden": not options["unhidden"],
                },
            )
            if created:
                self.stdout.write(f"Created team '{options['teamname']}'")
            dirty = False
            if team.is_prerelease_testsolver != options["prerelease"]:
                team.is_prerelease_testsolver = options["prerelease"]
            if team.is_hidden != (not options["unhidden"]):
                team.is_hidden = not options["unhidden"]
            if dirty:
                team.save()
                self.stdout.write(f"Updated team '{options['teamname']}'")
