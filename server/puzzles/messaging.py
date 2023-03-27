import email
import logging
import time
import traceback
from collections import defaultdict

import requests
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from tph.constants import IS_PYODIDE
from tph.utils import get_task_logger

from puzzles.celery import celery_app
from puzzles.hunt_config import (
    HUNT_CONTACT_EMAIL,
    HUNT_ORGANIZERS,
    HUNT_TITLE,
    MESSAGING_SENDER_EMAIL,
)

if IS_PYODIDE:
    DISCORD_WEBHOOKS = defaultdict(str)
else:
    from tph.secrets import DISCORD_WEBHOOKS


task_logger = get_task_logger(__name__)  # for Celery tasks


def dispatch_discord_alert(webhook, content, username="Django"):
    dispatch_discord_alert_internal.delay(webhook, content, username)


@celery_app.task
def dispatch_discord_alert_internal(webhook, content, username="Django"):
    content = f"<t:{int(time.time())}:t> {content}"
    if len(content) >= 2000:
        content = content[:1996] + "..."
    if settings.IS_TEST:
        task_logger.info("Discord alert:\n" + content)
    if not settings.SEND_DISCORD_ALERTS:
        return
    if settings.SERVER_ENVIRONMENT != "prod":
        # Override with staging webhook.
        webhook = DISCORD_WEBHOOKS["STAGING"]

    if webhook == "FIXME":
        task_logger.warning("Invalid webhook (FIXME)")
        return  # TODO: fix this

    try:
        requests.post(
            f"https://discord.com/api/webhooks/{webhook}",
            data={"username": username, "content": content},
        )
    except:
        task_logger.error(
            "Failed to post to discord webhook with username %s, content: %s",
            username,
            content,
        )


def dispatch_general_alert(content, username="AlertBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["ALERT_ALERT"],
        content,
        username,
    )


def dispatch_submission_alert(content, username="SubmissionBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["SUBMISSION_ALERT"],
        content,
        username,
    )


def dispatch_free_answer_alert(content, username="HelpBot"):
    dispatch_discord_alert("FIXME", content, username)


def dispatch_victory_alert(content, username="CongratBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["CONGRAT_ALERT"],
        content,
        username,
    )


def dispatch_profile_pic_alert(content, username="ProfilePicBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["PROFILE_PIC_ALERT"],
        content,
        username,
    )


def dispatch_bad_profile_pic_alert(content, username="ProfilePicBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["BAD_PROFILE_PIC_ALERT"],
        content,
        username,
    )


def dispatch_interaction_alert(content, username="InteractionBot"):
    # This goes to bot-spam and is expected to be handled by the Discord bot.
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["BOT_SPAM"],
        content,
        username,
    )


def dispatch_event_used_alert(content, username="EventRewardBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["EVENT_ALERT"],
        content,
        username,
    )


def dispatch_feedback_alert(content, username="FeedbackBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["FEEDBACK_ALERT"],
        content,
        username,
    )


def dispatch_email_alert(content, username="EmailBot"):
    # This goes to bot-spam and is expected to be handled by the Discord bot.
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["BOT_SPAM"],
        content,
        username,
    )


def dispatch_email_response_alert(content, username="EmailBot"):
    # This goes to bot-spam and is expected to be handled by the Discord bot.
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["BOT_SPAM"],
        content,
        username,
    )


def dispatch_interaction_response_alert(content, username="InteractionBot"):
    # This goes to bot-spam and is expected to be handled by the Discord bot.
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["BOT_SPAM"],
        content,
        username,
    )


def dispatch_hint_alert(content, username="HintBot"):
    # This goes to bot-spam and is expected to be handled by the Discord bot.
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["BOT_SPAM"],
        content,
        username,
    )


def dispatch_hint_response_alert(content, username="HintBot"):
    # This goes to bot-spam and is expected to be handled by the Discord bot.
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["BOT_SPAM"],
        content,
        username,
    )


