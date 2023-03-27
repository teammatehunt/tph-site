#!/usr/bin/env python3
"""
This script can be used to crop transparent parts out of images.

It will also output the positioning attributes for the factory csv.

To use, run as:
python3 crop.py ~/path/to/input-image.png

This will output the cropped image as ~/path/to/input-image-cropped.png.
"""
import argparse
from pathlib import Path

import imageio
import numpy as np


def format(f):
    return f"{f:.3f}".rstrip("0").rstrip(".")


def main(fin, fout):
    fin = Path(fin)
    if fout is None:
        fout = fin.parent / f"{fin.stem}-cropped{fin.suffix}"
    else:
        fout = Path(fout)
    img = imageio.v3.imread(fin)
    if img.shape[-1] != 4:
        raise RuntimeError("Input image does not have alpha channel")
    HEIGHT = img.shape[0]
    PX2PCT = 1.0 / HEIGHT * 100
    mask = img[..., -1] != 0
    y, x = np.indices(img.shape[:-1])
    ymin = np.min(y[mask])
    xmin = np.min(x[mask])
    ymax = np.max(y[mask])
    xmax = np.max(x[mask])
    h = ymax - ymin + 1
    w = xmax - xmin + 1
    cropped_img = img[ymin : ymax + 1, xmin : xmax + 1]
    imageio.imwrite(fout, cropped_img)
    print(
        "\n".join(
            [
                f"These are sizing attributes relative to the original dimensions of the given image.",
                f"  x (left-aligned): {format(xmin * PX2PCT)}",
                f"x (center-aligned): {format((xmin+xmax)/2 * PX2PCT)}",
                f"                 y: {format(ymin * PX2PCT)}",
                f"            height: {format(h * PX2PCT)}",
                f"             ratio: {format(w / h)}",
                f"         worldMinX: {format(xmin * PX2PCT)}",
                f"         worldMaxX: {format((xmax+1) * PX2PCT)}",
            ]
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Filename of image to be cropped")
    parser.add_argument(
        "--output",
        help="Output filename. Defaults to [input-name]-cropped.[input-image-type]",
    )
    args = parser.parse_args()

    main(args.input, args.output)
