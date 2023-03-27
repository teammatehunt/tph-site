import base64
import csv
import datetime
import functools
import os
from collections import defaultdict
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
    When,
    Window,
)
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from spoilr.core.api.hunt import is_site_solutions_published
from spoilr.core.models import HQUpdate, InteractionAccess, InteractionType, Round
from spoilr.hints.models import CannedHint, Hint
from spoilr.utils import generate_url, json

from puzzles.forms import ExtraGuessGrantForm, RequestHintForm
from puzzles.messaging import (
    dispatch_event_used_alert,
    dispatch_extra_guess_alert,
    send_mail_wrapper,
)
from puzzles.models import (
    ExtraGuessGrant,
    ExtraUnlock,
    Puzzle,
    PuzzleAccess,
    PuzzleSubmission,
    Team,
    build_guess_data,
)
from puzzles.rounds.utils import (
    SKIP_ROUNDS,
    get_round_data,
    get_round_positions,
    get_round_puzzles,
    get_superround_urls,
)
from puzzles.utils import HintVisibility, get_encryption_keys, hint_availability
from puzzles.views.auth import restrict_access, validate_puzzle
from puzzles.views.hints import maybe_create_hint
from puzzles.views.story import story_card_data
from puzzles.views.submissions import (
    get_allowed_a3_free_puzzles,
    get_allowed_free_puzzles,
    get_ratelimit,
    process_guess,
    submit_answer,
)

FORCE_VIRTUAL_UNLOCK = True


def virtual_unlock_initial_data(slug, virtual_delay_mins, module_name=None):
    """A shared tool that can be used to check if a virtual puzzle should be unlocked."""

    if module_name is None:
        module_name = slug

    def virtual_unlock_time(request, team):
        # Force all puzzles to be unlocked
        if FORCE_VIRTUAL_UNLOCK:
            return {"unlockTime": 0, "cryptKeys": get_encryption_keys([module_name])}

        # Convert delay to seconds
        delay = virtual_delay_mins * 60
        access = PuzzleAccess.objects.filter(team=team, puzzle__slug=slug).first()
        if access:
            # Check if overridden in admin
            if request.context.puzzle.override_virtual_unlocked:
                time_left_s = 0
            else:
                time_open = timezone.now() - access.timestamp
                time_left_s = max(0, delay - time_open.total_seconds())
        elif team.is_internal:
            # This case should only happen in the admin/internal team case where
            # a PuzzleAccess doesn't exist. For real teams, the auth code will prevent
            # this case from being reached.
            time_left_s = 0
        else:
            time_left_s = delay

        data = {"unlockTime": time_left_s}
        if time_left_s == 0:
            data["cryptKeys"] = get_encryption_keys([module_name])

        return data

    return virtual_unlock_time


# A map from slug to function getting data to pass on page load
# Function should be (request, team) => dict (or other json convertible object)
# FIXME: Add initial data here
PUZZLE_SPECIFIC_PRIVATE_INITIAL_DATA: Mapping[str, Callable] = {}


# A map from interaction-slug to function checking if the interaction is unlocked
# FIXME: Add interaction unlocks here
PUZZLE_SPECIFIC_INTERACTION_UNLOCKS: Mapping[str, Callable] = {}


@require_GET
def get_rounds(request):
    """Fetches all rounds to show on the landing page."""
    team = request.context.team
    if not team:
        return JsonResponse({"rounds": []})

    if request.context.hunt_has_started or request.context.hunt_has_almost_started:
        # Trigger unlocks on landing page visits
        # Even before hunt starts, pre-unlock puzzles with deep 0 to stagger db load
        request.context.puzzle_unlocks
    if not request.context.hunt_has_started:
        return JsonResponse({"rounds": []})

    story_state = request.context.story_state
    rounds = team.unlocked_rounds()
    round_data = [
        get_round_data(request, puzzle_round, team, images=("wordmark_small",))
        for puzzle_round in rounds
        if puzzle_round.slug not in SKIP_ROUNDS
    ]
    act = 1

    return JsonResponse(
        {
            "bg": get_superround_urls(act),
            "rounds": [
                {
                    **puzzle_round,
                    "wordmark": puzzle_round["wordmark_small"],
                    "position": get_round_positions(act, puzzle_round["slug"]),
                }
                for puzzle_round in round_data
            ],
        }
    )


@require_GET
def puzzles_by_round(request, round_slug=None):
    """Fetches puzzle data to show on the puzzle list or map page."""
    if not request.context.hunt_has_started:
        return JsonResponse({"puzzles": {}, "rounds": None})

    round_data = get_round_puzzles(request, round_slug)
    if not round_data:
        return JsonResponse({}, status=404)

    return JsonResponse(round_data)


