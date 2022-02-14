import datetime

from django.conf import settings
from django.utils import timezone

# FIXME: update hunt config!

# included in various templates. NOTE, sometimes appears with a "the" before
# it, maybe check those are what you want.
HUNT_TITLE = "FIXME Puzzle Hunt"

# included in various templates and displayed on the static site
HUNT_ORGANIZERS = "FIXME"

# included in various templates and set as reply-to for automatic emails
CONTACT_EMAIL = f"help@{settings.EMAIL_USER_DOMAIN}"

# the sender from which automatic emails are sent; your mail sending service
# might require you set this to something (check settings/base.py to put your
# actual mail sending service credentials)
MESSAGING_SENDER_EMAIL = f"admin@{settings.EMAIL_USER_DOMAIN}"


HUNT_START_TIME = timezone.make_aware(
    datetime.datetime(year=2023, month=1, day=13, hour=12, minute=0)
)

HUNT_END_TIME = timezone.make_aware(
    datetime.datetime(year=2023, month=1, day=16, hour=12, minute=0)
)

HUNT_CLOSE_TIME = timezone.make_aware(
    datetime.datetime(year=2023, month=1, day=23, hour=0, minute=0)
)

TEAM_SIZE = 8

# Ratelimiting, unlimited guesses.
MAX_GUESSES_PER_PUZZLE = 999999

# Min time a team needs to be registered before they get access to hints.
TEAM_AGE_BEFORE_HINTS = datetime.timedelta(hours=2)
# Days before hints get unlocked, 2 per day.
DAYS_BEFORE_HINTS = 1
# If set, the first N hints a team unlocks can only be used on intro round.
INTRO_HINTS = 2

# Below is not used but let's make it consistent anyways.
DAYS_BEFORE_FREE_ANSWERS = 999999

# The min deep a team should have at a given point in time.
# This is defined as an offset from first puzzle unlock (which should be whenever
# the team first loads a page that needs to display puzzle data).
TIME_UNLOCKS = (
    (datetime.timedelta(hours=0), 0),
    (datetime.timedelta(hours=3), 1),
    (datetime.timedelta(hours=7), 2),
    (datetime.timedelta(hours=11), 4),
    (datetime.timedelta(hours=15), 6),
    (datetime.timedelta(hours=19), 8),
    (datetime.timedelta(hours=23), 10),
)

# 20/24 hours
GUESSES_PER_PERIOD = 20
SECONDS_PER_PERIOD = 86400

# DEEP value used to indicate that you can see everything, e.g. the hunt is over.
DEEP_MAX = float("inf")
# Slug for the intro meta.
INTRO_ROUND = "intro"
INTRO_META_SLUGS = ("intro-meta",)
# Slugs for main round metas
MAIN_ROUNDS = ("round1", "round2")
MAIN_ROUND_META_SLUGS = ("main-meta",)
# Slug for the metameta.
META_META_SLUG = "meta-meta"
# Free answers are given out each day after helpers.DAYS_BEFORE_FREE_ANSWERS.
FREE_ANSWERS_PER_DAY = [1, 2, 2]
ADMIN_TEAM_NAME = "FIXME"
