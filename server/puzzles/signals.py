from functools import lru_cache

import spoilr.core.models
import spoilr.email.models
import spoilr.hints.models
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from pwreset.models import Token
from spoilr.core.api.events import HuntEvent, register
from spoilr.core.api.hunt import is_site_launched, release_interaction
from spoilr.registration.models import IndividualRegistrationInfo
from spoilr.utils import generate_url

from puzzles.assets import get_hashed_url
from puzzles.celery import celery_app
from puzzles.consumers import ClientConsumer
from puzzles.messaging import (
    dispatch_bot_alert,
    dispatch_email_alert,
    dispatch_email_response_alert,
    dispatch_extra_guess_alert,
    dispatch_feedback_alert,
    dispatch_free_answer_alert,
    dispatch_general_alert,
    dispatch_hint_alert,
    dispatch_hint_response_alert,
    dispatch_interaction_alert,
    dispatch_interaction_response_alert,
    dispatch_submission_alert,
    send_mail_wrapper,
)
from puzzles.models import (
    CustomPuzzleSubmission,
    ExtraGuessGrant,
    Feedback,
    PuzzleSubmission,
    Team,
    build_guess_data,
    handle_victory,
)
from puzzles.models.story import StoryCardAccess, StoryState
from puzzles.rounds.utils import get_round_emoji, get_solve_sound
from puzzles.utils import get_encryption_keys

# Django signals that trigger on model changes


@receiver(post_save, sender=Token)
def send_password_reset_email(sender, instance: Token, created: bool, **kwargs):
    if created:
        team = instance.user.team
        if team:
            email = team.team_email
        elif hasattr(instance.user, "individualregistrationinfo"):
            email = instance.user.individualregistrationinfo.contact_email
        else:
            return

        url = generate_url(
            "prehunt",
            "/reset_password",
            {"token": instance.token, "username": instance.user.username},
        )
        send_mail_wrapper(
            "Password reset requested",
            "password_reset_email",
            {"name": instance.user.username, "reset_link": url},
            email,
            is_prehunt=True,
        )


# Signals for Email and Hint infrastructure


@receiver(post_save, sender=spoilr.email.models.EmailTemplate)
def celery_queue_email_template(sender, instance, **kwargs):
    update_fields = kwargs["update_fields"]
    if (
        update_fields is None
        or "status" in update_fields
        or "scheduled_datetime" in update_fields
    ) and instance.status == instance.SCHEDULED:
        pk = instance.pk
        scheduled_datetime = instance.scheduled_datetime
        transaction.on_commit(
            lambda: celery_app.send_task(
                "puzzles.emailing.task_send_email_template",
                args=[pk],
                eta=scheduled_datetime,
            )
        )


# NB: Django signals are not inherited automatically
@receiver(post_save, sender=spoilr.email.models.Email)
def celery_queue_email(sender, instance, **kwargs):
    update_fields = kwargs["update_fields"]
    if update_fields is None or "status" in update_fields:
        if instance.status == instance.SENDING:
            pk = instance.pk
            scheduled_datetime = instance.scheduled_datetime
            # Templated emails are sent synchronously
            if instance.template is None:
                transaction.on_commit(
                    lambda: celery_app.send_task(
                        "puzzles.emailing.task_send_email",
                        args=[pk],
                        eta=scheduled_datetime,
                    )
                )


# Signals for informational discord notifications


@receiver(post_save, sender=Team)
def notify_on_team_creation(sender, instance, created, **kwargs):
    if created:

        def notify():
            # NB: important to check for teamregistrationinfo AFTER the commit,
            #     ie after all the saves have finished resolving
            if hasattr(instance, "teamregistrationinfo"):
                dispatch_general_alert(f"Team created: {instance.name}")
                send_mail_wrapper(
                    f"You’re registered for {settings.HUNT_NAME}!",
                    "registration_email",
                    {
                        "username": instance.username,
                        "name": instance.name,
                        "team_link": generate_url("prehunt", "register-team"),
                    },
                    [instance.teamregistrationinfo.contact_email],
                    is_prehunt=True,
                )

        transaction.on_commit(notify)


@receiver(post_save, sender=IndividualRegistrationInfo)
def notify_on_individual_registration(sender, instance, created, **kwargs):
    if created:

        def notify():
            dispatch_general_alert(f"Individual registered: {instance.contact_email}")
            send_mail_wrapper(
                f"Thanks for your interest joining {settings.HUNT_NAME}!",
                "registration_email_individual",
                {
                    "username": instance.user.username,
                    "user_link": generate_url("prehunt", "register-individual"),
                },
                [instance.contact_email],
                is_prehunt=True,
            )

        transaction.on_commit(notify)