@require_GET
def get_puzzles_team_api(request):
    """
    Public api for team scripts to fetch the puzzle list
    """
    team = request.context.team
    if not team:
        logged_out_data = {"error": "must be logged in"}
        return JsonResponse(logged_out_data, status=401)

    if not request.context.hunt_has_started:
        # Let teams see an example for prehunt
        clean_data = [
            {
                "name": "Sample Puzzle Name",
                "round": "Sample Round Name",
                "url": generate_url("hunt", "/puzzles/fake-url-this-is-not-a-puzzle"),
                "isMeta": False,
                "answer": None,
            }
        ]
    else:
        data = get_round_puzzles(request)
        clean_data = [
            {
                "name": puzzle["name"],
                "round": data["rounds"][round_slug]["name"],
                "url": puzzle["url"],
                "isMeta": puzzle["isMeta"],
                "answer": puzzle["answer"],
            }
            for round_slug, puzzles in data.get("puzzles", {}).items()
            for puzzle in puzzles
        ]
    # NB: Browsers patched the vulnerability allowed by safe=False in 2012
    # https://docs.djangoproject.com/en/4.0/ref/request-response/#jsonresponse-objects
    return JsonResponse(clean_data, safe=False)


def _get_hints(puzzle, team):
    if puzzle.canonical_puzzle:
        puzzle = puzzle.canonical_puzzle
        if puzzle.canonical_puzzle:
            raise RuntimeError(f"Canonical puzzle chain longer than 2: {puzzle.slug}")
    return Hint.objects.filter(team=team, puzzle=puzzle).order_by("timestamp")


def hint_data(puzzle, team):
    threads = defaultdict(lambda: {"hints": []})  # keyed by original_request_id
    for hint in _get_hints(puzzle, team):
        if hint.is_request and hint.root_ancestor_request_id is None:
            threads[hint.original_request_id]["threadId"] = hint.pk
            threads[hint.original_request_id]["status"] = hint.status
        threads[hint.original_request_id]["hints"].append(
            {
                "isRequest": hint.is_request,
                "requiresResponse": hint.requires_response,
                "content": hint.text_content,
                "submitTime": hint.timestamp,
            }
        )
    return list(threads.values())


def _get_errata(puzzle):
    if puzzle.canonical_puzzle:
        puzzle = puzzle.canonical_puzzle
        if puzzle.canonical_puzzle:
            raise RuntimeError(f"Canonical puzzle chain longer than 2: {puzzle.slug}")
    return [
        err.render_data()
        for err in HQUpdate.objects.filter(puzzle=puzzle, published=True).order_by(
            "creation_time"
        )
    ]


def _get_canned_hints(puzzle):
    if puzzle.canonical_puzzle:
        puzzle = puzzle.canonical_puzzle
        if puzzle.canonical_puzzle:
            raise RuntimeError(f"Canonical puzzle chain longer than 2: {puzzle.slug}")
    return [
        {"keywords": canned.keywords, "content": canned.content}
        for canned in CannedHint.objects.filter(puzzle=puzzle).order_by("order")
    ]


def get_puzzle_interaction_data(request, puzzle, team, guesses):
    interaction = puzzle.interaction_set.filter(
        interaction_type=InteractionType.PHYSICAL
    ).first()
    if not interaction:
        return None

    if interaction.required_pseudoanswer:
        # Check if any correct submissions match the pseudoanswer
        normalized_pseudoanswer = puzzle.normalize_answer(
            interaction.required_pseudoanswer.answer
        )
        if not any(
            [
                guess["partial"] and guess["guess"] == normalized_pseudoanswer
                for guess in guesses
            ]
        ):
            return None

    interaction_data = {
        "slug": interaction.slug,
        "instructions": interaction.instructions,
    }
    interaction_access = InteractionAccess.objects.filter(
        team=team, interaction=interaction
    ).first()
    if interaction_access:
        interaction_data["comments"] = interaction_access.request_comments
    elif interaction.unlocks_with_puzzle:
        pass
    elif get_unlocked := PUZZLE_SPECIFIC_INTERACTION_UNLOCKS.get(interaction.slug):
        if not get_unlocked(request, team):
            return None
    else:
        # Team does not have access to interaction yet
        return None

    if get_data := PUZZLE_SPECIFIC_PRIVATE_INITIAL_DATA.get(puzzle.slug):
        # hack for designating infinite puzzles
        if getattr(get_data, "is_infinite", False):
            # the infinite private puzzle data is nonempty when the puzzle is
            # visible (due to needing to pass cryptKeys).
            # NB: this makes a couple extra function calls but they are all cached anyways
            if not get_data(request, team):
                # should not have access to the puzzle yet
                return None

    return interaction_data


