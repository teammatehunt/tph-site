"""
All python code that we don't want to be public should go here.

All code that imports these should check for `not tph.constants.IS_PYODIDE` first
and have a fallback.
"""

# Should be Discord webhook URLs that look like
# https://discordapp.com/api/webhooks/(numbers)/(letters)
# From a channel you can create them under Integrations > Webhooks.
# They can be the same webhook if you don't care about keeping them in separate
# channels.
DISCORD_WEBHOOKS = {
    "BOT_SPAM": "FIXME",
    "STAGING": "FIXME",
    "ALERT_ALERT": "FIXME",
    "SUBMISSION_ALERT": "FIXME",
    "CONGRAT_ALERT": "FIXME",
    "PROFILE_PIC_ALERT": "FIXME",
    "BAD_PROFILE_PIC_ALERT": "FIXME",
    "EMAIL_RESPONSE_ALERT": "FIXME",
    "HINT_ALERT": "FIXME",
    "HINT_RESPONSE_ALERT": "FIXME",
    "INTERACTION_ALERT": "FIXME",
    "EVENT_ALERT": "FIXME",
    "FEEDBACK_ALERT": "FIXME",
    "MORE_GUESS_ALERT": "FIXME",
}

# These are used by the Discord bot to auto-post hints and emails.
DISCORD_BOT_ENV = {
    # The bot will only parse messages in this channel.
    # FIXME
    "BOT_SPAM_CHANNEL": 123456789,
    "HINT_CHANNEL": 123456789,
    "EMAIL_CHANNEL": 123456789,
    "INTERACTION_CHANNEL": 123456789,
    "TOKEN": "FIXME",
}
