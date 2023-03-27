import distutils.util
import os

from .base import *

DEBUG = False

SEND_DISCORD_ALERTS = True

EMAIL_USER_DOMAIN = os.environ.get("EMAIL_USER_DOMAIN", "FIXME.com")

IS_TEST = bool(
    distutils.util.strtobool(
        os.environ.get("IS_TEST", str(EMAIL_USER_DOMAIN not in HOSTS))
    )
)
EMAIL_HOST_USER = f"{EMAIL_USER_LOCALNAME}@{EMAIL_USER_DOMAIN}"

# for emailing Django errors, uncomment the AdminEmailHandler in LOGGING
# ADMINS = [("Matt", "FIXME@gmail.com")]

# FIXME: restrict this
ALLOWED_HOSTS = ["*"]