def get_puzzle_data(request, puzzle, team):
    """Helper method to retrieve puzzle specific data."""
    solution_link_visible = (
        request.context.hunt_is_over and is_site_solutions_published()
    ) or request.context.is_superuser

    errata = _get_errata(puzzle)
    is_solved = bool(request.context.puzzle_answer)
    hint_visibility, hint_reason = hint_availability(puzzle, team)
    story_state = request.context.story_state

    # Look up art assets from superround
    puzzle_round = puzzle.round.superround or puzzle.round

    guesses = [
        build_guess_data(submission)
        for submission in request.context.puzzle_submissions
    ]
    data = {
        "name": puzzle.name,
        "slug": puzzle.slug,
        # FIXME: inject url if multiple kinds (eg /events/slug and /puzzles/slug)
        # "url": puzzle.url,
        "hintsUrl": puzzle.get_hints_url(story_state)
        if hint_visibility.value >= HintVisibility.CAN_VIEW.value
        else None,
        "round": get_round_data(request, puzzle_round, team, puzzle=puzzle),
        "isSolved": is_solved,
        "guesses": guesses,
        "solutionLinkVisible": solution_link_visible,
        "rateLimit": get_ratelimit(puzzle, team) if team else None,
        "canViewHints": hint_visibility.value >= HintVisibility.CAN_VIEW.value,
        "canAskForHints": hint_visibility is HintVisibility.CAN_REQUEST,
        "hintReason": hint_reason,
        "hintThreads": hint_data(puzzle, team),
        "errata": errata,
    }

    # Show story cards for solved puzzles only
    if is_solved:
        story_card = puzzle.story_cards.first()
        if story_card:
            data["storycard"] = story_card_data(story_card)

    if team and (team.is_prerelease_testsolver or team.is_internal):
        data["puzzleUrl"] = puzzle.testsolve_url

    interaction = None
    if team:
        # Add interaction for physical puzzles, unless hunt is over
        interaction = get_puzzle_interaction_data(request, puzzle, team, guesses)

    if request.context.hunt_is_over:
        data["answerB64Encoded"] = base64.b64encode(
            puzzle.normalized_answer.encode("utf-8")
        ).decode("utf-8")

        data["partialMessagesB64Encoded"] = [
            [
                base64.b64encode(
                    puzzle.normalize_answer(message.answer).encode("utf-8")
                ).decode("utf-8"),
                base64.b64encode(message.response.encode("utf-8")).decode("utf-8"),
            ]
            for message in puzzle.pseudoanswer_set.all()
        ]
        if interaction:
            data["interaction"] = {"slug": interaction["slug"], "ended": True}
        data["cannedB64Encoded"] = base64.b64encode(
            json.dumps(_get_canned_hints(puzzle)).encode()
        ).decode()
    elif interaction:
        data["interaction"] = interaction

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


@require_POST
@validate_puzzle(require_team=True)
@restrict_access(after_hunt_end=False)
def solve(request):
    puzzle = request.context.puzzle
    team = request.context.team
    uuid = request.POST["uuid"]

    guess_data, status, error_msg, ratelimit_data = submit_answer(
        puzzle,
        team,
        request.POST.get("answer"),
        request.context.puzzle_answer,
        request.context.guesses_remaining,
        request.context.puzzle_submissions,
        request.context.now,
    )

    all_guesses = (
        (
            [] if guess_data is None else [guess_data]
        )  # just pass the latest guess for public teams
        if team.is_public
        # This includes the latest guess, if it was legitimate
        else [
            build_guess_data(submission)
            for submission in team.puzzle_submissions(puzzle)
        ]
    )

    data = {
        "form_errors": {"__all__": error_msg},
        "guesses": all_guesses,
        "ratelimit_data": ratelimit_data,
    }

    interaction = get_puzzle_interaction_data(request, puzzle, team, all_guesses)
    if interaction:
        data["interaction"] = interaction

    return JsonResponse(data, status=status)


