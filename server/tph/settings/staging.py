import distutils.util
import os

from .base import *

DEBUG = False

SEND_DISCORD_ALERTS = True

EMAIL_USER_DOMAIN = os.environ.get("EMAIL_USER_DOMAIN", "staging.teammatehunt.com")

IS_TEST = bool(
    distutils.util.strtobool(
        os.environ.get("IS_TEST", str(EMAIL_USER_DOMAIN not in HOSTS))
    )
)
EMAIL_HOST_USER = f"{EMAIL_USER_LOCALNAME}@{EMAIL_USER_DOMAIN}"

ALLOWED_HOSTS = ["localhost", "django", *HOSTS]

EMAIL_SUBJECT_PREFIX = "(staging) " + EMAIL_SUBJECT_PREFIX

MEDIA_ROOT = "/srv/media"
