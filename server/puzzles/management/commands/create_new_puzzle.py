# Command to generate a new puzzle with the relevant fields.
import random
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from puzzles.models import Puzzle


class Command(BaseCommand):
    help = "Generates a new puzzle with given arguments"

    def add_arguments(self, parser):
        parser.add_argument("title", type=str)
        parser.add_argument(
            "--round", nargs="?", type=str, choices=["intro", "main"]  # FIXME
        )
        parser.add_argument("--answer", nargs="?", type=str, default="REDACTED")
        parser.add_argument("--is-meta", action="store_true")

    def handle(self, *args, **options):
        title = options["title"]
        answer = options["answer"]
        puzzle_round = options["round"]
        slug = slugify(title)

        Puzzle(
            name=title,
            slug=slug,
            answer=answer,
            round=puzzle_round,
            deep=0,
            is_meta=options["is_meta"],
        ).save()

        # print the puzzle slug.
        self.stdout.write(slug)
