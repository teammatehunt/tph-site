import base64
import csv
import datetime
import os
import string
from collections import Counter, defaultdict
from typing import Callable, Mapping
from urllib.parse import unquote

import django.template
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import (
    Avg,
    Case,
    Count,
    F,
    Max,
    Min,
    OuterRef,
    Q,
    Subquery,
    Sum,
    When,
    Window,
)
from django.db.models.functions import FirstValue, LastValue
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template import TemplateDoesNotExist
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.static import serve

from puzzles.celery import celery_app
from puzzles.forms import (
    AnswerEmailForm,
    AnswerHintForm,
    ExtraGuessGrantForm,
    RequestHintForm,
    SubmitAnswerForm,
)
from puzzles.hunt_config import (
    ADMIN_TEAM_NAME,
    GUESSES_PER_PERIOD,
    HUNT_END_TIME,
    HUNT_START_TIME,
    INTRO_META_SLUGS,
    INTRO_ROUND,
    META_META_SLUG,
    SECONDS_PER_PERIOD,
)
from puzzles.messaging import (
    dispatch_email_response_alert,
    dispatch_extra_guess_alert,
    dispatch_hint_response_alert,
    send_mail_wrapper,
)
from puzzles.models import (
    AnswerSubmission,
    Email,
    Errata,
    ExtraGuessGrant,
    Hint,
    Puzzle,
    Round,
    StoryCardUnlock,
    Team,
    build_guess_data,
)
from puzzles.puzzlehandlers import RateLimitException, error_ratelimit, puzzle_key
from puzzles.views.auth import restrict_access, validate_puzzle

# A map from slug to function getting data to pass on page load
# Function should be (request, team) => dict (or other json convertible object)
PUZZLE_SPECIFIC_PRIVATE_INITIAL_DATA: Mapping[str, Callable] = {
    # TODO: Add mappings here.
    # "sample": sample.get_initial_data,
}


@require_GET
def puzzles(request):
    """Fetches puzzle data to show on the puzzle list or map page."""
    if not request.context.hunt_has_started:
        return JsonResponse({"puzzles": []})

    team = request.context.team

    solved = {}
    hints = {}
    if team is not None:
        solved = team.solves
        hints = Counter(team.hint_set.values_list("puzzle_id", flat=True))

    unlocks = request.context.unlocks
    for data in unlocks["puzzles"]:
        puzzle_id = data["puzzle"].id
        if puzzle_id in solved:
            data["answer"] = solved[puzzle_id].normalized_answer
        if puzzle_id in hints:
            data["hints"] = hints[puzzle_id]

    puzzles_by_round = defaultdict(list)

    def meta_order(puzzle_slug):
        """Special ordering just for metas."""
        if puzzle_slug in INTRO_META_SLUGS:
            return 0 if puzzle_slug == INTRO_META_SLUGS[0] else 1
        return 2

    def sort_key(unlock):
        # Group by round, then by is_meta (meta = False first), then by deep,
        # then by alpha. This is the order we list them in. Use the puzzle
        # name, after stripping characters to be alphanumeric.
        puzzle = unlock["puzzle"]
        alphanumeric_name = "".join(
            c for c in puzzle.name.lower() if c in string.ascii_lowercase + "0123456789"
        )
        return (
            puzzle.round,
            puzzle.is_meta,
            puzzle.deep,
            meta_order(puzzle.slug),
            alphanumeric_name,
        )

    puzzle_unlocks = sorted(unlocks["puzzles"], key=sort_key)
    for unlock in puzzle_unlocks:
        puzzle = unlock["puzzle"]
        dim = Round.from_round(puzzle.round).value
        puzzles_by_round[dim].append(
            {
                "name": puzzle.name,
                "slug": puzzle.slug,
                "isMeta": puzzle.is_meta,
                "iconURLs": get_icons(request, puzzle, unlock),
                "iconSize": puzzle.icon_size,
                "position": [puzzle.icon_x, puzzle.icon_y],
                "textPosition": [puzzle.text_x, puzzle.text_y],
                "answer": unlock.get("answer"),
                "round": dim,
            }
        )
        # Special hardcoding for intro metas.
        if puzzle.slug in INTRO_META_SLUGS:
            puzzles_by_round[dim][-1]["mainRoundPosition"] = [475, 440]

    # If no puzzles have been unlocked, return 404.
    if not puzzles_by_round:
        return JsonResponse({}, status=404)

    response = {
        "puzzles": puzzles_by_round,
    }

    return JsonResponse(response)


def get_icons(request, puzzle, unlock):
    # Build a dict of what properties the puzzle has, then use that to filter.
    # Return a list of icons we want to retrieve.
    # Not all puzzles are guaranteed to have puzzle.solved_icon.name defined.
    solved = "answer" in unlock
    round_ = Round.from_round(puzzle.round)
    # A permission dict we filter later.
    properties = {
        "solved": solved,
        "intro": round_ == Round.INTRO,
        "main_unlocked": request.context.is_main_round_unlocked,
        "is_intro_meta": puzzle.slug in INTRO_META_SLUGS,
    }
    icons = {}
    if request.context.hunt_is_over and request.context.team is None:
        # Retrieve all icons.
        icons["solved"] = puzzle.solved_icon.name
        icons["bgIcon"] = puzzle.bg_icon.name
        icons["unsolved"] = puzzle.unsolved_icon.name
    elif properties["solved"]:
        icons["solved"] = puzzle.solved_icon.name
        icons["bgIcon"] = puzzle.bg_icon.name
    else:
        icons["unsolved"] = puzzle.unsolved_icon.name
    # Only include icons with URLs defined in fixtures.
    icons = {
        k: os.path.join(settings.MEDIA_URL, name) for k, name in icons.items() if name
    }
    return icons


