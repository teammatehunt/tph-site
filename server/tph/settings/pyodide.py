import os

from .base import *

DEBUG = False

SERVER_ENVIRONMENT = "prod"

SEND_DISCORD_ALERTS = False

# FIXME
EMAIL_USER_DOMAIN = "mypuzzlehunt.com"

IS_TEST = True

# disable logging
LOGGING_CONFIG = None

# for emailing Django errors
ADMINS = []

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DATABASE_NAME", "/indexeddb/db.sqlite3"),
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
}
