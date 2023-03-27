import distutils.util
import os

from .staging import *

SEND_DISCORD_ALERTS = False
# this variable could be better named, but IS_TEST is effectively only being
# used to determine whether we should send real emails, and we do not want to
# for posthunt
IS_TEST = True
