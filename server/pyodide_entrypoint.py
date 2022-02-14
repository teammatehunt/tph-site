"""
Entrypoint for loading hunt environment for Pyodide

This file is imported, not executed.
"""

import os
from pathlib import Path
import zipfile

# FIXME
os.environ["SERVER_HOSTNAME"] = "mypuzzlehunt.com"
os.makedirs("/srv", exist_ok=True)
print("Caching site packages")
compression = zipfile.ZIP_DEFLATED
with zipfile.ZipFile(
    "/indexeddb/site-packages.zip", "a", compression=compression
) as zippedf:
    with zipfile.ZipFile(
        "/indexeddb/immovable-site-packages.zip", "a", compression=compression
    ) as immovablef:
        ignore_prefixes = [
            "pyodide",
            "_pyodide",
        ]
        immovable_prefixes = [
            "_distutils",
            "PIL",
            "Pillow",
            "pkg_resources",
            "pyparsing",
            "setuptools",
        ]
        site_packages = "/lib/python3.9/site-packages"
        for parent, dirs, filenames in os.walk(site_packages):
            rel_parent = os.path.relpath(parent, site_packages)
            is_ignore = False
            is_immovable = False
            for prefix in ignore_prefixes:
                if rel_parent.startswith(prefix):
                    is_ignore = True
            if is_ignore:
                continue
            for prefix in immovable_prefixes:
                if rel_parent.startswith(prefix):
                    is_immovable = True
            zipf = immovablef if is_immovable else zippedf
            for filename in filenames:
                path = os.path.join(parent, filename)
                relpath = os.path.relpath(path, site_packages)
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
dbcrc_path = Path("/indexeddb/dbcrc.txt")
db_old_crc = None
if dbcrc_path.is_file():
    with open(dbcrc_path) as f:
        db_old_crc = f.read()
reset_db(old_crc=db_old_crc)

sync_indexeddb()
