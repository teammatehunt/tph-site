import distutils.util
import os

from .base import *

DEBUG = False

SEND_DISCORD_ALERTS = True

# FIXME
EMAIL_USER_DOMAIN = "mypuzzlehunt.com"

IS_TEST = bool(
    distutils.util.strtobool(
        os.environ.get("IS_TEST", str(EMAIL_USER_DOMAIN != DOMAIN))
    )
)

# for emailing Django errors
ADMINS = [("admin", "mypuzzlehunt@gmail.com")]

# FIXME: restrict this
ALLOWED_HOSTS = ["*"]
