# Command to generate or load puzzle fixtures into a directory.
import os
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.management import CommandError, call_command
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from puzzles.models import Puzzle

PUZZLE_MODELS = ("puzzles.Puzzle", "puzzles.PuzzleMessage", "puzzles.Errata")
EXTENSION = ".yaml"


class Command(BaseCommand):
    help = "Loads or saves puzzle fixtures into a directory."

    def add_arguments(self, parser):
        parser.add_argument("dir", type=str)
        parser.add_argument("--save", action="store_true")

    def _path(self, fixture, extension=""):
        return os.path.join(self.directory, fixture + extension)

    def _dumpdata(self, model, **options):
        call_command("dumpdata", model, format="yaml", verbosity=0, **options)

    def _save_puzzle_fixtures(self):
        for puzzle in Puzzle.objects.prefetch_related("puzzlemessage_set"):
            path = self._path(puzzle.slug, extension=EXTENSION)
            self._dumpdata("puzzles.Puzzle", pks=str(puzzle.pk), output=path)

            message_pks = [
                str(message.pk) for message in puzzle.puzzlemessage_set.all()
            ]
            if message_pks:
                # Unfortunately dumpdata doesn't support both pks and multiple models,
                # so we have to save to a temp file and then append it to the output.
                with NamedTemporaryFile() as temp_file:
                    self._dumpdata(
                        "puzzles.PuzzleMessage",
                        pks=",".join(message_pks),
                        output=temp_file.name,
                    )

                    temp_file.seek(0)
                    with open(path, "a+b") as fixture:
                        fixture.write(temp_file.read())

            self.stdout.write(f"Successfully saved fixture: {path}")

    def _load_puzzle_fixtures(self):
        fixtures = []
        for f in os.listdir(self.directory):
            path = self._path(f)
            if os.path.isfile(path) and path.endswith(EXTENSION):
                fixtures.append(path)

        if not fixtures:
            raise CommandError("No puzzle fixtures found in directory. Aborting.")

        call_command("loaddata", *fixtures, app_label="puzzles")

    def handle(self, *args, **options):
        self.directory = os.path.join(settings.BASE_DIR, options["dir"])
        if not os.path.isdir(self.directory):
            raise CommandError(f"Invalid path specified: {options['dir']}")

        if options["save"]:
            self._save_puzzle_fixtures()
        else:
            self._load_puzzle_fixtures()
