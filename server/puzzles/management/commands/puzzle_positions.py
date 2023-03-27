# Command to generate fixtures for puzzle positions.
import csv
import os
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.management import CommandError, call_command
from django.core.management.base import BaseCommand
from puzzles.models import Puzzle

MODELS = ["puzzles"]
POSITION_FIELDS = ["icon_x", "icon_y", "icon_size", "icon_ratio", "text_x", "text_y"]
FIELDS_WITH_SLUG = ["slug", *POSITION_FIELDS]


class Command(BaseCommand):
    help = "Loads or saves puzzle positions in a CSV file."

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

    def _puzzle_path(self):
        return os.path.join(self.puzzle_directory, "positions.csv")

    def _save_puzzle_positions(self):
        data = []
        for puzzle in Puzzle.objects.order_by("order"):
            data.append(
                {field: getattr(puzzle, field, None) for field in FIELDS_WITH_SLUG}
            )

        path = self._puzzle_path()
        with open(path, "w") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS_WITH_SLUG)
            writer.writeheader()
            for puzzle in data:
                writer.writerow(puzzle)

        self.stdout.write(f"Successfully saved positions: {path}")

    def _load_puzzle_positions(self):
        path = self._puzzle_path()
        puzzles_by_key = {puzzle.slug: puzzle for puzzle in Puzzle.objects.all()}
        puzzles_to_update = []
        try:
            with open(path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["slug"] not in puzzles_by_key:
                        self.stdout.write(
                            f"Unable to find puzzle with slug {row['slug']}. Please check if this was renamed."
                        )
                        continue

                    for key, value in row.items():
                        if key == "slug":
                            continue
                        setattr(puzzles_by_key[row["slug"]], key, value)
                    puzzles_to_update.append(puzzles_by_key[row["slug"]])

        except OSError:
            raise CommandError(f"Unable to read file {path}. Aborting.")

        Puzzle.objects.bulk_update(puzzles_to_update, POSITION_FIELDS)

    def handle(self, *args, **options):
        if "puzzles" not in options["model"]:
            return

        self.puzzle_directory = os.path.join(
            settings.BASE_DIR, options["fixtures_dir"], "puzzles"
        )

        def check_dir(path):
            if not os.path.isdir(path):
                raise CommandError(f"Invalid path specified: {path}")

        check_dir(self.puzzle_directory)

        if options["save"]:
            self._save_puzzle_positions()
        else:
            self._load_puzzle_positions()
