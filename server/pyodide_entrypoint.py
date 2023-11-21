"""
Entrypoint for loading hunt environment for Pyodide

This file is imported, not executed.
"""

import os
from pathlib import Path
import zipfile

# FIXME
INDEXEDDB_PREFIX = "20xx-"
os.environ["SERVER_HOSTNAME"] = "mypuzzlehunt.com"
os.makedirs("/srv", exist_ok=True)
print("Caching site packages")
compression = zipfile.ZIP_DEFLATED
with zipfile.ZipFile(
    f"/{INDEXEDDB_PREFIX}indexeddb/site-packages.zip", "a", compression=compression
) as zippedf:
    with zipfile.ZipFile(
        f"/{INDEXEDDB_PREFIX}indexeddb/immovable-packages.zip",
        "a",
        compression=compression,
    ) as immovablef:
        immovable_prefixes = [
            "PIL",
            "sqlite3",
            "_sqlite3",
        ]
        packages = "/lib/python3.10"
        site_packages = f"{packages}/site-packages"
        for parent, dirs, filenames in os.walk(packages):
            for filename in filenames:
                path = os.path.join(parent, filename)
                rel_packages = os.path.relpath(path, packages)
                rel_site_packages = os.path.relpath(path, site_packages)
                is_immovable = False
                for prefix in immovable_prefixes:
                    # some of the immovable packages are standard library
                    if rel_packages.startswith(prefix) or rel_site_packages.startswith(
                        prefix
                    ):
                        is_immovable = True
                if not is_immovable and not parent.startswith(site_packages):
                    continue
                zipf = immovablef if is_immovable else zippedf
                relpath = rel_packages if is_immovable else rel_site_packages
                try:
                    zipf.getinfo(relpath)
                except KeyError:
                    zipf.write(path, relpath)
        zipped_touch_files = [
            "django/core/management/commands/__init__.py",
        ]
        for filename in zipped_touch_files:
            try:
                zippedf.getinfo(filename)
            except KeyError:
                zippedf.writestr(filename, "")

print("Starting django")
import django
from django.conf import settings

os.environ["DJANGO_SETTINGS_MODULE"] = f"tph.settings.pyodide"
# lets us run django ORM from javascript async. Must make sure single coroutine
# has access at a time.
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "1"
django.setup()

from tph.utils import sync_indexeddb, reset_db

print("Updating database")
dbcrc_path = Path(f"/{INDEXEDDB_PREFIX}indexeddb/dbcrc.txt")
db_old_crc = None
if dbcrc_path.is_file():
    with open(dbcrc_path) as f:
        db_old_crc = f.read()
reset_db(old_crc=db_old_crc)

sync_indexeddb()
