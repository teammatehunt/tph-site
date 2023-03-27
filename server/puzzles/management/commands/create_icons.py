# Command to generate icons.
import csv
from io import BytesIO
import os

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from puzzles.models import Puzzle
from PIL import Image


class Command(BaseCommand):
    help = "Generates icons for all puzzle given a directory of assets."

    def add_arguments(self, parser):
        parser.add_argument("directory", type=str)
        parser.add_argument("--save_icons", action="store_true")

    def read_csv(self):
        with open(os.path.join(self.directory, "icons.csv")) as f:
            reader = csv.DictReader(f)
            self.puzzle_info = []
            for row in reader:
                self.puzzle_info.append(row)

    def slug_exists(self, slug):
        for row in self.puzzle_info:
            if row["Slug"] == slug:
                return True
        return False

    def get_x(self, puzzle):
        for row in self.puzzle_info:
            if row["Slug"] == puzzle.slug:
                return int(row["Left"])
        raise ValueError(f"Did not find {puzzle.slug} x-offset")

    def get_y(self, puzzle):
        for row in self.puzzle_info:
            if row["Slug"] == puzzle.slug:
                return int(row["Top"])
        raise ValueError(f"Did not find {puzzle.slug} y-offset")

    def get_text_x(self, puzzle):
        for row in self.puzzle_info:
            if row["Slug"] == puzzle.slug:
                return int(row["Text X"])
        raise ValueError(f"Did not find {puzzle.slug} text x-offset")

    def get_text_y(self, puzzle):
        for row in self.puzzle_info:
            if row["Slug"] == puzzle.slug:
                return int(row["Text Y"])
        raise ValueError(f"Did not find {puzzle.slug} text y-offset")

    def width(self, puzzle):
        for row in self.puzzle_info:
            if row["Slug"] == puzzle.slug:
                return int(row["Icon Width"][:-2])
        raise ValueError(f"Did not find {puzzle.slug} width")

    def height(self, puzzle):
        # check if height is known
        for row in self.puzzle_info:
            if row["Slug"] == puzzle.slug and "Icon Height" in row:
                return int(row["Icon Height"][:-2])
        # Okay, nvm, infer by image.
        # The given CSV defines icons by their width.
        # For dumb CSS reasons, we need to set icon heights for layouts to work properly.
        # This computes the height offline by finding image dimensions and converting the
        # width in CSV to height the site should set it to.
        width = self.width(puzzle)
        # this is awful
        path = os.path.join(self.path(puzzle), "intro-unsolved.png")
        if path in self.dimensions:
            dims = self.dimensions[path]
        else:
            dims = self.dimensions[os.path.join(self.path(puzzle), "unsolved.png")]
        # Determine conversion factor for the height
        # Must be an int
        img_w, img_h = dims
        return round(img_h / float(img_w) * width)

    def bg(self, puzzle):
        for row in self.puzzle_info:
            if row["Slug"] == puzzle.slug:
                return row["Symbol that appears behind when solved"]
        raise ValueError(f"Did not find {puzzle.slug} background")

    def upload_image(self, image, filename):
        # Clean up old images
        if image and image.url:
            image.delete(save=False)

        try:
            bytes_io = BytesIO()
            if filename.endswith("svg"):
                # We assume it's square.
                self.dimensions[filename] = (150, 150)
                with open(filename, "rb") as f:
                    bytes_io = BytesIO(f.read())
            else:
                with open(filename, "rb") as f:
                    img = Image.open(f)
                    self.dimensions[filename] = (img.width, img.height)
                    # An arbitrary constant that should be a bit larger than any icon we care about.
                    target_width = 300
                    aspect_ratio = img.width / float(img.height)
                    if img.width > target_width:
                        # Becaues Herman said this looks better for handdrawn things.
                        img = img.resize(
                            (target_width, int(target_width / aspect_ratio)),
                            resample=Image.BICUBIC,
                        )
                    img.save(bytes_io, format="PNG", optimize=True)
            # Image will get automatically renamed
            image.save(f"{filename}", ContentFile(bytes_io.getvalue()))
        except FileNotFoundError:
            # placeholder
            import pdb

            pdb.set_trace()

    def path(self, puzzle):
        return os.path.join(self.directory, puzzle.slug)

    def handle(self, *args, **options):
        self.directory = options["directory"]
        self.read_csv()
        self.dimensions = {}
        # Do some basic validation before going forward.
        missing_img = []
        missing_csv = []
        for puzzle in Puzzle.objects.all():
            if not os.path.isdir(self.path(puzzle)):
                missing_img.append(puzzle.slug)
            if not self.slug_exists(puzzle.slug):
                missing_csv.append(puzzle.slug)
        if missing_img:
            print(f"Could not find {missing_img} in icons directory")
            return
        if missing_csv:
            print(f"Could not find {missing_csv} in icons CSV")
            return
        print("Found every slug, uploading icons")
        for puzzle in Puzzle.objects.all():
            puzzle.icon_x = self.get_x(puzzle)
            puzzle.icon_y = self.get_y(puzzle)
            puzzle.text_x = self.get_text_x(puzzle)
            puzzle.text_y = self.get_text_y(puzzle)
            if not options["save_icons"]:
                print(
                    "Skipping icon update, only updating x/y. Note icons must be loaded to adjust icon size!"
                )
                puzzle.save()
                print(f"Completed {puzzle.slug}")
                continue
            # Save the icons
            self.upload_image(
                puzzle.unsolved_icon,
                os.path.join(self.path(puzzle), "unsolved.png"),
            )
            self.upload_image(
                puzzle.solved_icon, os.path.join(self.path(puzzle), "solved.png")
            )
            # Height must be set after dimensions are known.
            puzzle.icon_size = self.height(puzzle)
            puzzle.save()
            print(f"Completed {puzzle.slug}")
