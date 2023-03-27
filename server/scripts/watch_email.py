#!/usr/bin/env python3
"Script to start the IMAP client process"

import os

import django

if __name__ == "__main__":
    server_environment = os.environ.get("SERVER_ENVIRONMENT", "dev")
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", f"tph.settings.{server_environment}"
    )
    django.setup()

from puzzles.emailing import ImapClient


def main():
    print("Creating IMAP client")
    ImapClient.create_and_run()


if __name__ == "__main__":
    main()