@receiver(post_save, sender=spoilr.email.models.Email)
def notify_on_new_email(sender, instance, created, **kwargs):
    # Only send the alert for emails that may need a response.
    if created and not settings.IS_TEST and instance.requires_response:
        dispatch_email_alert(instance.created_discord_message())


@receiver(post_save, sender=PuzzleSubmission)
def notify_on_answer_submission(sender, instance, created, **kwargs):
    from puzzles.views.story import story_card_data

    if created:
        now = timezone.localtime()
        guess_data = build_guess_data(instance)
        guess_data["puzzle"] = instance.puzzle.slug
        partial = guess_data.pop("partial")
        puzzle = instance.puzzle.puzzle
        team = instance.team.team

        def format_time_ago(timestamp):
            if not timestamp:
                return ""
            diff = now - timestamp
            parts = ["", "", "", ""]
            if diff.days > 0:
                parts[0] = "%dd" % diff.days
            seconds = diff.seconds
            parts[3] = "%02ds" % (seconds % 60)
            minutes = seconds // 60
            if minutes:
                parts[2] = "%02dm" % (minutes % 60)
                hours = minutes // 60
                if hours:
                    parts[1] = "%dh" % hours
            return " {} ago".format("".join(parts))

        hints = list(
            spoilr.hints.models.Hint.objects.filter(
                team=team, puzzle=puzzle, is_request=True
            ).select_related("response")
        )
        hint_line = ""
        if hints:
            hint_line = "\nHints:" + ",".join(
                "%s (%s%s)"
                % (
                    format_time_ago(hint.timestamp),
                    hint.status,
                    format_time_ago(
                        hint.response.timestamp if hint.response is not None else None
                    ),
                )
                for hint in hints
            )
        if instance.used_free_answer:
            dispatch_free_answer_alert(
                ":question: {} Team **{}** used a free answer on {}!{}".format(
                    puzzle.emoji,
                    team,
                    puzzle,
                    hint_line,
                )
            )
        else:
            sigil = ":x:"
            if instance.correct:
                sigil = {
                    1: ":first_place:",
                    2: ":second_place:",
                    3: ":third_place:",
                }.get(
                    PuzzleSubmission.objects.filter(
                        puzzle=puzzle,
                        correct=True,
                        used_free_answer=False,
                        team__team__is_hidden=False,
                    ).count(),
                    ":white_check_mark:",
                )
            # Determine the message reply.
            # Since we need to filter on the normalized_answer which is a Python
            # property, we can't use Django filters for that field. Loading all
            # the messages should be fine though, there are very few for each
            # puzzle.
            discord_message = "Correct!" if instance.correct else "Incorrect!!"
            discord_username = "WinBot" if instance.correct else "FailBot"
            if partial:
                discord_message = guess_data["response"]
                # If we have custom messages for success, do not change to
                # right arrow for correct guesses.
                if not instance.correct:
                    discord_username = "KeepGoingBot"
                    sigil = ":arrow_right:"
            if not team.is_hidden:
                multi = "\n" in instance.answer
                dispatch_submission_alert(
                    f"{sigil} {puzzle.emoji} Team **{team}** submitted "
                    f"""{"```" + chr(10) if multi else "`"}{instance.answer}{"```" if multi else "`"} """
                    f"for {puzzle}: {discord_message}{hint_line}",
                    username=discord_username,
                )

        is_correct = instance.correct
        websocket_data = get_puzzle_websocket_data(
            puzzle,
            team,
            notification_type="solve" if is_correct else None,
        )
        websocket_data["guess"] = guess_data

        if is_correct:
            story_card = puzzle.story_cards.first()
            if story_card:
                # Unlock story card
                StoryCardAccess.objects.get_or_create(team=team, story_card=story_card)
                websocket_data["storycard"] = story_card_data(story_card)
                websocket_data["cryptKeys"] = get_encryption_keys([story_card.slug])

        channels_group = ClientConsumer.get_team_group(id=instance.team_id)
        ClientConsumer.send_event(channels_group, "submission", websocket_data)

        if instance.correct:
            on_puzzle_solve(puzzle, instance)


