import getpass
import os
import pathlib
import sys

from .base import *

DEBUG = True

SEND_DISCORD_ALERTS = False

IS_TEST = True

DOMAIN = "localhost:8081"

# FIXME
EMAIL_USER_DOMAIN = os.environ.get("EMAIL_USER_DOMAIN", "staging.mypuzzlehunt.com")

ALLOWED_HOSTS = ["*"]

EMAIL_SUBJECT_PREFIX = "(dev) " + EMAIL_SUBJECT_PREFIX
# email addresses to whitelist in testing
# To test emails, create a file `dev_email_whitelist.txt` in the root project
# directory and add your email to it.
if IS_TEST:
    dev_list_file = pathlib.Path(__file__).parents[3] / "dev_email_whitelist.txt"
    if dev_list_file.is_file():
        with open(dev_list_file) as f:
            DEV_EMAIL_WHITELIST.update(f.read().strip().split())

# this is different because webpack-dev-server is serving /static in dev,
# and the webserver needs to be able to point the browser to the right place
STATIC_URL = "/static/"
STATIC_ROOT = "static"

# silk request logging if enabled
SILK_ENABLED = False
if SILK_ENABLED:
    INSTALLED_APPS.append("silk")
    MIDDLEWARE.insert(0, "silk.middleware.SilkyMiddleware")
    # authentication for silk
    SILKY_AUTHENTICATION = True
    SILKY_AUTHORISATION = True
    # discard raw requests and responses exceeding size
    SILKY_MAX_REQUEST_BODY_SIZE = 0
    SILKY_MAX_RESPONSE_BODY_SIZE = 0


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "django-file": {
            "format": "%(asctime)s [%(levelname)s] %(module)s\n%(message)s"
        },
        "puzzles-file": {"format": "%(asctime)s [%(levelname)s] %(message)s"},
        "django-console": {
            "format": "\033[34;1m%(asctime)s \033[35;1m[%(levelname)s] \033[34;1m%(module)s\033[0m\n%(message)s"
        },
        "puzzles-console": {
            "format": "\033[36;1m%(asctime)s \033[35;1m[%(levelname)s] \033[36;1m%(name)s\033[0m %(message)s"
        },
    },
    "handlers": {
        "django": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": LOG_BASE_DIR / "django.log",
            "formatter": "django-file",
        },
        "django-errors": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": LOG_BASE_DIR / "django.error.log",
            "formatter": "django-file",
        },
        "puzzle": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": LOG_BASE_DIR / "puzzle.log",
            "formatter": "puzzles-file",
        },
        "puzzle-errors": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": LOG_BASE_DIR / "puzzle.error.log",
            "formatter": "puzzles-file",
        },
        "request": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": LOG_BASE_DIR / "request.log",
            "formatter": "puzzles-file",
        },
        "request-errors": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": LOG_BASE_DIR / "request.error.log",
            "formatter": "puzzles-file",
        },
        "django-console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "django-console",
        },
        "puzzles-console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "puzzles-console",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["django", "django-console", "django-errors"],
            "level": "DEBUG",
            "propagate": True,
        },
        "django.db.backends": {
            "level": "DEBUG",
            "handlers": ["django"],
            "propagate": False,
        },
        "django.server": {
            "level": "DEBUG",
            "handlers": ["django"],
            "propagate": False,
        },
        "django.utils.autoreload": {
            "level": "INFO",
            "propagate": True,
        },
        "puzzles": {
            "handlers": ["puzzles-console"],
            "level": "DEBUG",
            "propagate": True,
        },
        "puzzles.puzzle": {
            "handlers": ["puzzle", "puzzles-console", "puzzle-errors"],
            "level": "DEBUG",
            "propagate": False,
        },
        "puzzles.request": {
            "handlers": ["request", "puzzles-console", "request-errors"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
try:
    assert getpass.getuser() == "root"
except:
    # The makemigrations script uses the host user, not the user inside the
    # docker container. This causes errors with django file logging, so we
    # disable file logging in this case.
    sys.stderr.write("WARNING: Unknown user, disabling file logging\n")
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
    }
