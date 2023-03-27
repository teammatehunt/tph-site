import datetime

from django.conf import settings
from django.utils import timezone

# FIXME: update hunt config!

# included in various templates. NOTE, sometimes appears with a "the" before
# it, maybe check those are what you want.
HUNT_TITLE = "teammate hunt 20xx"

# included in various templates and displayed on the static site
HUNT_ORGANIZERS = "teammate"

# included in various templates and set as reply-to for automatic emails
HUNT_CONTACT_EMAIL = f"help@{settings.EMAIL_USER_DOMAIN}"

# the sender from which automatic emails are sent; your mail sending service
# might require you set this to something (check settings/base.py to put your
# actual mail sending service credentials)
MESSAGING_SENDER_EMAIL = f"info@{settings.EMAIL_USER_DOMAIN}"

# Ratelimiting, unlimited guesses.
UNLIMITED_GUESSES = True
MAX_GUESSES_PER_PUZZLE = 999999

# DEEP value used to indicate that you can see everything, e.g. the hunt is over.
DEEP_MAX = float("inf")
ADMIN_TEAM_NAME = "teammate"

# FIXME: Hard-coded puzzle config
# Slug for the metametas.
META_META_SLUGS = ("metameta-slug",)
DONE_SLUG = "final-capstone"

# FIXME: Set up deep unlock structure.
# round slug -> {key: deep}. There can be multiple keys, and keys can be arbitrary strings
# (do not need to be round slugs).
# We expect all rounds to specify deep explicitly here, but code will default to
# adding deep to the round.slug
DEEP_PER_ROUND = {
    "intro": {"intro": 100, "intro-meta": 1},
}

# puzzle/story slug -> {key: deep}. Takes priority over round.
DEEP_PER_SLUG = {
    "intro-meta": {"main": 100},
}

EVENTS_ROUND_SLUG = "events"
