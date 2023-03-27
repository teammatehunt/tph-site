from collections import defaultdict

from django.contrib import messages
from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from spoilr.core.api.decorators import inject_puzzle
from spoilr.core.api.events import HuntEvent, dispatch
from spoilr.core.models import Puzzle, Team
from spoilr.hq.models import HqLog, TaskStatus
from spoilr.hq.util.decorators import hq
from spoilr.hq.util.redirect import redirect_with_message

from .forms import AnswerHintForm
from .models import Hint

MAX_HINT_LIMIT = 200


@hq()
def dashboard_view(request):
    hints = (
        Hint.objects.select_related("team", "puzzle")
        .prefetch_related("request_set")
        .defer("email__raw_content")
        .filter(is_request=True)
        .order_by("timestamp")
    )

    team = None
    puzzle = None
    open_only = False
    unclaimed_only = False
    limit = 10

    if request.GET.get("hint"):
        hints = hints.filter(id=request.GET["hint"])
    else:
        if request.GET.get("team"):
            team = get_object_or_404(Team, username=request.GET["team"])
            hints = hints.filter(team=team)

        if request.GET.get("puzzle"):
            puzzle = get_object_or_404(Puzzle, slug=request.GET["puzzle"])
            hints = hints.filter(puzzle=puzzle)

        if request.GET.get("open") == "1":
            open_only = True
            hints = Hint.all_requiring_response(hints)

        if request.GET.get("unclaimed") == "1":
            unclaimed_only = True
            hints = hints.filter(
                Q(tasks__handler=request.handler) | Q(tasks__handler=None)
            )

        if request.GET.get("limit"):
            limit = min([int(request.GET["limit"]), MAX_HINT_LIMIT])
            hints = hints[:limit]

    teams = Team.objects.values_list("username", flat=True).order_by("username")
    puzzles = Puzzle.objects.values_list("slug", flat=True).order_by("slug")

    hintdicts = []

    for hint in hints:
        hint_response = hint.get_or_populate_response()
        form = AnswerHintForm(instance=hint_response)
        form.cleaned_data = {}
        form.initial["hint_request_id"] = hint.id

        related_hints = Hint.objects.filter(team=hint.team, puzzle=hint.puzzle)
        thread = related_hints.filter(hint.original_request_filter()).order_by(
            "timestamp"
        )

        threadinfo = {"hints": [], "last_request": None, "last_response": None}
        for h in thread:
            threadinfo["hints"].append(h)
            threadinfo["last_request" if h.is_request else "last_response"] = h

        hintdicts.append(
            {
                "hint": hint,
                "thread": threadinfo,
                "form": form,
                "task": hint.task,
                "total_team_puzzle_hints": len(related_hints.filter(is_request=True)),
            }
        )

    return render(
        request,
        "spoilr/hints/dashboard.tmpl",
        {
            "hints": hintdicts,
            "limit": limit,
            "open_only": open_only,
            "unclaimed_only": unclaimed_only,
            "team": team.username if team else None,
            "puzzle": puzzle.slug if puzzle else None,
            "teams": teams,
            "puzzles": puzzles,
        },
    )