def hint_data(puzzle, team):
    threads = defaultdict(lambda: {"hints": []})  # keyed by original_request_id
    for hint in Hint.objects.filter(team=team, puzzle=puzzle).order_by(
        "submitted_datetime"
    ):
        if hint.is_request and hint.root_ancestor_request_id is None:
            threads[hint.original_request_id]["threadId"] = hint.pk
            threads[hint.original_request_id]["status"] = hint.status
        threads[hint.original_request_id]["hints"].append(
            {
                "isRequest": hint.is_request,
                "requiresResponse": hint.requires_response,
                "content": hint.text_content,
                "submitTime": hint.submitted_datetime,
            }
        )
    return list(threads.values())


def get_puzzle_data(request, puzzle, team):
    """Helper method to retrieve puzzle specific data."""
    solution_link_visible = request.context.hunt_is_over or request.context.is_superuser

    intro_hints_remaining = team.num_intro_hints_remaining if team else 0
    nonintro_hints_remaining = team.num_nonintro_hints_remaining if team else 0
    hints_remaining = team.num_hints_remaining if team else 0
    errata = [
        err.render_data()
        for err in Errata.objects.filter(puzzle=puzzle).order_by("creation_time")
    ]
    story_card = puzzle.story_cards.first()

    data = {
        "name": puzzle.name,
        "slug": puzzle.slug,
        "round": puzzle.round,
        "isIntro": puzzle.round == INTRO_ROUND,
        "isSolved": request.context.puzzle_answer,
        "guesses": [
            build_guess_data(submission)
            for submission in team.puzzle_submissions(puzzle)
        ]
        if team
        else [],
        "solutionLinkVisible": solution_link_visible,
        "rateLimit": get_ratelimit(puzzle, team) if team else None,
        "canViewHints": team
        and not request.context.hunt_is_closed
        and (team.num_hints_total > 0 or team.num_free_answers_total > 0),
        "canAskForHints": team
        and not request.context.hunt_is_over
        and (team.num_hints_remaining > 0 or team.num_free_answers_remaining > 0),
        "hintsRemaining": hints_remaining,
        "nonIntroHintsRemaining": nonintro_hints_remaining,
        "introHintsRemaining": intro_hints_remaining,
        "hintThreads": hint_data(puzzle, team),
        "errata": errata,
        "endcapSlug": story_card.slug if story_card else None,
    }
    if team and team.is_prerelease_testsolver:
        data["puzzleUrl"] = puzzle.testsolve_url

    if request.context.hunt_is_over:
        data["answerB64Encoded"] = base64.b64encode(
            puzzle.normalized_answer.encode("utf-8")
        ).decode("utf-8")
        data["partialMessagesB64Encoded"] = [
            [
                base64.b64encode(message.semicleaned_guess.encode("utf-8")).decode(
                    "utf-8"
                ),
                base64.b64encode(message.response.encode("utf-8")).decode("utf-8"),
            ]
            for message in puzzle.puzzlemessage_set.all()
        ]

    if team and puzzle.slug in PUZZLE_SPECIFIC_PRIVATE_INITIAL_DATA:
        data["private"] = PUZZLE_SPECIFIC_PRIVATE_INITIAL_DATA[puzzle.slug](
            request, team
        )

    return data


@validate_puzzle(require_team=True, allow_after_hunt=True)
def puzzle_data(request):
    puzzle = request.context.puzzle
    team = request.context.team
    return JsonResponse(get_puzzle_data(request, puzzle, team))


@require_POST
@validate_puzzle(require_team=True)
def request_more_guesses(request):
    puzzle = request.context.puzzle
    team = request.context.team
    guess_grant, created = ExtraGuessGrant.objects.get_or_create(
        puzzle=puzzle, team=team
    )
    if not created:
        # If they requested more guesses before, then the status might be
        # GRANTED, so set to NO_RESPONSE to indicate we need to check again.
        guess_grant.status = ExtraGuessGrant.NO_RESPONSE
        guess_grant.save()
    return JsonResponse(
        {
            "granted": False,
        }
    )


def get_ratelimit(puzzle, team):
    curr_time = timezone.now()
    guess_period = datetime.timedelta(seconds=SECONDS_PER_PERIOD)
    guesses_made = AnswerSubmission.objects.filter(
        team=team, puzzle=puzzle, submitted_datetime__gte=curr_time - guess_period
    )
    guess_count = guesses_made.count()
    extra_guesses = 0
    grant_under_review = False
    for grant in ExtraGuessGrant.objects.filter(team=team, puzzle=puzzle):
        if grant.status == ExtraGuessGrant.GRANTED:
            extra_guesses += grant.extra_guesses
        elif grant.status == ExtraGuessGrant.NO_RESPONSE:
            grant_under_review = True
    should_limit = guess_count >= (GUESSES_PER_PERIOD + extra_guesses)
    data = {
        "guessCount": guess_count,
        "shouldLimit": should_limit,
        "guessesMade": [
            g.submitted_answer for g in guesses_made.order_by("submitted_datetime")
        ],
        # diff can be negative if guess grant is revoked.
        "guessesLeft": max(0, (GUESSES_PER_PERIOD + extra_guesses) - guess_count),
        "grantUnderReview": grant_under_review,
    }
    if should_limit:
        earliest_guess = guesses_made.order_by("submitted_datetime").first()
        # Adding a small buffer to the submit time. This should guarantee that
        # by the time countdown expires, the server will be ready to respond to
        # guesses.
        expiration = (
            earliest_guess.submitted_datetime
            + guess_period
            + datetime.timedelta(seconds=1)
        )
        data["secondsToWait"] = (expiration - timezone.now()).total_seconds()
    return data


