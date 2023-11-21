import collections
import colorsys
import datetime
import random

from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render
from puzzles.assets import get_hashed_url
from spoilr.core.api.hunt import get_site_end_time, get_site_launch_time
from spoilr.core.models import Puzzle, PuzzleAccess, PuzzleSubmission, Team, TeamType
from spoilr.hints.models import Hint
from spoilr.hq.util.decorators import hq
from spoilr.utils import generate_url


def get_style_map():
    """Handle changing icon per puzzle in solve graph."""
    # This is turned into the right icon on the client side, since chart.js only
    # takes Image() elements in JS. MH-2023 specific.
    style_map = {}
    # FIXME(update): Update this logic for your hunt
    return style_map


def closest_hour(timestamp, start):
    # Actually more like the floor of the hour but whatever.
    hour = (timestamp - start).total_seconds() // (60 * 60)
    hour_as_unix = (start + datetime.timedelta(hours=hour)).timestamp() * 1000
    return hour_as_unix


@hq()
def solve_graph_view(request):
    # Prepare labels for per-hour histograms
    start = get_site_launch_time()
    end = get_site_end_time()
    hour_labels = []
    curr = start
    while curr < end:
        hour_labels.append(curr.timestamp() * 1000)
        curr += datetime.timedelta(hours=1)
    # Solve counts
    team_names_by_id = {
        team.id: truncate(team.name, 40)
        for team in Team.objects.exclude(type=TeamType.INTERNAL)
    }
    # Note this may not be defined for every team.
    team_sizes_by_id = {
        team.id: team.teamregistrationinfo.tm_total
        for team in Team.objects.exclude(type=TeamType.INTERNAL)
        .select_related("teamregistrationinfo")
        .exclude(teamregistrationinfo__tm_total=None)
        .filter(teamregistrationinfo__tm_total__gt=0)
    }
    puzzle_names_by_id = {puzzle.id: puzzle.name for puzzle in Puzzle.objects.all()}

    solve_counts_by_team = collections.defaultdict(int)
    solve_counts_time_series_by_team = collections.defaultdict(list)
    point_styles_by_team = collections.defaultdict(list)
    # To get free answer usage, query against PuzzleSubmission FIXME(update): Update this logic for your hunt
    all_puzzle_subs = (
        PuzzleSubmission.objects.select_related("team__team", "puzzle", "puzzle__round")
        .exclude(team__type=TeamType.INTERNAL)
        .exclude(team__type=TeamType.PUBLIC)
        .filter(
            # This might not be necessary / relies on tph code, but include anyways.
            team__team__is_hidden=False,
            team__team__is_prerelease_testsolver=False,
            timestamp__gte=start,
            timestamp__lte=end,
        )
        .order_by("timestamp")
    )
    # Drawn in order, draw most guesses last.
    guess_counts = (
        all_puzzle_subs.values("team_id")
        .annotate(guesses=Count("team_id"))
        .order_by("guesses")
    )
    guess_counts_by_id = {}
    for d in guess_counts:
        guess_counts_by_id[d["team_id"]] = d["guesses"]

    correct_puzzle_subs = all_puzzle_subs.filter(correct=True).values_list(
        "team_id",
        "puzzle_id",
        "puzzle__slug",
        "timestamp",
    )
    all_correct_subs = list(correct_puzzle_subs)
    all_correct_subs.sort(key=lambda info: info[3])  # solve-time

    free_answers_by_hour = collections.defaultdict(int)

    style_map = get_style_map()

    for team_id, puzzle_id, puzzle_slug, solved_time, used_free in all_correct_subs:
        solve_counts_by_team[team_id] += 1
        solved_time_as_unix = solved_time.timestamp() * 1000
        solve_counts_time_series_by_team[team_id].append(
            (solved_time_as_unix, solve_counts_by_team[team_id], puzzle_id)
        )
        point_styles_by_team[team_id].append(style_map.get(puzzle_slug, "circle"))
        if used_free:
            hour_as_unix = closest_hour(solved_time, start)
            free_answers_by_hour[hour_as_unix] += 1

    # Hint counts by hour
    hint_requests_by_hour = collections.defaultdict(int)
    hint_responses_by_hour = collections.defaultdict(int)
    contact_hq_requests_by_hour = collections.defaultdict(int)
    contact_hq_responses_by_hour = collections.defaultdict(int)

    # False = 0 True = 1
    hints_by_hour = [hint_responses_by_hour, hint_requests_by_hour]

    hints_requested = (
        Hint.objects.filter(timestamp__lte=end)
        .select_related("puzzle")
        .order_by("timestamp")
    )
    for hint in hints_requested:
        hour_as_unix = closest_hour(hint.timestamp, start)
        hints_by_hour[int(hint.is_request)][hour_as_unix] += 1

    # The drawing order is first one on top, draw the largest teams last.
    team_size_ids = team_sizes_by_id.keys() & solve_counts_by_team.keys()
    guess_count_ids = guess_counts_by_id.keys() & team_size_ids
    team_size_ids = sorted(team_size_ids, key=lambda k: team_sizes_by_id[k])
    guess_count_ids = sorted(guess_count_ids, key=lambda k: guess_counts_by_id[k])

    return render(
        request,
        "spoilr/progress/solves.tmpl",
        {
            "sites": {
                "hunt": generate_url("hunt", ""),
                "base_prefix": "/20xx" if settings.IS_POSTHUNT else "",
            },
            "hint_counts_for_chartjs": {
                "datasets": [
                    {
                        "label": "Requested",
                        "data": [
                            {"x": hour, "y": hint_requests_by_hour[hour]}
                            for hour in hour_labels
                        ],
                        "borderColor": "red",
                        "backgroundColor": "red",
                        "fill": False,
                    },
                    {
                        "label": "Answered",
                        "data": [
                            {"x": hour, "y": hint_responses_by_hour[hour]}
                            for hour in hour_labels
                        ],
                        "borderColor": "blue",
                        "backgroundColor": "blue",
                        "fill": False,
                    },
                ],
            },
            "contacthq_counts_for_chartjs": {
                "datasets": [
                    {
                        "label": "Requested",
                        "data": [
                            {"x": hour, "y": contact_hq_requests_by_hour[hour]}
                            for hour in hour_labels
                        ],
                        "borderColor": "red",
                        "backgroundColor": "red",
                        "fill": False,
                    },
                    {
                        "label": "Answered",
                        "data": [
                            {"x": hour, "y": contact_hq_responses_by_hour[hour]}
                            for hour in hour_labels
                        ],
                        "borderColor": "blue",
                        "backgroundColor": "blue",
                        "fill": False,
                    },
                ],
            },
            "freeanswer_counts_for_chartjs": {
                "datasets": [
                    {
                        "label": "Redeemed",
                        "data": [
                            {"x": hour, "y": free_answers_by_hour[hour]}
                            for hour in hour_labels
                        ],
                        "borderColor": "red",
                        "backgroundColor": "red",
                        "fill": False,
                    },
                ],
            },
            "solve_counts_for_chartjs": {
                "datasets": [
                    {
                        "label": team_names_by_id[team_id],
                        "data": [
                            {
                                "x": solve_count[0],
                                "y": solve_count[1],
                            }
                            for solve_count in solve_counts
                        ],
                        "pointStyle": point_styles_by_team[team_id],
                        "borderColor": team_id_to_line_color(team_id),
                        "backgroundColor": team_id_to_line_color(team_id),
                        "fill": False,
                    }
                    for team_id, solve_counts in solve_counts_time_series_by_team.items()
                ],
                "pointLabels": [
                    [
                        f"{team_names_by_id[team_id]} solved {puzzle_names_by_id[solve_count[2]]}, "
                        f'{solve_count[1]} {"puzzle" if solve_count[1] == 1 else "puzzles"} solved'
                        for solve_count in solve_counts
                    ]
                    for team_id, solve_counts in solve_counts_time_series_by_team.items()
                ],
            },
            "solves_by_size_for_chartjs": {
                # The drawing order is first one on top, draw the largest teams last.
                "datasets": [
                    {
                        "label": team_names_by_id[team_id],
                        "data": [
                            {
                                "x": team_sizes_by_id[team_id],
                                "y": solve_counts_by_team[team_id],
                                "r": 10 + team_sizes_by_id[team_id] / 5.0,
                            }
                        ],
                        "backgroundColor": team_id_to_line_color(team_id),
                    }
                    for team_id in team_size_ids
                ],
            },
            "solves_by_guesses_for_chartjs": {
                # The drawing order is first one on top, draw the largest teams last.
                "datasets": [
                    {
                        "label": team_names_by_id[team_id],
                        "data": [
                            {
                                "x": guess_counts_by_id[team_id],
                                "y": solve_counts_by_team[team_id],
                                "r": 10 + team_sizes_by_id[team_id] / 5.0,
                            }
                        ],
                        "backgroundColor": team_id_to_line_color(team_id),
                    }
                    for team_id in guess_count_ids
                ],
            },
            # Not the true max - whatever makes the plot look nice.
            "max_solves": 180,
        },
    )


