import os

# set environment variables before loading from settings.base
# FIXME
os.environ["ENABLE_POSTHUNT_SITE"] = "1"
os.environ["CDN_REGISTRATION_HOST"] = "/2023"
os.environ["CDN_HUNT_HOST"] = "/2023"
os.environ["MAIN_HUNT_HOST"] = "mypuzzlehunt.com"
os.environ["REGISTRATION_HOST"] = "register.mypuzzlehunt.com"

from tph.constants import INDEXEDDB_PREFIX

from .base import *

DEBUG = False

SERVER_ENVIRONMENT = "posthunt"

SEND_DISCORD_ALERTS = False

# FIXME
EMAIL_USER_DOMAIN = "mypuzzlehunt.com"

IS_TEST = True

# disable logging
LOGGING_CONFIG = None

# for emailing Django errors
ADMINS = []

ALLOWED_HOSTS = ["*"]

# replace redis caches with sqlite, persisted with indexeddb
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get(
            "DATABASE_NAME", f"/{INDEXEDDB_PREFIX}indexeddb/db.sqlite3"
        ),
    }
}

# replace redis caches with local memory caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "default-cache",
    },
    SPOILR_CACHE_NAME: {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "spoilr-cache",
    },
}
