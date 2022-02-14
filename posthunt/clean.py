#!/usr/bin/env python3
"""
Next.js export is broken for non urlsafe characters in paths. This script
rectifies these paths. This should be run on a unix machine.
"""
import argparse
import os
from pathlib import Path
import shutil
import urllib.parse


def main(path):
    for root, dirs, files in os.walk(path):
        root = Path(root)
        if root.name == "team":
            for file in files:
                new_fname = urllib.parse.unquote(file)
                if new_fname != file:
                    file = root / file
                    new_fname = root / new_fname
                    os.makedirs(new_fname.parent, exist_ok=True)
                    shutil.move(file, new_fname)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()
    main(args.path)