def dispatch_bot_alert(content, username="Bot Relayer"):
    """For messages where Django needs to send info to a Discord bot."""
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["BOT_SPAM"],
        content,
        username,
    )


def dispatch_extra_guess_alert(content, username="MoreGuessBot"):
    dispatch_discord_alert(
        DISCORD_WEBHOOKS["MORE_GUESS_ALERT"],
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
def send_mail_wrapper(
    subject, template, context, recipients, *, is_prehunt, sent_datetime=None
):
    """Send emails for a small list of email addresses via template in repo."""
    if not recipients:
        return
    # Allow single recipient
    if isinstance(recipients, str):
        recipients = [recipients]

    # Manually plug in some template variables we know we want
    context["hunt_title"] = HUNT_TITLE
    context["hunt_organizers"] = HUNT_ORGANIZERS
    plaintxt = render_to_string(template + ".txt", context)
    html = render_to_string(template + ".html", context)
    return send_mail_implementation(
        subject,
        plaintxt,
        html,
        recipients,
        is_prehunt=is_prehunt,
        sent_datetime=sent_datetime,
    )


# This is identical to send_mail_wrapper, except instead of rendering a template
# we take the plaintext and html directly.
def send_mail_text_wrapper(subject, plaintxt, html, recipients, *, is_prehunt):
    """Send emails for a small list of email addresses via given text."""
    if not recipients:
        return
    # Allow single recipient
    if isinstance(recipients, str):
        recipients = [recipients]

    # Manually plug in some template variables we know we want
    return send_mail_implementation(
        subject, plaintxt, html, recipients, is_prehunt=is_prehunt
    )


def send_mail_canned_email(slug, recipients, bcc=False, **kwargs):
    from spoilr.email.models import CannedEmail, Email

    if not recipients:
        return
    # Allow single recipient
    if isinstance(recipients, str):
        recipients = [recipients]

    if bcc:
        to = []
        bcc = recipients
    else:
        to = recipients
        bcc = []

    contact_email = HUNT_CONTACT_EMAIL
    reply_to = f'"{HUNT_TITLE}" <{contact_email}>'

    canned_email = CannedEmail.objects.get(slug=slug)
    mail_obj = Email.from_canned_email(
        canned_email,
        from_domain=settings.EMAIL_USER_DOMAIN,
        to_addresses=to,
        bcc_addresses=bcc,
        reply_to=reply_to,
        is_from_us=True,
        is_authenticated=True,
        created_via_webapp=False,
        status=Email.SENDING,
        **kwargs,
    )
    try:
        mail_obj.save()
        return mail_obj
    except Exception:
        dispatch_general_alert(
            "Could not send mail <{}> to <{}>:\n{}".format(
                canned_email.subject, ", ".join(recipients), traceback.format_exc()
            )
        )


def send_mail_implementation(
    subject,
    plaintxt,
    html,
    recipients,
    bcc=False,
    *,
    is_prehunt,
    sent_datetime=None,
):
    from spoilr.email.models import Email

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
    contact_email = HUNT_CONTACT_EMAIL
    mail["Reply-To"] = f'"{HUNT_TITLE}" <{contact_email}>'
    mail_obj = Email.FromEmailMessage(
        mail,
        bcc_addresses=bcc,
        status=Email.SENDING,
        sent_datetime=sent_datetime,
    )
    try:
        mail_obj.save()
        return mail_obj
    except Exception:
        dispatch_general_alert(
            "Could not send mail <{}> to <{}>:\n{}".format(
                subject, ", ".join(recipients), traceback.format_exc()
            )
        )


def send_mass_mail_implementation(
    subject, plaintxt, html, context, recipients=None, addresses=None, dry_run=True
):
    """Send emails to all teams, or a large list of email addresses."""
    from spoilr.email.models import EmailTemplate

    if recipients is None:
        recipients = EmailTemplate.RECIPIENT_TEAMS

    subject = settings.EMAIL_SUBJECT_PREFIX + subject
    from_address = f'"{HUNT_ORGANIZERS}" <info@{settings.EMAIL_USER_DOMAIN}>'
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