@require_POST
@validate_puzzle(require_team=True)
@restrict_access(after_hunt_end=False)
def solve(request):
    puzzle = request.context.puzzle
    team = request.context.team
    form = SubmitAnswerForm(request.POST)
    guess_data = None
    ratelimit_data = None
    status = 200

    if request.context.puzzle_answer:
        form.add_error(None, "You\u2019ve already solved this puzzle!")
        status = 400
    elif request.context.guesses_remaining <= 0:
        form.add_error(None, "You have no more guesses for this puzzle!")
        status = 400
    elif "answer" in request.POST:
        normalized_answer = Puzzle.normalize_answer(request.POST.get("answer"))
        tried_before = any(
            normalized_answer == submission.submitted_answer
            for submission in request.context.puzzle_submissions
        )

        if not normalized_answer:
            form.add_error(
                None,
                "All puzzle answers will have "
                "at least one letter A through Z (case does not matter).",
            )
            status = 400
        elif tried_before:
            form.add_error(
                None,
                "You\u2019ve already tried calling in the "
                "answer \u201c%s\u201d for this puzzle." % normalized_answer,
            )
            status = 400
        elif form.is_valid():
            # A real guess! Check the ratelimit first.
            ratelimit_data = get_ratelimit(puzzle, team)
            # If it's fine, make the guess
            if not ratelimit_data["shouldLimit"]:
                guess_data = process_guess(
                    request.context.now, team, puzzle, normalized_answer
                )
                # If it isn't correct, requery rate limit with added guess.
                # Only do this for incorrect guesses, to make sure we do not
                # trigger modal if they solve it with their last guess.
                if not guess_data["isCorrect"]:
                    ratelimit_data = get_ratelimit(puzzle, team)
            # Now check for whether to notify user they're out of guesses.
            if ratelimit_data["shouldLimit"]:
                status = 429
    if guess_data:
        all_guesses = [guess_data]
        form_errors = None
    else:
        all_guesses = []
        form_errors = form.errors

    all_guesses.extend(
        [build_guess_data(submission) for submission in team.puzzle_submissions(puzzle)]
    )

    form_errors = None if guess_data else form.errors
    return JsonResponse(
        {
            "form_errors": form_errors,
            "guesses": all_guesses,
            "ratelimit_data": ratelimit_data,
        },
        status=status,
    )


def process_guess(solve_time, team, puzzle, normalized_answer):
    is_correct = normalized_answer == puzzle.normalized_answer
    answer_submission = AnswerSubmission(
        team=team,
        puzzle=puzzle,
        submitted_answer=normalized_answer,
        is_correct=is_correct,
        used_free_answer=False,
    )
    answer_submission.save()
    guess_data = build_guess_data(answer_submission)

    if is_correct and solve_time < HUNT_END_TIME:
        team.last_solve_time = solve_time
        team.save()

        # Unlock all story cards that are post-solve.
        for story_card in puzzle.story_cards.filter(unlocks_post_solve=True):
            StoryCardUnlock.objects.get_or_create(team=team, story_card=story_card)

    return guess_data


# TODO: the following endpoints are from legacy GPH and need to be reimplemented.
@validate_puzzle(require_team=True)
@restrict_access(after_hunt_end=False)
def free_answer(request):
    puzzle = request.context.puzzle
    team = request.context.team
    if request.method == "POST":
        if puzzle.is_meta:
            messages.error(request, "You can\u2019t use a free answer on a metapuzzle.")
        elif request.context.puzzle_answer:
            messages.error(request, "You\u2019ve already solved this puzzle!")
        elif team.num_free_answers_remaining <= 0:
            messages.error(request, "You have no free answers to use.")
        elif request.POST.get("use") == "Yes":
            AnswerSubmission(
                team=team,
                puzzle=puzzle,
                submitted_answer=puzzle.normalized_answer,
                is_correct=True,
                used_free_answer=True,
            ).save()
            messages.success(request, "Free answer used!")
        return redirect("solve", puzzle.slug)
    return render(request, "free_answer.html")


@validate_puzzle()
@restrict_access(after_hunt_end=True)
def post_hunt_solve(request):
    puzzle = request.context.puzzle
    answer = Puzzle.normalize_answer(request.GET.get("answer"))
    is_correct = answer == puzzle.normalized_answer
    return render(
        request,
        "post_hunt_solve.html",
        {
            "is_correct": answer is not None and is_correct,
            "is_wrong": answer is not None and not is_correct,
            "form": SubmitAnswerForm(),
        },
    )


