# Command to generate or load puzzle fixtures into a directory.
import os
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.management import CommandError, call_command
from django.core.management.base import BaseCommand
from puzzles.models import Puzzle, Round
from puzzles.models.story import StoryCard
from spoilr.core.models import Interaction
from spoilr.email.models import CannedEmail
from spoilr.events.models import Event

EXTENSION = ".yaml"
MODELS = ["puzzles", "rounds", "events", "story", "interactions", "emails"]


class Command(BaseCommand):
    help = "Loads or saves puzzle fixtures into a directory."

    def add_arguments(self, parser):
        parser.add_argument("--fixtures-dir", type=str)
        parser.add_argument("--save", action="store_true")
        parser.add_argument(
            "--model",
            "--models",
            help=f"Choose from {MODELS}",
            nargs="+",
            default=MODELS,
        )

    def _puzzle_path(self, fixture, extension=""):
        return os.path.join(self.puzzle_directory, fixture + extension)

    def _round_path(self, fixture, extension=""):
        return os.path.join(self.round_directory, fixture + extension)

    def _events_path(self, fixture, extension=""):
        return os.path.join(self.events_directory, fixture + extension)

    def _story_path(self, fixture, extension=""):
        return os.path.join(self.story_directory, fixture + extension)

    def _interactions_path(self, fixture, extension=""):
        return os.path.join(self.interactions_directory, fixture + extension)

    def _emails_path(self, fixture, extension=""):
        return os.path.join(self.emails_directory, fixture + extension)

    def _dumpdata(self, model, **options):
        call_command("dumpdata", model, format="yaml", verbosity=0, **options)

    def _appenddata(self, model, pks="", output=""):
        # Unfortunately dumpdata doesn't support both pks and multiple models,
        # so we have to save to a temp file and then append it to the output.
        with NamedTemporaryFile() as temp_file:
            self._dumpdata(model, pks=pks, output=temp_file.name)

            temp_file.seek(0)
            with open(output, "a+b") as fixture:
                fixture.write(temp_file.read())

    def _save_round_fixtures(self):
        for round_ in Round.objects.all():
            path = self._round_path(round_.slug, extension=EXTENSION)
            self._dumpdata("spoilr_core.Round", pks=str(round_.pk), output=path)
            self.stdout.write(f"Successfully saved fixture: {path}")

    def _save_puzzle_fixtures(self):
        for puzzle in Puzzle.objects.prefetch_related("pseudoanswer_set"):
            path = self._puzzle_path(puzzle.slug, extension=EXTENSION)
            self._dumpdata("puzzles.Puzzle", pks=str(puzzle.pk), output=path)
            self._appenddata(
                "spoilr_core.Puzzle", pks=str(puzzle.spoilr_puzzle_id), output=path
            )

            # Save partial answers, e.g. "Keep going" messages
            message_pks = [str(message.pk) for message in puzzle.pseudoanswer_set.all()]
            if message_pks:
                self._appenddata(
                    "spoilr_core.PseudoAnswer",
                    pks=",".join(message_pks),
                    output=path,
                )

            # Save canned hints
            hint_pks = [str(hint.pk) for hint in puzzle.canned_hints.all()]
            if hint_pks:
                self._appenddata(
                    "spoilr_hints.CannedHint",
                    pks=",".join(hint_pks),
                    output=path,
                )

            self.stdout.write(f"Successfully saved fixture: {path}")

    def _save_event_fixtures(self):
        for event in Event.objects.all():
            path = self._events_path(event.slug, extension=EXTENSION)
            self._dumpdata("spoilr_events.Event", pks=str(event.pk), output=path)
            self.stdout.write(f"Successfully saved fixture: {path}")

    def _save_story_fixtures(self):
        for story in StoryCard.objects.all():
            path = self._story_path(story.slug, extension=EXTENSION)
            self._dumpdata("puzzles.StoryCard", pks=str(story.pk), output=path)
            self.stdout.write(f"Successfully saved fixture: {path}")

    def _save_interaction_fixtures(self):
        for interaction in Interaction.objects.all():
            path = self._interactions_path(interaction.slug, extension=EXTENSION)
            self._dumpdata(
                "spoilr_core.Interaction", pks=str(interaction.pk), output=path
            )
            self.stdout.write(f"Successfully saved fixture: {path}")

    def _save_email_fixtures(self):
        for email in CannedEmail.objects.all():
            path = self._emails_path(email.slug, extension=EXTENSION)
            self._dumpdata("spoilr_email.CannedEmail", pks=str(email.pk), output=path)
            self.stdout.write(f"Successfully saved fixture: {path}")

    def _load_round_fixtures(self):
        fixtures = []
        for f in os.listdir(self.round_directory):
            path = self._round_path(f)
            if os.path.isfile(path) and path.endswith(EXTENSION):
                fixtures.append(path)

        if not fixtures:
            print("No round fixtures found in directory. Skipping.")
            return

        call_command("loaddata", *fixtures)

    def _load_puzzle_fixtures(self):
        fixtures = []
        for f in os.listdir(self.puzzle_directory):
            path = self._puzzle_path(f)
            if os.path.isfile(path) and path.endswith(EXTENSION):
                fixtures.append(path)

        if not fixtures:
            print("No puzzle fixtures found in directory. Skipping.")
            return

        call_command("loaddata", *fixtures)

    def _load_event_fixtures(self):
        fixtures = []
        for f in os.listdir(self.events_directory):
            path = self._events_path(f)
            if os.path.isfile(path) and path.endswith(EXTENSION):
                fixtures.append(path)

        if not fixtures:
            print("No events fixtures found in directory. Skipping.")
            return

        call_command("loaddata", *fixtures)

    def _load_story_fixtures(self):
        fixtures = []
        for f in os.listdir(self.story_directory):
            path = self._story_path(f)
            if os.path.isfile(path) and path.endswith(EXTENSION):
                fixtures.append(path)

        if not fixtures:
            print("No story fixtures found in directory. Skipping.")
            return

        call_command("loaddata", *fixtures)

    def _load_interaction_fixtures(self):
        fixtures = []
        for f in os.listdir(self.interactions_directory):
            path = self._interactions_path(f)
            if os.path.isfile(path) and path.endswith(EXTENSION):
                fixtures.append(path)

        if not fixtures:
            print("No interaction fixtures found in directory. Skipping.")
            return

        call_command("loaddata", *fixtures)

    def _load_email_fixtures(self):
        fixtures = []
        for f in os.listdir(self.emails_directory):
            path = self._emails_path(f)
            if os.path.isfile(path) and path.endswith(EXTENSION):
                fixtures.append(path)

        if not fixtures:
            print("No email fixtures found in directory. Skipping.")
            return

        call_command("loaddata", *fixtures)

    def handle(self, *args, **options):
        self.puzzle_directory = os.path.join(
            settings.BASE_DIR, options["fixtures_dir"], "puzzles"
        )
        self.round_directory = os.path.join(
            settings.BASE_DIR, options["fixtures_dir"], "rounds"
        )
        self.events_directory = os.path.join(
            settings.BASE_DIR, options["fixtures_dir"], "events"
        )
        self.story_directory = os.path.join(
            settings.BASE_DIR, options["fixtures_dir"], "story"
        )
        self.interactions_directory = os.path.join(
            settings.BASE_DIR, options["fixtures_dir"], "interactions"
        )
        self.emails_directory = os.path.join(
            settings.BASE_DIR, options["fixtures_dir"], "emails"
        )

        def check_dir(path):
            if not os.path.isdir(path):
                raise CommandError(f"Invalid path specified: {path}")

        for d in (
            self.puzzle_directory,
            self.round_directory,
            self.events_directory,
            self.story_directory,
            self.emails_directory,
        ):
            check_dir(d)

        if options["save"]:
            if "rounds" in options["model"]:
                self._save_round_fixtures()
            if "puzzles" in options["model"]:
                self._save_puzzle_fixtures()
            if "events" in options["model"]:
                self._save_event_fixtures()
            if "story" in options["model"]:
                self._save_story_fixtures()
            if "interactions" in options["model"]:
                self._save_interaction_fixtures()
            if "emails" in options["model"]:
                self._save_email_fixtures()
        else:
            if "rounds" in options["model"]:
                self._load_round_fixtures()
            if "puzzles" in options["model"]:
                self._load_puzzle_fixtures()
            if "events" in options["model"]:
                self._load_event_fixtures()
            if "story" in options["model"]:
                self._load_story_fixtures()
            if "interactions" in options["model"]:
                self._load_interaction_fixtures()
            if "emails" in options["model"]:
                self._load_email_fixtures()