@require_POST
@hq(require_handler=True)
def respond_view(request):
    form = AnswerHintForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(f"Missing or invalid fields: {form.errors}")

    text_content = form.cleaned_data["text_content"]
    status = form.cleaned_data["status"]

    confirm = request.POST.get("confirm")
    if confirm.lower() != "respond":
        messages.warning(request, "Hint response was not confirmed.")
        return redirect_with_message(request, "spoilr.hints:dashboard")

    hint_request = (
        Hint.objects.select_related()
        .defer("email__raw_content")
        .filter(id=form.cleaned_data["hint_request_id"])
        .first()
    )
    if not hint_request:
        return HttpResponseBadRequest("Hint could not be found")

    task = hint_request.task
    if not task or task.handler != request.handler:
        messages.warning(request, "You are no longer handling this hint.")
        return redirect_with_message(request, "spoilr.hints:dashboard")

    if task.status == TaskStatus.DONE:
        messages.warning(
            request,
            "Hint is already done. If you'd like to update the hint, edit it in Admin.",
        )
        return redirect_with_message(request, "spoilr.hints:dashboard")

    hint_email = None
    if status in (Hint.OBSOLETE, Hint.ANSWERED) and not text_content:
        hint_response = None
        requests_to_update = hint_request.get_prior_requests_needing_response()
        if any(
            request.pk == hint_request.original_request_id
            for request in requests_to_update
        ):
            # should not immediately resolve a thread without responding
            return HttpResponseBadRequest(
                "A new hint came in while responding. Refresh and evaluate."
            )
    else:
        objs = hint_request.populate_response_and_update_requests(text_content, status)
        hint_response = objs["response"]
        requests_to_update = objs["requests"]
        hint_email = objs["response_email"]

    with transaction.atomic():
        task.status = TaskStatus.DONE
        task.snooze_time = None
        task.snooze_until = None
        task.save()

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
        request_obj_to_update = Hint.objects.filter(
            pk__in=[request.pk for request in requests_to_update]
        )
        request_obj_to_update.update(
            response=hint_response,
            **individual_status_updates,
        )
        Hint.clean_up_tasks(request_obj_to_update)

        HqLog.objects.create(
            handler=request.handler,
            event_type="hint-resolved",
            object_id=hint_request.puzzle.id,
            message=f"Resolved hint {hint_request} with status {status}",
        )

        def commit_action():
            dispatch(
                HuntEvent.HINT_RESOLVED,
                hint_request=hint_request,
                hint_response=hint_response,
                status=status,
                message=f"Resolved hint for {hint_request.team.name} about {hint_request.puzzle} with status {status}",
            )
            messages.success(request, "Hint saved successfully.")

        transaction.on_commit(commit_action)

    return redirect_with_message(request, "spoilr.hints:dashboard", "Hint resolved.")


@hq()
@inject_puzzle(error_if_inaccessible=True)
def canned_hints_view(request):
    """View for canned hints available to team."""
    puzzle = request.puzzle

    context = {}
    context["puzzle"] = puzzle
    context["canned_hints"] = get_canned_hints(puzzle)

    return render(request, "spoilr/hints/canned.tmpl", context)


@hq()
@inject_puzzle(error_if_inaccessible=True)
def history_view(request, **kwargs):
    """View for historical hints for the puzzle."""
    puzzle = request.puzzle
    team = get_object_or_404(Team, username=kwargs["team"])

    all_previous = Hint.objects.filter(puzzle=puzzle)

    hints_by_same_team = all_previous.filter(team_id=team.id).order_by("timestamp")
    threads_for_same_team = defaultdict(
        lambda: {"hints": [], "last_request": None, "last_response": None}
    )
    for hint in hints_by_same_team:
        threads_for_same_team[hint.original_request_id]["hints"].append(hint)
        threads_for_same_team[hint.original_request_id][
            "last_request" if hint.is_request else "last_response"
        ] = hint
    threads_for_same_team = sorted(
        threads_for_same_team.values(),
        key=lambda thread: thread["hints"][0].timestamp,
        reverse=True,
    )

    previous_by_others = (
        all_previous.filter(
            Q(status=Hint.ANSWERED) | Q(root_ancestor_request__status=Hint.ANSWERED),
            response__isnull=False,
        )
        .select_related("response")
        .exclude(team_id=team.id)
        .annotate(answered_datetime=F("response__timestamp"))
        .order_by("-answered_datetime")
    )

    context = {}
    context["puzzle"] = puzzle
    context["team"] = team
    context["threads_for_same_team"] = threads_for_same_team
    context["previous_by_others"] = previous_by_others

    return render(request, "spoilr/hints/history.tmpl", context)


def get_canned_hints(puzzle):
    """Returns canned hints from puzzle data."""
    return puzzle.canned_hints.all()
