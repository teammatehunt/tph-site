# Command to generate a new puzzle with the relevant fields.
import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image
from puzzles.hunt_config import META_META_SLUG
from puzzles.models import Puzzle, StoryCard

STORY_CARD_DEEP = {
    # FIXME: create map from slug to deep.
}


class Command(BaseCommand):
    help = "Generates a storycard per puzzle given a directory"

    def add_arguments(self, parser):
        parser.add_argument("directory", type=str)
        parser.add_argument("--round", type=str, nargs="?", default="all")
        parser.add_argument("-w", type=int, nargs="?", default=1000)

    def upload_image(self, image, filename, resize=False):
        # Clean up old images
        if image and image.url:
            image.delete(save=False)

        bytes_io = BytesIO()
        with Image.open(f"{self.directory}/{filename}") as img:
            aspect_ratio = img.width / img.height
            new_width = self.width
            new_height = int(new_width / aspect_ratio)
            if resize and (img.width > new_width or img.height > new_height):
                img = img.resize((new_width, new_height))

            img.save(bytes_io, format="PNG")

        # Image will get automatically renamed
        image.save(f"{filename}", ContentFile(bytes_io.getvalue()))

    def handle(self, *args, **options):
        self.directory = options["directory"]
        self.width = options["w"]
        self.round = options["round"]

        all_puzzles = (
            Puzzle.objects.all()
            if self.round == "all"
            else Puzzle.objects.filter(round=self.round)
        )
        puzzle_map = {}
        for p in all_puzzles:
            puzzle_map[p.slug] = p

        for f in os.listdir(self.directory):
            if os.path.isfile(os.path.join(self.directory, f)):
                self.process_image(f, puzzle_map)

    def process_image(self, filename, puzzle_map):
        slug, extension = os.path.splitext(filename)

        is_post = slug.endswith("-post")
        is_pre = slug.endswith("-pre")
        puzzle_slug = slug.rsplit("-", 1)[0] if (is_post or is_pre) else slug

        puzzle = puzzle_map.get(puzzle_slug, None)
        if puzzle:
            story_card, created = StoryCard.objects.update_or_create(
                slug=slug,
                defaults={
                    "deep": STORY_CARD_DEEP.get(slug)
                    or STORY_CARD_DEEP.get(puzzle_slug, puzzle.deep),
                    "puzzle": puzzle,
                    "unlocks_post_solve": is_post,
                },
            )
        else:
            deep = STORY_CARD_DEEP.get(slug, None)
            if deep is None:
                print(f"Failed to find puzzle or hard-coded deep for slug {slug}")
                return

            story_card, created = StoryCard.objects.update_or_create(
                slug=slug, defaults={"deep": deep}
            )

        # Resize all story cards that aren't main round, non-metas
        resize = not puzzle or puzzle.round == "intro" or puzzle.is_meta

        if not puzzle or puzzle.slug == META_META_SLUG or puzzle.round == "intro":
            self.upload_image(story_card.image, filename, resize=resize)
        story_card.save()
