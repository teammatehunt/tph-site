from collections import defaultdict
import email
import logging
import traceback

import requests
from django.conf import settings
from django.core.mail.message import EmailMultiAlternatives
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone

from tph.constants import IS_PYODIDE
from puzzles.hunt_config import (
    HUNT_TITLE,
    HUNT_ORGANIZERS,
    CONTACT_EMAIL,
    MESSAGING_SENDER_EMAIL,
)


if IS_PYODIDE:
    DISCORD_WEBHOOKS = defaultdict(str)
else:
    from tph.secrets import DISCORD_WEBHOOKS


logger = logging.getLogger("puzzles.messaging")


def dispatch_discord_alert(webhook, content, username="TPH Django"):
    content = "[{}] {}".format(timezone.localtime().strftime("%H:%M:%S"), content)
    if len(content) >= 2000:
        content = content[:1996] + "..."
    if settings.IS_TEST:
        logger.info("Discord alert:\n" + content)
        return
    if not settings.SEND_DISCORD_ALERTS:
        return
    if webhook == "FIXME":
        logger.warning("Invalid webhook (FIXME)")
        return  # TODO: fix this

    if settings.SERVER_ENVIRONMENT == "staging":
        # Override with staging webhook.
        webhook = DISCORD_WEBHOOKS["STAGING"]

    try:
        requests.post(
            f"https://discord.com/api/webhooks/{webhook}",
            data={"username": username, "content": content},
        )
    except:
        logger.error(
            "Failed to post to discord webhook with username %s, content: %s",
            username,
            content,
        )


def dispatch_general_alert(content, username="TPH AlertBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["ALERT_ALERT"],
        content,
        username,
    )


def dispatch_submission_alert(content, username="TPH SubmissionBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["SUBMISSION_ALERT"],
        content,
        username,
    )


def dispatch_free_answer_alert(content, username="TPH HelpBot"):
    dispatch_discord_alert("FIXME", content, username)


def dispatch_victory_alert(content, username="TPH CongratBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["CONGRAT_ALERT"],
        content,
        username,
    )


def dispatch_profile_pic_alert(content, username="TPH ProfilePicBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["PROFILE_PIC_ALERT"],
        content,
        username,
    )


def dispatch_bad_profile_pic_alert(content, username="TPH ProfilePicBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["BAD_PROFILE_PIC_ALERT"],
        content,
        username,
    )


def dispatch_email_alert(content, username="TPH EmailBot"):
    # This goes to bot-spam and is expected to be handled by the Discord bot.
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["BOT_SPAM"],
        content,
        username,
    )


def dispatch_email_response_alert(content, username="TPH EmailBot"):
    # This goes to bot-spam and is expected to be handled by the Discord bot.
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["BOT_SPAM"],
        content,
        username,
    )


def dispatch_hint_alert(content, username="TPH HintBot"):
    # This goes to bot-spam and is expected to be handled by the Discord bot.
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["BOT_SPAM"],
        content,
        username,
    )


def dispatch_hint_response_alert(content, username="TPH HintBot"):
    # This goes to bot-spam and is expected to be handled by the Discord bot.
    dispatch_discord_alert(
        # DISCORD_WEBHOOKS["HINT_RESPONSE_ALERT"],
        DISCORD_WEBHOOKS["BOT_SPAM"],
        content,
        username,
    )


def dispatch_bot_alert(content, username="TPH Bot Relayer"):
    """For messages where Django needs to send info to a Discord bot."""
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["BOT_SPAM"],
        content,
        username,
    )


def dispatch_extra_guess_alert(content, username="TPH MoreGuessBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["MORE_GUESS_ALERT"],
        content,
        username,
    )


def dispatch_spoiler_alert(content, username="TPH SpoilerBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["SPOILER_ALERT"],
        content,
        username,
    )


puzzle_logger = logging.getLogger("puzzles.puzzle")


def log_puzzle_info(puzzle, team, content):
    puzzle_logger.info("<{}> ({}) {}".format(puzzle, team, content))


request_logger = logging.getLogger("puzzles.request")


def log_request_middleware(get_response):
    def middleware(request):
        request_logger.info("{} {}".format(request.get_full_path(), request.user))
        return get_response(request)

    return middleware


# NOTE: we don't have a request available, so this doesn't render with a
# RequestContext, so the magic from our context processor is not available! (We
# maybe could sometimes provide a request, but I don't want to add that
# coupling right now.)
def send_mail_wrapper(subject, template, context, recipients):
    if not recipients:
        return
    # Manually plug in some template variables we know we want
    context["hunt_title"] = HUNT_TITLE
    context["hunt_organizers"] = HUNT_ORGANIZERS
    plaintxt = render_to_string(template + ".txt", context)
    html = render_to_string(template + ".html", context)
    return send_mail_implementation(subject, plaintxt, html, context, recipients)


def send_mail_implementation(subject, plaintxt, html, context, recipients, bcc=False):
    from puzzles.models import Email

    subject = settings.EMAIL_SUBJECT_PREFIX + subject
    body = plaintxt
    if bcc:
        to = []
        bcc = recipients
    else:
        to = recipients
        bcc = []
    mail = email.message.EmailMessage()
    mail["Subject"] = subject
    mail.set_content(body)
    mail["From"] = f'"{HUNT_TITLE}" <{MESSAGING_SENDER_EMAIL}>'
    mail["To"] = ", ".join(to)
    mail.add_alternative(html, subtype="html")
    mail["Reply-To"] = f'"{HUNT_TITLE}" <{CONTACT_EMAIL}>'
    mail_obj = Email.FromEmailMessage(
        mail,
        bcc_addresses=bcc,
        status=Email.SENDING,
    )
    try:
        mail_obj.save()
    except Exception:
        dispatch_general_alert(
            "Could not send mail <{}> to <{}>:\n{}".format(
                subject, ", ".join(recipients), traceback.format_exc()
            )
        )


def send_mass_mail_implementation(
    subject, plaintxt, html, context, recipients=None, addresses=None, dry_run=True
):
    from puzzles.models import EmailTemplate

    if recipients is None:
        recipients = EmailTemplate.RECIPIENT_BATCH_USERS

    subject = settings.EMAIL_SUBJECT_PREFIX + subject
    from_address = f'"{HUNT_TITLE}" <info@{settings.EMAIL_USER_DOMAIN}>'
    status = EmailTemplate.DRAFT if dry_run else EmailTemplate.SCHEDULED
    kwargs = {}
    if addresses is not None:
        kwargs["addresses"] = addresses
    template_obj = EmailTemplate(
        subject=subject,
        text_content=plaintxt,
        html_content=html,
        from_address=from_address,
        scheduled_datetime=timezone.now(),
        status=status,
        recipients=recipients,
        **kwargs,
    )

    if not dry_run:
        try:
            template_obj.save()
        except:
            dispatch_general_alert(
                "Could not schedule mail <{}>:\n{}".format(
                    subject, traceback.format_exc()
                )
            )
            raise
    return template_obj


class EmptyEmbed:
    def to_dict(self):
        return {}