@require_GET
@restrict_access()
def unanswered_email_list(request):
    is_spam = request.GET.get("spam") == "true"
    to_username = request.GET.get("to")
    to_filters = [
        # FIXME
        "custom-puzzle",
    ]

    unanswered_all = list(
        Email.objects.select_related("team")
        .defer("raw_content", "header_content")
        .filter(
            is_from_us=False,
            status=Email.RECEIVED_NO_REPLY,
        )
        .order_by("received_datetime")
    )
    unanswered_counts = defaultdict(int)
    unclaimed_counts = defaultdict(int)
    unanswered = []
    for email in unanswered_all:
        if email.is_spam:
            unanswered_counts["spam"] += 1
            unclaimed_counts["spam"] += email.claimed_datetime is not None
            if is_spam:
                unanswered.append(email)
        else:
            found = False
            for username in to_filters:
                to_address = f"{username}@{settings.EMAIL_USER_DOMAIN}"
                if to_address in email.to_addresses:
                    found = True
                    unanswered_counts[username] += 1
                    unclaimed_counts[username] += email.claimed_datetime is not None
                    if to_username == username:
                        unanswered.append(email)
            if not found:
                unanswered_counts["rest"] += 1
                if email.claimed_datetime is not None:
                    unclaimed_counts["rest"] += email.claimed_datetime is not None
                if to_username not in to_filters:
                    unanswered.append(email)

    # filter to only show last email in thread but use earliest created timestamp
    by_id = {
        email.message_id: email for email in unanswered if email.message_id is not None
    }
    all_reference_ids = set()
    for email in unanswered:
        all_reference_ids.update(
            (
                _id
                for _id in email.reference_ids
                if _id is not None and _id != email.message_id
            )
        )
    unanswered = [
        email for email in unanswered if email.message_id not in all_reference_ids
    ]
    # set thread_received_time to minimum time of unanswered email
    for email in unanswered:
        email.thread_received_time = email.received_datetime
        for _id in email.reference_ids:
            referenced_email = by_id.get(_id)
            if referenced_email is not None:
                email.thread_received_time = min(
                    email.thread_received_time, referenced_email.received_datetime
                )

    # for stats, only count emails after hunt has started
    answered = Email.objects.filter(
        is_from_us=False,
        response__isnull=False,
        received_datetime__gte=HUNT_START_TIME,
    )
    most_answers = list(
        answered.values("claimer").annotate(count=Count("claimer")).order_by("-count")
    )
    total_answers = sum(by_user["count"] for by_user in most_answers)
    avg_timedelta = answered.annotate(
        response_time=F("response__received_datetime") - F("received_datetime"),
    ).aggregate(avg_time=Avg("response_time"))["avg_time"]
    avg_time = 0 if avg_timedelta is None else avg_timedelta.total_seconds()
    now = datetime.datetime.now(datetime.timezone.utc)

    # stats for emails waiting to be sent via a Celery task
    unsent_email_stats = Email.objects.filter(
        status=Email.SENDING,
        scheduled_datetime__lte=now,
    ).aggregate(
        count=Count("pk"),
        min_scheduled_time=Min("scheduled_datetime"),
        max_scheduled_time=Max("scheduled_datetime"),
    )

    return render(
        request,
        "request_list.html",
        {
            "name": "email",
            "is_hint": False,
            "unanswered": unanswered,
            "most_answers": most_answers,
            "avg_time": avg_time,
            "num_answered": total_answers,
            "unsent_email_stats": unsent_email_stats,
            "filters": {
                "spam": is_spam,
                "unanswered_counts": unanswered_counts,
                "unclaimed_counts": unclaimed_counts,
                "to_filters": to_filters,
            },
        },
    )


@require_GET
@restrict_access()
def hint_list(request):
    # only show last request in thread but use earliest created timestamp
    unanswered = (
        Hint.objects.select_related("team", "puzzle")
        .filter(is_request=True, response__isnull=True)
        .exclude(status__in=(Hint.OBSOLETE, Hint.RESOLVED))
        .annotate(
            db_original_request_id=Case(
                When(root_ancestor_request__isnull=True, then="id"),
                default="root_ancestor_request_id",
            )
        )
        .annotate(
            created_datetime=Window(
                expression=FirstValue("submitted_datetime"),
                partition_by=["db_original_request_id"],
            ),
            thread_last_request_id=Window(
                expression=LastValue("id"),
                partition_by=["db_original_request_id"],
            ),
            thread_last_claimer=Subquery(
                Hint.objects.filter(
                    Q(id=OuterRef("db_original_request_id"))
                    | Q(root_ancestor_request_id=OuterRef("db_original_request_id")),
                )
                .exclude(claimer__exact="")
                .order_by("-id")
                .values("claimer")[:1],
            ),
        )
        .order_by("created_datetime")
    )
    # easier to filter for last hint in thread in python than with a subquery
    unanswered = [hint for hint in unanswered if hint.id == hint.thread_last_request_id]

    popular = list(
        Hint.objects.values("puzzle_id")
        .annotate(count=Count("team_id", distinct=True))
        .order_by("-count")
    )
    answered = Hint.objects.filter(is_request=False)
    most_answers = list(
        answered.values("claimer").annotate(count=Count("claimer")).order_by("-count")
    )
    total_answers = sum(by_user["count"] for by_user in most_answers)
    avg_timedelta = answered.annotate(
        response_time=F("submitted_datetime") - Min("request_set__submitted_datetime"),
    ).aggregate(avg_time=Avg("response_time"))["avg_time"]
    avg_time = 0 if avg_timedelta is None else avg_timedelta.total_seconds()
    puzzles = {puzzle.id: puzzle for puzzle in request.context.all_puzzles}
    for aggregate in popular:
        aggregate["puzzle"] = puzzles[aggregate["puzzle_id"]]

    return render(
        request,
        "request_list.html",
        {
            "name": "hint",
            "is_hint": True,
            "popular": popular,
            "unanswered": unanswered,
            "most_answers": most_answers,
            "avg_time": avg_time,
            "num_answered": total_answers,
            "filters": None,
        },
    )


