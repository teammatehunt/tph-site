# Command to generate a new puzzle with the relevant fields.
import random
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from puzzles.models import Puzzle, Round


# TODO: Rewrite this to automatically import from PuzzUp.
class Command(BaseCommand):
    help = "Generates a new puzzle with given arguments"

    def add_arguments(self, parser):
        parser.add_argument("title", type=str)
        parser.add_argument(
            "--round",
            nargs="?",
            type=str,
            choices=Round.objects.values_list("name", flat=True),
        )
        parser.add_argument("--answer", nargs="?", type=str, default="REDACTED")
        parser.add_argument("--is-meta", action="store_true")

    def handle(self, *args, **options):
        title = options["title"]
        answer = options["answer"]
        puzzle_round = Round.objects.get(name=options["round"])
        slug = slugify(title)

        puzzle = Puzzle.objects.create(
            name=title,
            slug=slug,
            answer=answer,
            round=puzzle_round,
            deep=0,
            is_meta=options["is_meta"],
            external_id=10000,
            order=10000,
        )
        # TODO: set external_id, order, and other fields from PuzzUp instead of hard-coding.
        puzzle.external_id = puzzle.pk
        puzzle.order = puzzle.pk
        puzzle.save()

        # print the puzzle slug.
        self.stdout.write(slug)
