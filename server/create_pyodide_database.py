#!/usr/bin/env python3
"Script to create and populate a database with fixtures for pyodide."

import argparse
import os

import django
from django.core.management import execute_from_command_line


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("database_file")
    parser.add_argument("fixtures", nargs="*")
    args = parser.parse_args()

    server_environment = "pyodide"
    os.environ["DJANGO_SETTINGS_MODULE"] = f"tph.settings.{server_environment}"
    os.environ["DATABASE_NAME"] = args.database_file
    django.setup()

    execute_from_command_line(["manage.py", "migrate"])
    execute_from_command_line(
        [
            "manage.py",
            "loaddata",
            *args.fixtures,
        ]
    )


if __name__ == "__main__":
    main()