def on_puzzle_solve(puzzle, submission):
    # Send Discord alert and victory email
    handle_victory(submission)

    # Clean up obsolete hints
    obsolete_hints = spoilr.hints.models.Hint.objects.filter(
        team=submission.team,
        puzzle=puzzle,
        status=spoilr.hints.models.Hint.NO_RESPONSE,
    )
    # Trigger postsave
    for hint in obsolete_hints:
        hint.status = spoilr.hints.models.Hint.OBSOLETE
        hint.save()
    spoilr.hints.models.Hint.clean_up_tasks(obsolete_hints)


@receiver(post_save, sender=CustomPuzzleSubmission)
def notify_on_custom_puzzle_submission(sender, instance, created, **kwargs):
    if created:
        pass
        # FIXME: can run custom logic on puzzle submission. Also consider
        # using Mixins a la MH 2022
        # if instance.puzzle and instance.puzzle.slug == "sample":
        #   pass


@receiver(post_save, sender=spoilr.hints.models.Hint)
def notify_on_new_hint(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.is_request:
        # Only send alert for hints requested by teams, not responses.
        dispatch_hint_alert(instance.created_discord_message())
    elif instance.status == spoilr.hints.models.Hint.ANSWERED:
        # Hint was a response from HQ
        websocket_data = get_puzzle_websocket_data(
            instance.puzzle.puzzle, instance.team, notification_type="hint"
        )
        channels_group = ClientConsumer.get_team_group(id=instance.team_id)
        ClientConsumer.send_event(channels_group, "hint", websocket_data)


@receiver(post_save, sender=ExtraGuessGrant)
def notify_on_extra_guess_grant_update(sender, instance, **kwargs):
    from puzzles.views.puzzles import get_ratelimit

    websocket_data = get_puzzle_websocket_data(instance.puzzle, instance.team)
    channels_group = ClientConsumer.get_puzzle_group(
        id=instance.team_id, slug=instance.puzzle.slug
    )
    ClientConsumer.send_event(channels_group, "submission", websocket_data)

    # Handle status = GRANTED inside API call.
    if instance.status == ExtraGuessGrant.NO_RESPONSE:
        dispatch_extra_guess_alert(instance.requested_discord_message())


@receiver(post_save, sender=spoilr.core.models.InteractionAccess)
def notify_on_interactionaccess_update(sender, instance, **kwargs):
    if not instance.accomplished:
        # Send a Discord alert
        dispatch_interaction_alert(instance.created_discord_message())


@receiver(post_save, sender=StoryCardAccess)
def notify_on_storycardaccess_update(sender, instance, created, **kwargs):
    if not created:
        return

    story_card = instance.story_card
    team = instance.team
    data = {
        # NB: Reuse the puzzle data format for notifications even though it's a storycard.
        "puzzle": {
            "slug": story_card.slug,
            "name": story_card.slug,
            "url": story_card.url,
            "act": story_card.act,
        },
        "title": "Story Update",
    }
    message, icon, _, _ = get_notification_message(
        team, story=story_card, notification_type="unlock"
    )
    # Suppress notifications for unlocks without a message
    if not message:
        return

    data["message"] = message
    data["icon"] = icon
    channels_group = ClientConsumer.get_team_group(id=team.id)
    ClientConsumer.send_event(channels_group, "unlock", data)


@receiver(post_save, sender=Feedback)
def notify_on_new_feedback(sender, instance, created, **kwargs):
    if created:
        dispatch_feedback_alert(
            f"Feedback from {instance.team} on {instance.puzzle}: {instance.comments}"
        )


def should_notify(notification_type, puzzle=None, round=None, story=None) -> bool:
    if notification_type == "hint":
        # Always notify for hint responses
        return True

    # No notifications before hunt begins
    if not is_site_launched():
        return False

    # Don't show notification for events
    blocklist = set()
    story_blocklist = set()
    round_blocklist = set()

    if notification_type == "unlock":
        round_blocklist.add("events")

    if puzzle:
        return puzzle.slug not in blocklist and puzzle.round.slug not in round_blocklist
    elif round:
        return round.slug not in round_blocklist
    else:  # story
        return story.slug not in story_blocklist


def get_notification_message(
    team, notification_type=None, puzzle=None, round=None, story=None
):
    if not should_notify(notification_type, puzzle, round, story):
        return None, None, None, None

    if story:
        puzzle = story.puzzle
    puzzle_round = round or (puzzle.round if puzzle else None)
    round_emoji = get_round_emoji(puzzle_round) if puzzle_round else ""
    sound = get_solve_sound(puzzle_round) if puzzle_round else None
    icon = None

    if notification_type == "hint":
        return (
            f"{round_emoji} Your hint for {puzzle.name} was answered!",
            None,
            None,
            None,
        )

    # Special case: storycard unlocks, round unlocks, meta unlocks, and meta solves
    if story or round or (puzzle and puzzle.is_meta):
        if story:
            key = "notif-story-unlock"
            title = "Story Update"
            icon = get_hashed_url(f"Story/Notifications/{story.slug}.png")
        elif round:
            key = "notif-round-unlock"
            title = "Round Unlocked"
        else:
            key = f"notif-meta-{notification_type}"
            title = "Meta Solved" if notification_type == "solve" else "Meta Unlocked"
        # FIXME: populate notifications format string basend on hunt logic here
        round_name = ""
        if puzzle_round:
            round_name = (puzzle_round.superround or puzzle_round).name
        message = (
            "{ROUND_EMOJI} A meta puzzle, {PUZZLE_NAME}, has unlocked in {ROUND_NAME}!"
        ).format(
            PUZZLE_NAME=puzzle.name if puzzle else None,
            ROUND_NAME=round_name,
            ROUND_EMOJI=round_emoji,
        )
        return message, icon, title, (sound if notification_type == "solve" else None)

    if notification_type == "solve":
        return f"{round_emoji} {puzzle.name} was solved! ✨", None, None, sound

    if notification_type == "unlock":
        message = f"{round_emoji} {puzzle.name} was unlocked!"
        return message, None, None, None

    raise AssertionError(f"Invalid notification type: {notification_type}")


def get_puzzle_websocket_data(puzzle, team, notification_type=None):
    from puzzles.views.puzzles import get_ratelimit

    ratelimit_data = get_ratelimit(puzzle, team)
    story_state = StoryState.get_state(team)
    url = (
        puzzle.get_hints_url(story_state)
        if notification_type == "hint"
        else puzzle.get_url(story_state)
    )
    data = {
        "puzzle": {
            "slug": puzzle.slug,
            "name": puzzle.name,
            "url": url,
            "act": puzzle.round.act,
        },
        "rateLimit": ratelimit_data,
    }
    if notification_type:
        message, icon, title, sound = get_notification_message(
            team, puzzle=puzzle, notification_type=notification_type
        )
        if message:
            data["message"] = message
            if icon:
                data["icon"] = icon
            if title:
                data["title"] = title
            if sound:
                data["sound"] = sound

    return data


# Spoilr events that trigger on custom logic


def _on_puzzle_unlock(*, team, puzzle, **kwargs):
    websocket_data = get_puzzle_websocket_data(
        puzzle.puzzle, team, notification_type="unlock"
    )
    # Suppress notifications for unlocks without a message
    if not websocket_data.get("message"):
        return

    channels_group = ClientConsumer.get_team_group(id=team.id)
    ClientConsumer.send_event(channels_group, "unlock", websocket_data)


def _on_round_unlock(*, team, round, **kwargs):
    data = {
        # NB: Reuse the puzzle data format for notifications even though it's a round.
        "puzzle": {
            "slug": round.slug,
            "name": round.name,
            "url": round.url,
            "act": round.act,
        },
    }
    message, _, title, _ = get_notification_message(
        team, round=round, notification_type="unlock"
    )
    # Suppress notifications for unlocks without a message
    if not message:
        return

    data["message"] = message
    data["title"] = title
    channels_group = ClientConsumer.get_team_group(id=team.id)
    ClientConsumer.send_event(channels_group, "unlock", data)


def _on_hint_resolved(**kwargs):
    response = kwargs["hint_response"]
    if response:
        dispatch_hint_response_alert(
            spoilr.hints.models.Hint.responded_discord_message(
                kwargs["hint_request"], response
            )
        )


def _on_email_reply(**kwargs):
    dispatch_email_response_alert(
        spoilr.email.models.Email.responded_discord_message(
            kwargs["email_in_reply_to"], kwargs.get("email_reply", None)
        )
    )


def _on_interaction_acomplished(**kwargs):
    dispatch_interaction_response_alert(
        spoilr.core.models.InteractionAccess.responded_discord_message(
            kwargs["interaction_access"]
        )
    )


register(HuntEvent.PUZZLE_RELEASED, _on_puzzle_unlock)
register(HuntEvent.METAPUZZLE_RELEASED, _on_puzzle_unlock)
register(HuntEvent.ROUND_RELEASED, _on_round_unlock)
register(HuntEvent.HINT_RESOLVED, _on_hint_resolved)
register(HuntEvent.EMAIL_REPLIED, _on_email_reply)
register(HuntEvent.INTERACTION_ACCOMPLISHED, _on_interaction_acomplished)
