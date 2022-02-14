import distutils.util
import os

from .base import *

DEBUG = False

SEND_DISCORD_ALERTS = True

# FIXME
EMAIL_USER_DOMAIN = "staging.mypuzzlehunt.com"

IS_TEST = bool(
    distutils.util.strtobool(
        os.environ.get("IS_TEST", str(EMAIL_USER_DOMAIN != DOMAIN))
    )
)

ALLOWED_HOSTS = ["localhost", DOMAIN]

EMAIL_SUBJECT_PREFIX = "(staging) " + EMAIL_SUBJECT_PREFIX

MEDIA_ROOT = "/srv/media"