@restrict_access()
def debug_hint(request):
    """Creates hints for debugging purposes, ignores solve status, hints left, etc."""
    puzzle = Puzzle.objects.get(slug="FIXME")
    team = Team.objects.get(team_name=ADMIN_TEAM_NAME)
    if request.method == "POST":
        form = RequestHintForm(team, request.POST)
        if not form.is_valid():
            return JsonResponse({"reply": "Invalid hint request."}, status=400)
        # Form valid.
        text_content = form.cleaned_data["text_content"]
        notify_emails = form.cleaned_data["notify_emails"]
        Hint(
            team=team,
            puzzle=puzzle,
            text_content=text_content,
            notify_emails=notify_emails,
        ).save()
        return redirect("hint-list")

    form = RequestHintForm(team)
    context = {"puzzle": puzzle, "form": form}
    return render(request, "hints.html", context)


@require_POST
@validate_puzzle(require_team=True)
@restrict_access(after_hunt_end=False)
def create_hint(request):
    puzzle = request.context.puzzle
    team = request.context.team

    form = RequestHintForm(team, request.POST)
    if not form.is_valid():
        return JsonResponse({"reply": "Invalid hint request."}, status=400)

    thread_id = form.cleaned_data["thread_id"]
    if thread_id is not None:
        original_request = Hint.objects.filter(pk=thread_id).first()
        if (
            original_request is None
            or original_request.team_id != team.pk
            or original_request.puzzle_id != puzzle.pk
        ):
            return JsonResponse(
                {"reply": "Invalid hint request."},
                status=400,
            )

    relevant_hints_remaining = (
        team.num_hints_remaining
        if puzzle.round == INTRO_ROUND
        else team.num_nonintro_hints_remaining
    )

    if (
        relevant_hints_remaining <= 0
        and team.num_free_answers_remaining <= 0
        and thread_id is None
    ):
        return JsonResponse({"reply": "You have no more hints available!"}, status=400)

    # Form valid.
    text_content = form.cleaned_data["text_content"]
    notify_emails = form.cleaned_data["notify_emails"]

    if Hint.objects.filter(
        is_request=True,
        team=team,
        puzzle=puzzle,
        text_content=text_content,
    ).exists():
        return JsonResponse(
            {"reply": "You\u2019ve already asked the exact same hint question!"},
            status=400,
        )

    with transaction.atomic():
        # TODO: fix this hint counting logic and race conditions
        if thread_id is None and team.num_hints_remaining <= 0:
            team.total_hints_awarded += 1
            team.total_free_answers_awarded -= 1
            team.save()

        hint = Hint(
            team=team,
            puzzle=puzzle,
            text_content=text_content,
            notify_emails=notify_emails,
            root_ancestor_request_id=thread_id,
        )
        hint.save()

    return JsonResponse(
        {
            "reply": "Your request for a hint has been submitted and the puzzlehunt "
            "staff has been notified\u2014we will respond to it soon!",
            "hintThreads": hint_data(puzzle, team),
        }
    )


@restrict_access()
def manage_extra_guess_grant(request, id):
    guess_grant = ExtraGuessGrant.objects.select_related().filter(id=id).first()
    if not guess_grant:
        return JsonResponse({}, status=404)

    if request.method == "POST":
        prev_status = guess_grant.status
        if "no" in request.POST:
            guess_grant.status = ExtraGuessGrant.NO_RESPONSE
        elif "yes" in request.POST:
            guess_grant.status = ExtraGuessGrant.GRANTED
            form = ExtraGuessGrantForm(request.POST)
            if form.is_valid():
                guess_grant.extra_guesses = form.cleaned_data["extra_guesses"]
        # Only save on changes to reduce Discord alerts.
        if guess_grant.status != prev_status:
            guess_grant.save()
            if guess_grant.status == ExtraGuessGrant.GRANTED:
                dispatch_extra_guess_alert(guess_grant.granted_discord_message())
                send_mail_wrapper(
                    "Extra guesses granted for {}".format(guess_grant.puzzle),
                    "extra_guess_email",
                    {"guess_grant": guess_grant},
                    guess_grant.team.get_emails(),
                )

    ratelimit = get_ratelimit(guess_grant.puzzle, guess_grant.team)
    form = ExtraGuessGrantForm(instance=guess_grant)

    return render(
        request,
        "extra_guess.html",
        {"guess_grant": guess_grant, "form": form, "ratelimit": ratelimit},
    )


@restrict_access()
def resend_emails(request):
    if request.method == "POST":
        pks = request.POST.getlist("pks")
        try:
            pks = list(map(int, pks))
        except:
            pass
        else:
            if pks:
                celery_app.send_task(
                    "puzzles.emailing.task_resend_emails", kwargs={"pks": pks}
                )
                return redirect("email-main")

    cooldown = datetime.timedelta(seconds=Email.RESEND_COOLDOWN)
    now = timezone.now()
    unsent_emails = list(
        Email.objects.filter(status=Email.SENDING)
        .exclude(scheduled_datetime__gt=now)
        .exclude(attempted_send_datetime__gt=now - cooldown)
        # exclude when all address lists are empty
        .exclude(to_addresses__len=0, cc_addresses__len=0, bcc_addresses__len=0)
        .defer("raw_content", "header_content")
        .order_by("scheduled_datetime")
    )
    return render(
        request,
        "resend_emails.html",
        {
            "unsent_emails": unsent_emails,
        },
    )