@require_GET
def get_puzzles_for_free_answers(request):
    if not request.context.team:
        return JsonResponse({}, status=404)

    puzzles_by_round = defaultdict(list)
    for puzzle in get_allowed_free_puzzles(request):
        puzzles_by_round[puzzle.round.name].append(
            {
                "slug": puzzle.slug,
                "name": puzzle.name,
            }
        )

    normal, _, existing_uses, _ = request.context._internal_num_event_rewards
    return JsonResponse(
        {
            "currency": normal,
            "rounds": puzzles_by_round,
            "used": existing_uses,
        }
    )


@require_GET
def get_rounds_for_free_unlock(request):
    if not request.context.team:
        return JsonResponse({}, status=404)

    team = request.context.team
    # Do not directly send all_display_name to client, that would leak names of rounds.
    locked_puzzles, dk_display_name, all_display_name = team.compute_next_event_unlocks(
        request.context.deep
    )

    # Insert order matches round order.
    rounds = []
    for deep_key in locked_puzzles:
        if len(locked_puzzles[deep_key]) == 0:
            continue
        # Return deep key as the value of the form - this is only readable if you
        # inspect source code, and since this is only for rounds already unlocked,
        # it doesn't seem worth more effort to hide it.
        rounds.append({"name": dk_display_name[deep_key], "slug": deep_key})
    existing_uses = []
    for eu in ExtraUnlock.objects.filter(team=team).order_by("deep_key"):
        existing_uses.append({"name": all_display_name[eu.deep_key], "count": eu.count})
    # Alpha by round name. Too lazy to do it in round order.
    existing_uses.sort(key=lambda d: d["name"])
    return JsonResponse(
        {
            "currency": request.context.num_event_rewards,
            "rounds": rounds,
            "used": existing_uses,
        }
    )


@require_POST
@validate_puzzle(require_team=True)
def free_answer(request):
    puzzle = request.context.puzzle
    team = request.context.team
    if not team:
        return JsonResponse(
            {"message": "You must be logged in to request a free answer."}, status=401
        )

    if puzzle.is_meta:
        return JsonResponse(
            {"message": "You cannot use a free answer on a meta."}, status=400
        )

    allowed_slugs = {puzzle.slug for puzzle in get_allowed_free_puzzles(request)}
    if puzzle.slug not in allowed_slugs:
        return JsonResponse(
            {"message": "You cannot use a free answer on this puzzle."}, status=400
        )

    if request.context.num_event_rewards <= 0:
        return JsonResponse(
            {"message": "You do not have enough event rewards."}, status=400
        )

    answer = puzzle.normalized_answer
    process_guess(
        request.context.now,
        team,
        puzzle,
        answer,
        used_free_answer=True,
    )
    dispatch_event_used_alert(f"{team} used a free answer on {puzzle}")
    # Unlock immediately
    request.context.puzzle_unlocks
    return JsonResponse({"message": "Free answer used!", "answer": answer})


@require_POST
def free_unlock(request, slug):
    team = request.context.team
    if not team:
        return JsonResponse(
            {"message": "You must be logged in to unlock a new puzzle."}, status=401
        )
    if request.context.num_event_rewards <= 0:
        return JsonResponse(
            {"message": "You do not have enough event rewards."}, status=400
        )
    locked_puzzles, dk_display_name, all_display_name = team.compute_next_event_unlocks(
        request.context.deep
    )
    if slug not in locked_puzzles:
        return JsonResponse(
            {"message": "You cannot use an unlock on this round."}, status=400
        )

    # Unlock logic itself occurs in unlock_puzzles() function.
    ExtraUnlock.increment(team, slug)
    dispatch_event_used_alert(f"{team} used a free unlock on {slug}")
    # Unlock immediately
    request.context.puzzle_unlocks
    return JsonResponse(
        {"message": f"Puzzle unlocked in {all_display_name[slug]}!"},
    )


@require_GET
def get_puzzles_for_free_a3_answers(request):
    if not request.context.team:
        return JsonResponse({}, status=404)

    puzzles_by_round = defaultdict(list)
    for puzzle in get_allowed_a3_free_puzzles(request):
        puzzle_round = puzzle.round.superround or puzzle.round
        puzzles_by_round[puzzle_round.name].append(
            {
                "slug": puzzle.slug,
                "name": puzzle.name,
            }
        )

    _, a3, _, existing_a3_uses = request.context._internal_num_event_rewards
    return JsonResponse(
        {
            "currency": a3,
            "rounds": puzzles_by_round,
            "used": existing_a3_uses,
        }
    )


