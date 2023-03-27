#!/usr/bin/env python3
"""
This script can be used to resize all images in a directory based on a max width.

To use, run as:
python3 resize_icons.py ~/directory --max-width X [--proportional] [-r]

All images will be resized with their own aspect ratio preserved.
If proportional is true, they will be downscaled by the same amount
(based on the widest image in the directory).

Note: this will overwrite the icons in place.
"""
import argparse
import os
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image


def get_widest_width(dir_name):
    max_width = 0
    for filename in os.listdir(dir_name):
        if not filename.endswith(".png"):
            continue
        with open(os.path.join(dir_name, filename), "rb") as f:
            img = Image.open(f)
            max_width = max(max_width, img.width)
    return max_width


def resize_image(filename, max_width, min_width, scale=None):
    try:
        bytes_io = BytesIO()
        if not filename.endswith(".png"):
            print("Extension not supported, skipping", filename)
            return False

        with open(filename, "rb") as f:
            img = Image.open(f)
            if scale:
                target_width = img.width / scale
            else:
                target_width = max_width

            if img.width <= target_width or img.width <= min_width:
                print(filename, "already smaller than target width")
                return False

            target_width = max(min_width, target_width)

            aspect_ratio = img.width / float(img.height)
            new_width = int(target_width)
            new_height = int(target_width / aspect_ratio)
            print(
                f"Resizing {filename} from {img.width}x{img.height} to {new_width}x{new_height}"
            )
            img = img.resize((new_width, new_height), resample=Image.BICUBIC)
            img.save(filename, format="PNG", optimize=True)
        return True
    except FileNotFoundError:
        print("unable to find", filename)
        return False


def main(
    dir_name, max_width, min_width, proportional=False, recursive=False, skip_dir=None
):
    scale = None
    if proportional:
        widest_image_width = get_widest_width(dir_name)
        scale = widest_image_width / float(max_width)
        if scale < 1:
            print(f"All images are smaller than {max_width}. Aborting")
            return

    skip_dir = skip_dir or []
    if recursive:
        files_to_resize = (
            os.path.join(root, file)
            for root, _, files in os.walk(dir_name)
            for file in files
            if root.split(os.sep)[-1] not in skip_dir
        )
    else:
        files_to_resize = (
            file
            for file in os.listdir(dir_name)
            if os.path.isfile(os.path.join(dir_name, file))
        )

    for file in files_to_resize:
        resize_image(os.path.join(dir_name, file), max_width, min_width, scale=scale)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", help="Directory of images to be resized")
    parser.add_argument("--max-width", help="Max width allowed", default=8000, type=int)
    parser.add_argument("--min-width", help="Min width required", default=100, type=int)
    parser.add_argument("--skip-dir", help="Directories to skip", nargs="*")
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Recursively resizes all subdirectories",
        default=False,
    )
    parser.add_argument(
        "--proportional",
        "-p",
        action="store_true",
        help="If true, scale all images proportionally based on the widest image",
        default=False,
    )
    args = parser.parse_args()
    if args.proportional and args.recursive:
        print("ERROR: Can only specify one of recursive and proportional")

    main(
        args.dir,
        args.max_width,
        args.min_width,
        args.proportional,
        args.recursive,
        args.skip_dir,
    )
