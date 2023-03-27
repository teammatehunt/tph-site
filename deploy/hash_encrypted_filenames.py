#!/usr/bin/env python3
"""
This hashes the names of files under client/encrypted so that they don't leak.
This should only be run by the Dockerfile when building for staging/prod.
These files must be imported with useEncryptedDynamic.

NB: This is not idempotent!
"""

import argparse
import hashlib
from pathlib import Path
import shutil


# length of hash file length in the next.config.js
FILENAME_HASH_LENGTH = 8


def run_rename(root, parent):
    """
    Recursively hash filenames of files in parent and place directly under root.
    """
    # get all children before we start modifying
    children = list(parent.iterdir())
    for child in children:
        if child.is_dir():
            run_rename(root, child)
            child.rmdir()
        else:
            stem = child.stem
            if stem.startswith("."):
                # skip dot files like .keep
                continue
            if stem == "index":
                stem = child.parent.name
            name = hashlib.sha256(stem.encode()).hexdigest()[:FILENAME_HASH_LENGTH]
            dest = root / f"{name}{child.suffix}"
            assert not dest.exists()
            # NB: shutil.move needed over child.rename because the move gets
            #     put on a new docker layer
            shutil.move(child, dest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("encrypted_dir")
    args = parser.parse_args()
    root = Path(args.encrypted_dir)
    run_rename(root, root)


if __name__ == "__main__":
    main()