# TODO: address multiple responses
@restrict_access()
def email(request, id):
    if request.method == "POST":
        if request.POST.get("action") == AnswerEmailForm.ACTION_UNCLAIM:
            action = "unclaim"
        elif request.POST.get("action") == AnswerEmailForm.ACTION_NO_REPLY:
            action = "no-reply"
        elif request.POST.get("action") == AnswerEmailForm.ACTION_CUSTOM_PUZZLE:
            action = "custom-puzzle"
        else:
            action = "update"
    else:
        action = "get"

    claimer = request.COOKIES.get("claimer", "")

    form = None
    if action in ("no-reply", "update"):
        form = AnswerEmailForm(request.POST)
        if form.is_valid():
            email_in_reply_to_pk = form.cleaned_data["email_in_reply_to_pk"]
            text_content = form.cleaned_data["text_content"]

            email_in_reply_to = (
                Email.objects.select_related("team")
                .filter(pk=email_in_reply_to_pk)
                .first()
            )
            if not email_in_reply_to:
                return JsonResponse({}, status=404)

            reference_ids = set(
                filter(
                    bool,
                    (email_in_reply_to.message_id, *email_in_reply_to.reference_ids),
                )
            )
            emails_with_updated_status = Email.objects.filter(
                message_id__in=reference_ids,
                status=Email.RECEIVED_NO_REPLY,
            )

            if action == "no-reply":
                # Redundant with the update call, but needs to be set on the object
                # for dispatch alert to work correctly.
                email_in_reply_to.status = Email.RECEIVED_NO_REPLY_REQUIRED
                with transaction.atomic():
                    count = emails_with_updated_status.update(
                        status=Email.RECEIVED_NO_REPLY_REQUIRED
                    )

                    def commit_action():
                        if count:
                            dispatch_email_response_alert(
                                Email.responded_discord_message(email_in_reply_to)
                            )
                            messages.success(request, "Email resolved.")

                    transaction.on_commit(commit_action)
                if not count:
                    return JsonResponse({}, status=400)
                return redirect("unanswered-email-list")

            email_reply = Email.ReplyEmail(
                email_in_reply_to,
                plain=text_content,
                reply_all=True,
                check_addresses=False,
                claimer=claimer,
            )
            with transaction.atomic():
                email_reply.save()
                emails_with_updated_status.update(
                    response=email_reply,
                    status=Email.RECEIVED_ANSWERED,
                )

                def commit_action():
                    dispatch_email_response_alert(
                        Email.responded_discord_message(email_in_reply_to, email_reply)
                    )
                    messages.success(request, "Email queued.")

                transaction.on_commit(commit_action)
            return redirect("unanswered-email-list")

    email_request = (
        Email.objects.select_related("team", "response")
        .defer("raw_content", "header_content")
        .filter(id=id)
        .first()
    )
    if not email_request:
        return JsonResponse({}, status=404)

    email_response = email_request.response

    if action == "custom-puzzle":
        form = AnswerEmailForm(request.POST)
        if form.is_valid():
            text_content = django.template.loader.render_to_string(
                # FIXME
                "puzzle_responses/sample_email.txt"
            )
            formvalues = dict(form.cleaned_data)
            formvalues.update(
                {
                    "text_content": text_content,
                }
            )
            form = AnswerEmailForm(formvalues)

    elif form is None:
        form = AnswerEmailForm()
        form.cleaned_data = {}

    if action == "unclaim":
        if email_request.status == Email.RECEIVED_NO_REPLY:
            email_request.claimed_datetime = None
            email_request.claimer = ""
            email_request.save(update_fields=["claimer", "claimed_datetime"])
            messages.warning(request, "Unclaimed.")
        return redirect("unanswered-email-list")

    form.initial["email_in_reply_to_pk"] = email_request.pk

    reply_to_addresses = [email_request.from_address]
    reply_cc_addresses = [
        address
        for address in email_request.recipients(bcc=False)
        if not Email.check_is_address_us(address)
    ]

    request_tree_emails = list(
        email_request.get_emails_in_thread_filter()
        .select_related("team")
        .defer("raw_content", "header_content")
        .order_by("received_datetime")
    )
    nonleaf_ids = set()
    reference_ids = set(
        filter(bool, (email_request.message_id, *email_request.reference_ids))
    )
    for email in request_tree_emails:
        nonleaf_ids.update(
            (_id for _id in email.reference_ids if _id != email.message_id)
        )
    for email in request_tree_emails:
        email.is_leaf = email.message_id not in nonleaf_ids
        email.is_on_path_to_request = email.message_id in reference_ids

    # query by from_address will only match if name and address are exactly
    # correct, but we probably don't really care
    emails_for_same_team = list(
        Email.objects.defer("raw_content", "header_content")
        .filter(
            (Q() if email_request.team_id is None else Q(team_id=email_request.team_id))
            | Q(from_address=email_request.from_address)
            | Q(to_addresses__contains=[email_request.from_address])
            | Q(cc_addresses__contains=[email_request.from_address]),
            hint__isnull=True,
            # received_datetime__gte=HUNT_START_TIME,
        )
        .exclude(
            pk=email_request.pk,
        )
        .exclude(
            **(
                {"root_reference_id": email_request.root_reference_id}
                if email_request.root_reference_id
                else {}
            ),
        )
        .order_by("received_datetime")
    )
    trees_for_same_team = defaultdict(lambda: {"emails": []})
    for i, email in enumerate(emails_for_same_team):
        # use i to give emails without ids unique ids
        tree = trees_for_same_team[email.root_reference_id or email.message_id or i]
        tree["emails"].append(email)
        tree["last"] = email
        if email.is_from_us:
            tree["last_response"] = email
        if email.template_id is None:
            tree.setdefault("first", email)
    for tree in trees_for_same_team.values():
        tree.setdefault("first", tree["emails"][0])
    trees_for_same_team = sorted(
        trees_for_same_team.values(),
        key=lambda tree: tree["first"].received_datetime,
        reverse=True,
    )

    if claimer:
        claimer = unquote(claimer)
        if email_request.status != Email.RECEIVED_NO_REPLY:
            if email_request.claimed_datetime is None:
                msg = "This email does not require a response."
            else:
                msg = "This email has been answered{}!".format(
                    " by " + email_request.claimer if email_request.claimer else ""
                )
            form.add_error(
                None,
                msg,
            )
        elif email_request.claimed_datetime:
            if email_request.claimer != claimer:
                form.add_error(
                    None,
                    "This email is currently claimed{}!".format(
                        " by " + email_request.claimer if email_request.claimer else ""
                    ),
                )
        else:
            email_request.claimed_datetime = request.context.now
            email_request.claimer = claimer
            email_request.save(update_fields=["claimer", "claimed_datetime"])
            messages.success(request, "You have claimed this email!")
    else:
        messages.error(
            request,
            "Please set your name before claiming emails! (If you just set your name, you can refresh or click Claim.)",
        )

    return render(
        request,
        "answer_email.html",
        {
            "request_tree_emails": request_tree_emails,
            "email_request": email_request,
            "email_response": email_response,
            "reply_to_addresses": reply_to_addresses,
            "reply_cc_addresses": reply_cc_addresses,
            "trees_for_same_team": trees_for_same_team,
            "form": form,
        },
    )