# Access raw data via JSON so that we can experiment with different uses
# more flexibly.
@hq()
def solve_data_json_view(request):
    team_names_by_id = {
        team.id: truncate(team.name, 40)
        for team in Team.objects.exclude(type=TeamType.INTERNAL)
    }
    puzzle_names_by_id = {puzzle.id: puzzle.name for puzzle in Puzzle.objects.all()}

    solve_counts_by_team = collections.defaultdict(int)
    solve_counts_time_series_by_team = collections.defaultdict(list)
    puzzle_accesses = (
        PuzzleAccess.objects.exclude(team__type=TeamType.INTERNAL)
        .filter(solved=True, solved_time__isnull=False)
        .values_list("team_id", "puzzle_id", "solved_time")
        .order_by("solved_time")
    )

    for team_id, puzzle_id, solved_time in puzzle_accesses:
        solve_counts_by_team[team_id] += 1
        solved_time_as_unix = solved_time.timestamp() * 1000
        solve_counts_time_series_by_team[team_id].append(
            (solved_time_as_unix, solve_counts_by_team[team_id], puzzle_id)
        )

    return JsonResponse(
        {
            "data": [
                {
                    "team": team_names_by_id[team_id],
                    "solves": [
                        {
                            "puzzle": puzzle_names_by_id[solve_count[2]],
                            "timestamp": solve_count[0],
                            "solve_number": solve_count[1],
                        }
                        for solve_count in solve_counts
                    ],
                }
                for team_id, solve_counts in solve_counts_time_series_by_team.items()
            ]
        }
    )


def team_id_to_line_color(team_id):
    old_seed = random.random()
    random.seed(team_id)
    r, g, b = colorsys.hls_to_rgb(
        random.random(), random.random() * 0.5 + 0.25, random.random() * 0.5 + 0.3
    )
    random.seed(old_seed)

    return f"rgba({int(r * 255)}, {int(g * 255)}, {int(b * 255)}, 1)"


def truncate(name, length):
    if len(name) > length - 3:
        return name[: length - 3] + "..."
    return name