@require_POST
@validate_puzzle(require_team=True)
def free_a3_answer(request):
    puzzle = request.context.puzzle
    team = request.context.team
    if not team:
        return JsonResponse(
            {"message": "You must be logged in to request a free answer."}, status=401
        )

    if puzzle.is_meta:
        return JsonResponse(
            {"message": "You cannot use a free answer on a meta."}, status=400
        )

    allowed_slugs = {puzzle.slug for puzzle in get_allowed_a3_free_puzzles(request)}
    if puzzle.slug not in allowed_slugs:
        return JsonResponse(
            {"message": "You cannot use a free answer on this puzzle."}, status=400
        )

    if request.context.num_a3_event_rewards <= 0:
        return JsonResponse(
            {"message": "You do not have enough event rewards."}, status=400
        )

    answer = puzzle.normalized_answer
    process_guess(
        request.context.now,
        team,
        puzzle,
        answer,
        used_free_answer=True,
    )
    dispatch_event_used_alert(f"{team} used a free Act 3 answer on {puzzle}")
    # Unlock immediately
    request.context.puzzle_unlocks
    return JsonResponse(
        {"message": "Free answer used! See puzzle page for answer.", "answer": answer}
    )


@require_POST
@validate_puzzle(require_team=True)
@restrict_access()
def update_position(request):
    puzzle = request.context.puzzle
    # Save with 1 decimal place because we shouldn't need > 1 in 1000 precision.
    if "x" in request.POST:
        puzzle.icon_x = round(float(request.POST["x"]), 1)
    if "y" in request.POST:
        puzzle.icon_y = round(float(request.POST["y"]), 1)
    if "w" in request.POST:
        puzzle.icon_size = round(float(request.POST["w"]), 1)
    puzzle.save()
    return JsonResponse({})


@require_GET
@restrict_access()
def unanswered_email_list(request):
    return render(request, "request_list.html")


@restrict_access()
def debug_hint(request):
    """Creates hints for debugging purposes, ignores solve status, hints left, etc."""
    puzzle = Puzzle.objects.get(slug="test-puzzle")
    team = Team.objects.get(name="dev")
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
def request_hint(request):
    puzzle = request.context.puzzle
    team = request.context.team

    form = RequestHintForm(team, request.POST)
    if not form.is_valid():
        return JsonResponse({"reply": "Invalid hint request."}, status=400)

    thread_id = form.cleaned_data["thread_id"]
    text_content = form.cleaned_data["text_content"]
    notify_emails = form.cleaned_data["notify_emails"]

    status, msg = maybe_create_hint(
        puzzle, team, text_content, thread_id, notify_emails
    )

    return JsonResponse(
        {"reply": msg, "hintThreads": hint_data(puzzle, team)}, status=status
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
                    f"Extra guesses granted for {guess_grant.puzzle}",
                    "extra_guess_email",
                    {"guess_grant": guess_grant},
                    guess_grant.team.all_emails,
                    is_prehunt=False,
                )

    ratelimit = get_ratelimit(guess_grant.puzzle, guess_grant.team)
    form = ExtraGuessGrantForm(instance=guess_grant)

    return render(
        request,
        "extra_guess.html",
        {"guess_grant": guess_grant, "form": form, "ratelimit": ratelimit},
    )


@require_GET
@restrict_access()
def guess_csv(request):
    response = HttpResponse(content_type="text/csv")
    fname = "tph_guesslog_{}.csv".format(request.context.now.strftime("%Y%m%dT%H%M%S"))
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(fname)
    writer = csv.writer(response)
    for ans in (
        PuzzleSubmission.objects.annotate(
            name=F("team__team_name"), puzzle_name=F("puzzle__name")
        )
        .order_by("timestamp")
        .exclude(team__is_hidden=True)
    ):
        writer.writerow(
            [
                ans.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                ans.name,
                ans.puzzle_name,
                ans.answer,
                "F" if ans.used_free_answer else ("Y" if ans.correct else "N"),
            ]
        )
    return response


@require_GET
@restrict_access()
def hint_csv(request):
    response = HttpResponse(content_type="text/csv")
    fname = "tph_hintlog_{}.csv".format(request.context.now.strftime("%Y%m%dT%H%M%S"))
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(fname)
    writer = csv.writer(response)
    for hint in Hint.objects.annotate(
        name=F("team__team__name"),
        puzzle_name=F("puzzle__name"),
        answered_datetime=F("response__timestamp"),
    ).order_by("timestamp"):
        writer.writerow(
            [
                hint.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                None
                if hint.answered_datetime is None
                else (hint.answered_datetime.strftime("%Y-%m-%d %H:%M:%S")),
                hint.name,
                hint.puzzle_name,
                hint.response,
            ]
        )
    return response