# TODO: address multiple responses
@restrict_access()
def hint(request, id):
    if request.method == "POST" and request.POST.get("action") == "unclaim":
        action = "unclaim"
    elif request.method == "POST":
        action = "update"
    else:
        action = "get"

    def get_hint_request(request_id):
        return (
            Hint.objects.select_related()
            .defer("email__raw_content")
            .filter(id=request_id)
            .first()
        )

    if action == "update":
        form = AnswerHintForm(request.POST)
        if form.is_valid():
            text_content = form.cleaned_data["text_content"]
            status = form.cleaned_data["status"]

            hint_request = get_hint_request(form.cleaned_data["hint_request_id"])
            if not hint_request or not hint_request.is_request:
                return JsonResponse({}, status=404)

            if hint_request.response:
                # response already existed, we're just updating it
                hint_request.response.text_content = text_content
                with transaction.atomic():
                    hint_request.response.save(update_fields=("text_content",))
                    if status not in (Hint.OBSOLETE, Hint.RESOLVED):
                        original_request = hint_request.original_request
                        original_request.status = status
                        original_request.save(update_fields=("status",))
                    # Dispatch an alert on update so that we can edit the embed.
                    dispatch_hint_response_alert(
                        Hint.responded_discord_message(
                            hint_request, hint_request.response
                        )
                    )
                return redirect("hint-list")

            if status in (Hint.OBSOLETE, Hint.RESOLVED) and not text_content:
                hint_response = None
                requests_to_update = hint_request.get_prior_requests_needing_response()
                hint_email = None
                if any(
                    request.pk == hint_request.original_request_id
                    for request in requests_to_update
                ):
                    # should not immediately resolve a thread without responding
                    return JsonResponse({}, status=400)
            else:
                objs = hint_request.populate_response_and_update_requests(text_content)
                hint_response = objs["response"]
                requests_to_update = objs["requests"]
                hint_email = objs["response_email"]

            with transaction.atomic():
                if hint_email is not None:
                    # Hint message written, notify teams.
                    # Note: we can still stealth edit by editing the hint response in
                    # Django admin.
                    hint_email.save()
                if hint_response is not None:
                    hint_response.save()
                individual_status_updates = {}
                # The actual DB update is done in the update() calls, setting status
                # here is just so the Discord alert sees the status it will be.
                hint_request.status = status
                if status in (Hint.OBSOLETE, Hint.RESOLVED):
                    if not hint_response:
                        individual_status_updates["status"] = status
                    Hint.objects.filter(
                        pk=hint_request.original_request_id,
                        status__in=(Hint.NO_RESPONSE, Hint.REQUESTED_MORE_INFO),
                    ).update(status=status)
                else:
                    Hint.objects.filter(pk=hint_request.original_request_id).update(
                        status=status
                    )
                Hint.objects.filter(
                    pk__in=[request.pk for request in requests_to_update]
                ).update(
                    response=hint_response,
                    claimer=hint_request.claimer,
                    claimed_datetime=hint_request.claimed_datetime,
                    **individual_status_updates,
                )
                # If we're at this point, then this must be a new hint reponse, since
                # if it already exists we would have hit the earlier redirect.
                if hint_response:

                    def commit_action():
                        dispatch_hint_response_alert(
                            Hint.responded_discord_message(hint_request, hint_response)
                        )
                        messages.success(request, "Hint saved.")

                    transaction.on_commit(commit_action)
            return redirect("hint-list")

    hint_request = (
        Hint.objects.select_related().defer("email__raw_content").filter(id=id).first()
    )
    if not hint_request:
        return JsonResponse({}, status=404)
    hint_response = hint_request.get_or_populate_response()
    form = AnswerHintForm(instance=hint_response)
    form.cleaned_data = {}

    if action == "unclaim":
        if hint_request.status == Hint.NO_RESPONSE:
            hint_request.claimed_datetime = None
            hint_request.claimer = ""
            hint_request.save(update_fields=["claimer", "claimed_datetime"])
            messages.warning(request, "Unclaimed.")
        return redirect("hint-list")

    limit = request.META.get("QUERY_STRING", "")
    limit = int(limit) if limit.isdigit() else 20
    all_previous = Hint.objects.filter(puzzle=hint_request.puzzle)

    hints_by_same_team = all_previous.filter(team_id=hint_request.team_id).order_by(
        "submitted_datetime"
    )
    threads_for_same_team = defaultdict(
        lambda: {"hints": [], "last_request": None, "last_response": None}
    )
    for hint in hints_by_same_team:
        threads_for_same_team[hint.original_request_id]["hints"].append(hint)
        threads_for_same_team[hint.original_request_id][
            "last_request" if hint.is_request else "last_response"
        ] = hint
    request_thread = threads_for_same_team.pop(
        hint_request.original_request_id, [hint_request]
    )
    threads_for_same_team = sorted(
        threads_for_same_team.values(),
        key=lambda thread: thread["hints"][0].submitted_datetime,
        reverse=True,
    )

    previous_by_others = (
        all_previous.filter(
            Q(status=Hint.ANSWERED) | Q(root_ancestor_request__status=Hint.ANSWERED),
            response__isnull=False,
        )
        .select_related("team", "response")
        .exclude(team_id=hint_request.team_id)
        .annotate(answered_datetime=F("response__submitted_datetime"))
        .order_by("-answered_datetime")[:limit]
    )
    request.context.puzzle = hint_request.puzzle

    for hint in request_thread["hints"]:
        if hint.is_request:
            hint_request = hint
        # if editing a previous response, ignore requests that came after
        if hint == hint_response:
            break
    form.initial["hint_request_id"] = hint_request.id

    claimer = request.COOKIES.get("claimer", "")
    if claimer:
        claimer = unquote(claimer)
        if hint_request.response_id is not None:
            form.add_error(
                None,
                "This hint has been answered{}!".format(
                    " by " + hint_request.claimer if hint_request.claimer else ""
                ),
            )
        elif hint_request.claimed_datetime:
            if hint_request.claimer != claimer:
                form.add_error(
                    None,
                    "This hint is currently claimed{}!".format(
                        " by " + hint_request.claimer if hint_request.claimer else ""
                    ),
                )
        else:
            hint_request.claimed_datetime = request.context.now
            hint_request.claimer = claimer
            hint_request.save(update_fields=["claimer", "claimed_datetime"])
            messages.success(request, "You have claimed this hint!")
    else:
        messages.error(
            request,
            "Please set your name before claiming hints! (If you just set your name, you can refresh or click Claim.)",
        )

    return render(
        request,
        "hint.html",
        {
            "request_thread": request_thread,
            "hint_response": hint_response,
            "hint_request": hint_request,
            "threads_for_same_team": threads_for_same_team,
            "previous_by_others": previous_by_others,
            "form": form,
        },
    )


