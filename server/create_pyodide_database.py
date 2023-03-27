#!/usr/bin/env python3
"Script to create and populate a database with fixtures for pyodide."

import argparse
import os

import django
from django.core.management import execute_from_command_line
from django.db.migrations.recorder import MigrationRecorder


MIGRATION_TIMESTAMP = "2023-01-13T20:00:00Z"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("database_file")
    parser.add_argument("fixtures", nargs="*")
    args = parser.parse_args()

    server_environment = "pyodide"
    os.environ["DJANGO_SETTINGS_MODULE"] = f"tph.settings.{server_environment}"
    os.environ["DATABASE_NAME"] = args.database_file
    django.setup()

    # replace default timestamp
    applied = MigrationRecorder.Migration._meta.get_field("applied")
    applied_default = applied.default
    applied.default = MIGRATION_TIMESTAMP
    execute_from_command_line(["manage.py", "migrate"])
    # reset migration model
    applied.default = applied_default

    # load fixtures
    execute_from_command_line(
        [
            "manage.py",
            "loaddata",
            *args.fixtures,
        ]
    )


if __name__ == "__main__":
    main()
