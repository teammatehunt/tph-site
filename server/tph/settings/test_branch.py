import os

from .staging import *

for host in (MAIN_HUNT_HOST, REGISTRATION_HOST):
    if host is not None:
        ALLOWED_HOSTS.append(f".{host}")
SSO_HOST = None