@require_GET
@restrict_access()
def guess_csv(request):
    response = HttpResponse(content_type="text/csv")
    fname = "hunt_guesslog_{}.csv".format(request.context.now.strftime("%Y%m%dT%H%M%S"))
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(fname)
    writer = csv.writer(response)
    for ans in (
        AnswerSubmission.objects.annotate(
            team_name=F("team__team_name"), puzzle_name=F("puzzle__name")
        )
        .order_by("submitted_datetime")
        .exclude(team__is_hidden=True)
    ):
        writer.writerow(
            [
                ans.submitted_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                ans.team_name,
                ans.puzzle_name,
                ans.submitted_answer,
                "F" if ans.used_free_answer else ("Y" if ans.is_correct else "N"),
            ]
        )
    return response


@require_GET
@restrict_access()
def hint_csv(request):
    response = HttpResponse(content_type="text/csv")
    fname = "hunt_hintlog_{}.csv".format(request.context.now.strftime("%Y%m%dT%H%M%S"))
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(fname)
    writer = csv.writer(response)
    for hint in (
        Hint.objects.annotate(
            team_name=F("team__team_name"),
            puzzle_name=F("puzzle__name"),
            answered_datetime=F("response__submitted_datetime"),
        )
        .order_by("submitted_datetime")
        .exclude(team__is_hidden=True)
    ):
        writer.writerow(
            [
                hint.submitted_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                None
                if hint.answered_datetime is None
                else (hint.answered_datetime.strftime("%Y-%m-%d %H:%M:%S")),
                hint.team_name,
                hint.puzzle_name,
                hint.response,
            ]
        )
    return response
