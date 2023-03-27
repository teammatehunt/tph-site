# Command to create a user / team if it doesn't exist
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from puzzles.models import Team
from spoilr.core.models import TeamType, UserTeamRole

User = get_user_model()


class Command(BaseCommand):
    help = "Creates a user if it doesn't exist."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("--password", type=str, required=True)
        parser.add_argument("--teamname", type=str)
        parser.add_argument("--admin", action="store_true", help="make a superuser")
        parser.add_argument(
            "--internal",
            action="store_true",
            help="team will be able to see all puzzles",
        )
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
        team = None
        if not options["user_only"]:
            team, created = Team.objects.update_or_create(
                username=options["teamname"],  # TODO rethink
                defaults={
                    "name": options["teamname"],
                    "is_prerelease_testsolver": options["prerelease"],
                    "type": TeamType.INTERNAL
                    if options["internal"] or options["admin"]
                    else None,
                    "is_hidden": not options["unhidden"],
                },
            )
            if created:
                self.stdout.write(f"Created team '{options['teamname']}'")
            else:
                self.stdout.write(f"Updated team '{options['teamname']}'")
        user = User.objects.filter(username=options["username"]).first()
        if user is None:
            role = UserTeamRole.SHARED_ACCOUNT if not options["user_only"] else None
            if options["admin"]:
                user = User.objects.create_superuser(
                    options["username"],
                    password=options["password"],
                    team=team,
                    team_role=role,
                )
                self.stdout.write(f"Created superuser '{options['username']}'")
            else:
                user = User.objects.create_user(
                    options["username"],
                    password=options["password"],
                    team=team,
                    team_role=role,
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
