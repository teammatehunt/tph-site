import csv
import datetime
import pytz

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

from spoilr.core.models import *
from spoilr.hints.models import Hint
from spoilr.hq.util.decorators import hq


@hq()
def system_log_view(request):
    entries = SystemLog.objects.select_related("team").order_by("-id")

    team = None
    if request.GET.get("team"):
        team = get_object_or_404(Team, username=request.GET["team"])
        entries = entries.filter(team=team)

    puzzle = None
    if request.GET.get("puzzle"):
        puzzle = get_object_or_404(Puzzle, slug=request.GET["puzzle"])
        entries = entries.filter(object_id=puzzle.slug)

    search = None
    if request.GET.get("search"):
        search = request.GET["search"]
        entries = entries.filter(
            Q(message__icontains=search)
            | Q(object_id__icontains=search)
            | Q(event_type__icontains=search)
        )

    limit = 200
    if request.GET.get("limit"):
        limit = min([int(request.GET["limit"]), 5000])
    entries = entries[: int(limit)]

    teams = Team.objects.values_list("username", flat=True).order_by("username")
    puzzles = Puzzle.objects.values_list("slug", flat=True).order_by("slug")

    return HttpResponse(
        render(
            request,
            "hq/log.html",
            {
                "limit": limit,
                "team": team.username if team else None,
                "puzzle": puzzle.slug if puzzle else None,
                "search": search or "",
                "entries": entries,
                "teams": teams,
                "puzzles": puzzles,
            },
        )
    )


@hq()
def system_log_csv_export(request):
    # Filter out system log events that we should't publicize i.e. email responses.
    # And also limit to events up until hunt close
    entries = SystemLog.objects.select_related("team").order_by("timestamp")
    bad_types = [
        "email-replied",
        "hint-resolved",
        "task-unsnoozed",
        "update-sent",
        "interaction-accomplished",
        "interaction-released",
    ]
    # The team types are "internal", "public", None.
    entries = (
        entries.exclude(event_type__in=bad_types)
        .exclude(team=None)
        .filter(team__type=None)
    )
    # FIXME(update): Update this logic for your hunt
    # free_answers = ??? .order_by("timestamp")
    response = HttpResponse(content_type="text/csv")
    fname = "tph_guesslog_{}.csv".format(
        datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    )
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(fname)
    fieldnames = ["timestamp", "team", "event_type", "object_id", "message"]
    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()
    datarows = []
    for entr in entries:
        data = {k: getattr(entr, k) for k in fieldnames}
        data["timestamp"] = data["timestamp"].astimezone(
            pytz.timezone("America/New_York")
        )
        data["team"] = data["team"].name
        datarows.append(data)
    # FIXME(update): Update this logic for your hunt
    # for free in free_answers:
    #     datarows.append(
    #         {
    #             "timestamp": free.timestamp.astimezone(
    #                 pytz.timezone("America/New_York")
    #             ),
    #             "team": free.team.name,
    #             "event_type": "used-free-answer",
    #             "object_id": free.puzzle.slug,
    #             "message": f"Used free answer on {free.puzzle.name}",
    #         }
    #     )
    datarows.sort(key=lambda row: row["timestamp"])
    for row in datarows:
        writer.writerow(row)
    return response


@hq()
def hint_log_view(request, limit):
    entries = (
        Hint.objects.select_related("team", "puzzle")
        .prefetch_related("tasks")
        .order_by("-id")
    )
    if limit:
        entries = entries[: int(limit)]
    else:
        entries = entries[: int(1000)]
    entries = [
        {
            "entry": entry,
            "task": entry.tasks.first(),
        }
        for entry in entries
    ]
    return HttpResponse(
        render(
            request,
            "hq/hint-log.html",
            {
                "limit": limit,
                "entries": entries,
            },
        )
    )
