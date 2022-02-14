import csv
import datetime
import functools
import glob
import io
import json
import os
import subprocess
import tempfile
import zipfile
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

from django.conf import settings
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.http import require_GET, require_POST
from importlib_resources import files
from tph.utils import DEFAULT_USERNAME, staticfiles_storage

from puzzles.emailing import Batch, email_obj_for_batch
from puzzles.forms import CustomEmailForm, HiddenCustomEmailForm
from puzzles.hunt_config import (
    HUNT_CLOSE_TIME,
    HUNT_END_TIME,
    HUNT_START_TIME,
    INTRO_META_SLUGS,
    META_META_SLUG,
)
from puzzles.messaging import send_mail_wrapper, send_mass_mail_implementation
from puzzles.models import (
    AnswerSubmission,
    CustomPuzzleSubmission,
    Dimension,
    Email,
    EmailTemplate,
    Errata,
    Hint,
    Puzzle,
    PuzzleUnlock,
    Round,
    Team,
    TeamMember,
)
from puzzles.shortcuts import dispatch_shortcut
from puzzles.utils import get_all_emails
from puzzles.views.auth import restrict_access, validate_puzzle

ERRATA_EMAIL_TEMPLATE = "errata_email"


@require_GET
def get_hunt_info(request):
    def get_team_info_for_header():
        if request.user.is_authenticated and request.user.username != DEFAULT_USERNAME:
            team_info = None
            if request.context.team:
                team_info = {
                    "name": request.context.team.team_name,
                    "slug": request.context.team.slug,
                    "solves": len(request.context.team.solves),
                    "members": request.context.team.get_members(with_emails=True),
                }
                if request.context.is_hunt_complete:
                    team_info["stage"] = "finished"
                elif request.context.team.has_unlocked_final_meta(request.context):
                    team_info["stage"] = "meta"
                elif request.context.team.has_unlocked_main_round(request.context):
                    team_info["stage"] = "main"
            team_info = {
                "teamInfo": team_info,
                "superuser": request.context.is_superuser,
                "isImpersonate": hasattr(request.user, "is_impersonate")
                and request.user.is_impersonate,
            }
            team_info["errata"] = request.context.errata
            return team_info

        return None

    storyUnlocks = []

    for story in request.context.unlocks["story"]:
        puzzle = story.puzzle
        if not request.context.hunt_has_started:
            if puzzle and puzzle.slug:
                continue
        story_data = {
            "slug": story.slug,
            "text": story.text,
            "puzzleSlug": puzzle.slug if puzzle else None,
            # meta cards should show in modal
            "modal": not puzzle or puzzle.is_meta,
            "deep": story.deep,
        }
        image_url = story.get_image_url(Dimension.INTRO)
        if image_url:
            story_data["storyUrl"] = image_url
        team = request.context.team
        storyUnlocks.append(story_data)

    hunt_info = {
        "startTime": request.context.start_time,
        "secondsToStartTime": max(
            0, (request.context.start_time - timezone.now()).total_seconds()
        ),
        "endTime": request.context.end_time,
        "closeTime": request.context.close_time,
        "hintReleaseTime": request.context.hint_time,
        "storyUnlocks": storyUnlocks,
    }

    return JsonResponse(
        {
            "huntInfo": hunt_info,
            "userInfo": get_team_info_for_header(),
        }
    )


def sort_puzzle(puzzle):
    """Sorting for internal use only."""
    return (puzzle.is_meta, puzzle.deep, puzzle.slug)


@require_GET
@restrict_access(after_hunt_end=True)
def hunt_stats(request):
    total_teams = Team.objects.exclude(is_hidden=True).count()
    total_participants = TeamMember.objects.exclude(team__is_hidden=True).count()

    def is_forward_solve(puzzle, team_id):
        return puzzle.is_meta or all(
            solve_times[puzzle.id, team_id]
            <= solve_times[meta.id, team_id] - datetime.timedelta(minutes=5)
            for meta in puzzle.metas.all()
        )

    total_hints = 0
    hints_by_puzzle = defaultdict(int)
    hint_counts = defaultdict(int)
    # A hint is used if it has not been marked as REFUNDED or OBSOLETE. A
    # response requesting more information still uses the hint because teams
    # can reply to the thread.
    for hint in Hint.objects.filter(
        team__is_hidden=False,
        root_ancestor_request__isnull=True,
        is_request=True,
    ).exclude(
        status__in=(Hint.REFUNDED, Hint.OBSOLETE),
    ):
        total_hints += 1
        hints_by_puzzle[hint.puzzle_id] += 1
        if hint.status != Hint.OBSOLETE:
            hint_counts[hint.puzzle_id, hint.team_id] += 1

    total_guesses = 0
    total_solves = 0
    total_metas = 0
    guesses_by_puzzle = defaultdict(int)
    solves_by_puzzle = defaultdict(int)
    guess_teams = defaultdict(set)
    solve_teams = defaultdict(set)
    solve_times = defaultdict(lambda: HUNT_CLOSE_TIME)
    for submission in AnswerSubmission.objects.filter(
        used_free_answer=False,
        team__is_hidden=False,
        submitted_datetime__lt=HUNT_END_TIME,
    ):
        total_guesses += 1
        guesses_by_puzzle[submission.puzzle_id] += 1
        guess_teams[submission.puzzle_id].add(submission.team_id)
        if submission.is_correct:
            total_solves += 1
            solves_by_puzzle[submission.puzzle_id] += 1
            solve_teams[submission.puzzle_id].add(submission.team_id)
            solve_times[
                submission.puzzle_id, submission.team_id
            ] = submission.submitted_datetime

    data = []
    for puzzle in sorted(request.context.all_puzzles, key=sort_puzzle):
        if puzzle.is_meta:
            total_metas += solves_by_puzzle[puzzle.id]
        data.append(
            {
                "puzzle": puzzle,
                "numbers": [
                    solves_by_puzzle[puzzle.id],
                    guesses_by_puzzle[puzzle.id],
                    hints_by_puzzle[puzzle.id],
                    len(
                        [
                            1
                            for team_id in solve_teams[puzzle.id]
                            if is_forward_solve(puzzle, team_id)
                        ]
                    ),
                    len(
                        [
                            1
                            for team_id in solve_teams[puzzle.id]
                            if is_forward_solve(puzzle, team_id)
                            and hint_counts[puzzle.id, team_id] < 1
                        ]
                    ),
                    len(
                        [
                            1
                            for team_id in solve_teams[puzzle.id]
                            if is_forward_solve(puzzle, team_id)
                            and hint_counts[puzzle.id, team_id] == 1
                        ]
                    ),
                    len(
                        [
                            1
                            for team_id in solve_teams[puzzle.id]
                            if is_forward_solve(puzzle, team_id)
                            and hint_counts[puzzle.id, team_id] > 1
                        ]
                    ),
                    len(
                        [
                            1
                            for team_id in solve_teams[puzzle.id]
                            if not is_forward_solve(puzzle, team_id)
                        ]
                    ),
                    len(guess_teams[puzzle.id] - solve_teams[puzzle.id]),
                ],
            }
        )

    return render(
        request,
        "hunt_stats.html",
        {
            "total_teams": total_teams,
            "total_participants": total_participants,
            "total_hints": total_hints,
            "total_guesses": total_guesses,
            "total_solves": total_solves,
            "total_metas": total_metas,
            "data": data,
        },
    )


def get_puzzle_stats(puzzle, team):
    q = Q(team__is_hidden=False)
    if team:
        q |= Q(team__id=team.id)
    puzzle_submissions = (
        puzzle.answersubmission_set.filter(
            q, used_free_answer=False, submitted_datetime__lt=HUNT_END_TIME
        )
        .order_by("submitted_datetime")
        .select_related("team")
    )

    solve_time_map = {}
    total_guesses_map = defaultdict(int)
    solvers_map = {}
    unlock_time_map = {
        unlock.team_id: unlock.unlock_datetime
        for unlock in puzzle.puzzleunlock_set.all()
    }
    incorrect_guesses = Counter()
    guess_time_map = {}
    for submission in puzzle_submissions:
        team_id = submission.team_id
        total_guesses_map[team_id] += 1
        if submission.is_correct:
            solve_time_map[team_id] = submission.submitted_datetime
            solvers_map[team_id] = submission.team
        else:
            incorrect_guesses[submission.submitted_answer] += 1
            guess_time_map[
                team_id, submission.submitted_answer
            ] = submission.submitted_datetime
    wrong = "(?)"
    if incorrect_guesses:
        ((wrong, _),) = incorrect_guesses.most_common(1)
    solvers = [
        {
            "team": solver,
            "is_current": solver == team,
            "unlock_time": unlock_time_map.get(solver.id),
            "solve_time": solve_time_map[solver.id],
            "wrong_duration": (
                solve_time_map[solver.id] - guess_time_map[solver.id, wrong]
            ).total_seconds()
            if (solver.id, wrong) in guess_time_map
            else None,
            "open_duration": (
                solve_time_map[solver.id] - unlock_time_map[solver.id]
            ).total_seconds()
            if solver.id in unlock_time_map
            else None,
            "total_guesses": total_guesses_map[solver.id] - 1,
        }
        for solver in solvers_map.values()
    ]
    solvers.sort(key=lambda d: d["solve_time"])
    return {
        "solvers": solvers,
        "solves": len(solvers_map),
        "guesses": sum(total_guesses_map.values()),
        "answers_tried": incorrect_guesses.most_common(),
        "wrong": wrong,
    }


@require_GET
@validate_puzzle()
@restrict_access(after_hunt_end=True)
def stats_internal(request):
    stats_dict = get_puzzle_stats(request.context.puzzle, request.context.team)
    return render(request, "stats.html", stats_dict)


@require_GET
@restrict_access()
def histogram(request, slug):
    puzzle = Puzzle.objects.get(slug=slug)
    data = CustomPuzzleSubmission.histogram(puzzle).order_by("-counts")
    response = HttpResponse(content_type="text/csv")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="hunt_{slug}_histogram.csv"'
    fieldnames = ["submission", "counts"]
    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()
    for row in data:
        writer.writerow(row)
    return response


@require_GET
@restrict_access()
def histogram_by_team(request, slug):
    puzzle = Puzzle.objects.get(slug=slug)
    data = CustomPuzzleSubmission.histogram_by_team(puzzle).order_by("team", "-counts")
    # team is the PK, replace with team name
    pk_to_teamname = {}
    for team in Team.objects.all():
        pk_to_teamname[team.pk] = team.team_name
    rows = []
    for row in data:
        rows.append(row)
        rows[-1]["team"] = pk_to_teamname[rows[-1]["team"]]
    response = HttpResponse(content_type="text/csv")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="hunt_{slug}_histogram_by_team.csv"'
    fieldnames = ["submission", "team", "counts"]
    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()
    for row in data:
        writer.writerow(row)
    return response


@require_GET
@restrict_access()
def custom_puzzle_csv(request, slug):
    puzzle = Puzzle.objects.get(slug=slug)
    submissions = CustomPuzzleSubmission.objects.filter(
        puzzle=puzzle, submitted_datetime__lt=HUNT_END_TIME
    ).select_related()
    rows = []
    for guess in submissions:
        rows.append(
            {
                "team": guess.team.team_name,
                "subpuzzle": guess.subpuzzle,
                "submission": guess.submission,
                "count": guess.count,
                "first_submit": guess.submitted_datetime,
                "correct": guess.is_correct,
            }
        )
    rows.sort(key=lambda d: d["first_submit"])
    response = HttpResponse(content_type="text/csv")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="hunt_{slug}_submissions.csv"'
    fieldnames = ["team", "subpuzzle", "submission", "count", "first_submit", "correct"]
    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return response


@require_GET
@restrict_access()
def activity_csv(request):
    answers = (
        AnswerSubmission.objects.filter(
            submitted_datetime__lt=HUNT_END_TIME, team__is_hidden=False
        )
        .order_by("submitted_datetime")
        .select_related()
    )
    unlocks = (
        PuzzleUnlock.objects.filter(
            unlock_datetime__lt=HUNT_END_TIME, team__is_hidden=False
        )
        .order_by("unlock_datetime")
        .select_related()
    )

    csv_header = ["team", "event", "puzzle", "time", "submission", "correct"]
    date_pattern = "%Y-%m-%d %H:%M:%S"

    def process_guess(guess):
        out = []
        out.append(
            [
                guess.team.team_name,
                "guess",
                guess.puzzle.name,
                guess.submitted_datetime.strftime(date_pattern),
                guess.submitted_answer,
                guess.is_correct,
            ]
        )
        if guess.is_correct:
            out.append(
                [
                    guess.team.team_name,
                    "solve",
                    guess.puzzle.name,
                    guess.submitted_datetime.strftime(date_pattern),
                    "",
                    "",
                ]
            )
        return out

    def process_unlock(unlock):
        unlock_time = max(unlock.unlock_datetime, HUNT_START_TIME)
        return [
            [
                unlock.team.team_name,
                "unlock",
                unlock.puzzle.name,
                unlock_time.strftime(date_pattern),
                "",
                "",
            ]
        ]

    rows = []
    i = 0
    j = 0
    while i < len(answers) and j < len(unlocks):
        # gueses and solve events before unlocks if there's a tie
        if answers[i].submitted_datetime <= unlocks[j].unlock_datetime:
            rows.extend(process_guess(answers[i]))
            i += 1
        else:
            rows.extend(process_unlock(unlocks[j]))
            j += 1
    while i < len(answers):
        rows.extend(process_guess(answers[i]))
        i += 1
    while j < len(unlocks):
        rows.extend(process_unlock(unlocks[j]))
        j += 1

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="hunt_submit_log.csv"'
    writer = csv.writer(response)
    writer.writerow(csv_header)
    for row in rows:
        writer.writerow(row)
    return response


@require_GET
@restrict_access(after_hunt_end=True)
def public_activity_csv(request):
    # Downloads a static version of the CSV generated earlier.
    current_dir = files(".".join(__name__.split(".")[:-1]))
    with current_dir.joinpath("hunt_submit_log.csv").open() as f:
        content = f.read()
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="hunt_submit_log.csv"'
        return response


@require_GET
@validate_puzzle()
@restrict_access(after_hunt_end=True)
def stats_public(request):
    stats_dict = get_puzzle_stats(request.context.puzzle, request.context.team)
    # Change some objects to be a better fit for JSON
    solvers = []
    for solver in stats_dict["solvers"]:
        team = solver["team"]
        solver["team"] = team.team_name
        solver["slug"] = team.slug
        solvers.append(solver)
    stats_dict["solvers"] = solvers
    stats_dict["answers_tried"] = [
        {"wrong_answer": pair[0], "count": pair[1]}
        for pair in stats_dict["answers_tried"]
    ]
    # Manually populate puzzle data that's normally already in the Django call.
    stats_dict["puzzle_name"] = request.context.puzzle.name
    stats_dict["puzzle_answer"] = request.context.puzzle.normalized_answer
    return JsonResponse(stats_dict)


@require_GET
@restrict_access(after_hunt_end=True)
def finishers(request):
    teams = OrderedDict()
    solves_by_team = defaultdict(list)
    metas_by_team = defaultdict(list)
    unlock_times = defaultdict(lambda: HUNT_END_TIME)
    wrong_times = {}

    for submission in AnswerSubmission.objects.filter(
        puzzle__slug=META_META_SLUG,
        team__is_hidden=False,
        submitted_datetime__lt=HUNT_END_TIME,
    ).order_by("submitted_datetime"):
        if submission.is_correct:
            teams[submission.team_id] = None
        else:
            wrong_times[submission.team_id] = submission.submitted_datetime
    for unlock in PuzzleUnlock.objects.filter(
        team__id__in=teams, puzzle__slug=META_META_SLUG
    ):
        unlock_times[unlock.team_id] = unlock.unlock_datetime
    for solve in AnswerSubmission.objects.select_related().filter(
        team__id__in=teams,
        used_free_answer=False,
        is_correct=True,
        submitted_datetime__lt=HUNT_END_TIME,
    ):
        solves_by_team[solve.team_id].append(solve.submitted_datetime)
        if solve.puzzle.is_meta:
            metas_by_team[solve.team_id].append(solve.submitted_datetime)
        if solve.puzzle.slug == META_META_SLUG:
            teams[solve.team_id] = (solve.team, unlock_times[solve.team_id])

    data = []
    for team_id, (team, unlock) in teams.items():
        solves = [HUNT_START_TIME] + solves_by_team[team_id] + [HUNT_END_TIME]
        solves = [
            {
                "before": (solves[i - 1] - HUNT_START_TIME).total_seconds(),
                "after": (solves[i] - HUNT_START_TIME).total_seconds(),
            }
            for i in range(1, len(solves))
        ]
        metas = metas_by_team[team_id]
        data.append(
            {
                "team": team,
                "mm1_time": unlock,
                "mm2_time": metas[-1],
                "duration": (metas[-1] - unlock).total_seconds(),
                "wrong_duration": (metas[-1] - wrong_times[team_id]).total_seconds()
                if team_id in wrong_times
                else None,
                "hunt_length": (HUNT_END_TIME - HUNT_START_TIME).total_seconds(),
                "solves": solves,
                "metas": [(ts - HUNT_START_TIME).total_seconds() for ts in metas],
            }
        )
    if request.context.is_superuser:
        data.reverse()
    return render(request, "finishers.html", {"data": data})


@require_GET
@restrict_access(after_hunt_end=True)
def bigboard(request):
    puzzles = sorted(request.context.all_puzzles, key=sort_puzzle)
    puzzle_map = {}
    puzzle_metas = defaultdict(set)
    intro_meta_ids = set()
    meta_meta_id = None
    for puzzle in puzzles:
        puzzle_map[puzzle.id] = puzzle
        if puzzle.slug in INTRO_META_SLUGS:
            intro_meta_ids.add(puzzle.id)
        if puzzle.slug == META_META_SLUG:
            meta_meta_id = puzzle.id
        if not puzzle.is_meta:
            for meta in puzzle.metas.all():
                puzzle_metas[puzzle.id].add(meta.id)

    wrong_guesses_map = defaultdict(int)  # key (team, puzzle)
    wrong_guesses_by_team_map = defaultdict(int)  # key team
    solve_position_map = (
        dict()
    )  # key (team, puzzle); value n if team is nth to solve this puzzle
    solve_count_map = defaultdict(int)  # puzzle -> number of counts
    total_guess_map = defaultdict(int)  # puzzle -> number of guesses
    used_hints_map = defaultdict(int)  # (team, puzzle) -> number of hints
    used_hints_by_team_map = defaultdict(int)  # team -> number of hints
    used_hints_by_puzzle_map = defaultdict(int)  # puzzle -> number of hints
    solves_map = defaultdict(dict)  # team -> {puzzle id -> puzzle}
    intro_solves_map = defaultdict(int)  # team -> number of puzzle solves
    main_solves_map = defaultdict(int)  # team -> number of puzzle solves
    meta_solves_map = defaultdict(int)  # team -> number of meta solves
    solve_time_map = defaultdict(dict)  # team -> {puzzle id -> solve time}
    during_hunt_solve_time_map = defaultdict(dict)  # team -> {puzzle id -> solve time}
    free_answer_map = defaultdict(set)  # team -> {puzzle id}
    free_answer_by_puzzle_map = defaultdict(int)  # puzzle -> number of free answers

    for team_id, puzzle_id, used_free_answer, submitted_datetime in (
        AnswerSubmission.objects.filter(team__is_hidden=False, is_correct=True)
        .order_by("submitted_datetime")
        .values_list("team_id", "puzzle_id", "used_free_answer", "submitted_datetime")
    ):
        total_guess_map[puzzle_id] += 1
        if used_free_answer:
            free_answer_map[team_id].add(puzzle_id)
            free_answer_by_puzzle_map[puzzle_id] += 1
        else:
            solve_count_map[puzzle_id] += 1
            solve_position_map[(team_id, puzzle_id)] = solve_count_map[puzzle_id]
            solve_time_map[team_id][puzzle_id] = submitted_datetime
            if submitted_datetime < HUNT_END_TIME:
                during_hunt_solve_time_map[team_id][puzzle_id] = submitted_datetime
        solves_map[team_id][puzzle_id] = puzzle_map[puzzle_id]
        if puzzle_id not in puzzle_metas:
            meta_solves_map[team_id] += 1
        elif len(intro_meta_ids & puzzle_metas[puzzle_id]) >= 1:
            intro_solves_map[team_id] += 1
        else:
            main_solves_map[team_id] += 1

    for aggregate in (
        AnswerSubmission.objects.filter(team__is_hidden=False, is_correct=False)
        .values("team_id", "puzzle_id")
        .annotate(count=Count("*"))
    ):
        team_id = aggregate["team_id"]
        puzzle_id = aggregate["puzzle_id"]
        total_guess_map[puzzle_id] += aggregate["count"]
        wrong_guesses_map[(team_id, puzzle_id)] += aggregate["count"]
        wrong_guesses_by_team_map[team_id] += aggregate["count"]

    for aggregate in (
        Hint.objects.filter(
            is_request=True,
            root_ancestor_request__isnull=True,
            status=Hint.ANSWERED,
        )
        .values("team_id", "puzzle_id")
        .annotate(count=Count("*"))
    ):
        team_id = aggregate["team_id"]
        puzzle_id = aggregate["puzzle_id"]
        used_hints_map[(team_id, puzzle_id)] += aggregate["count"]
        used_hints_by_team_map[team_id] += aggregate["count"]
        used_hints_by_puzzle_map[puzzle_id] += aggregate["count"]

    # Reproduce Team.leaderboard behavior for ignoring solves after hunt end,
    # but not _teams_ created after hunt end. They'll just all be at the bottom.
    leaderboard = sorted(
        Team.objects.filter(is_hidden=False),
        key=lambda team: (
            during_hunt_solve_time_map[team.id].get(meta_meta_id, HUNT_END_TIME),
            -len(during_hunt_solve_time_map[team.id]),
            team.last_solve_time or team.creation_time,
        ),
    )
    limit = request.META.get("QUERY_STRING", "")
    limit = int(limit) if limit.isdigit() else 0
    if limit:
        leaderboard = leaderboard[:limit]
    unlocks = set(PuzzleUnlock.objects.values_list("team_id", "puzzle_id"))
    unlock_count_map = defaultdict(int)

    def classes_of(team_id, puzzle_id):
        unlocked = (team_id, puzzle_id) in unlocks
        if unlocked:
            unlock_count_map[puzzle_id] += 1
        solve_time = solve_time_map[team_id].get(puzzle_id)
        if puzzle_id in free_answer_map[team_id]:
            yield "F"  # free answer
        elif solve_time:
            yield "S"  # solved
        elif wrong_guesses_map.get((team_id, puzzle_id)):
            yield "W"  # wrong
        elif unlocked:
            yield "U"  # unlocked
        if used_hints_map.get((team_id, puzzle_id)):
            yield "H"  # hinted
        if solve_time and solve_time > HUNT_END_TIME:
            yield "P"  # post-hunt solve
        if solve_time and puzzle_metas.get(puzzle_id):
            metas_before = 0
            metas_after = 0
            for meta_id in puzzle_metas[puzzle_id]:
                meta_time = solve_time_map[team_id].get(meta_id)
                if meta_time and solve_time > meta_time - datetime.timedelta(minutes=5):
                    metas_before += 1
                else:
                    metas_after += 1
            if metas_after == 0:
                yield "B"  # backsolved from all metas
            elif metas_before != 0:
                yield "b"  # backsolved from some metas

    board = []
    for team in leaderboard:
        team.solves = solves_map[team.id]
        board.append(
            {
                "team": team,
                "last_solve_time": max(
                    [team.creation_time, *solve_time_map[team.id].values()]
                ),
                "total_solves": len(solve_time_map[team.id]),
                "free_solves": len(free_answer_map[team.id]),
                "wrong_guesses": wrong_guesses_by_team_map[team.id],
                "used_hints": used_hints_by_team_map[team.id],
                "total_hints": team.num_hints_total,
                "finished": solve_position_map.get((team.id, meta_meta_id)),
                # "deep": team.display_deep,
                "intro_solves": intro_solves_map[team.id],
                "main_solves": main_solves_map[team.id],
                "meta_solves": meta_solves_map[team.id],
                "entries": [
                    {
                        "wrong_guesses": wrong_guesses_map[(team.id, puzzle.id)],
                        "solve_position": solve_position_map.get((team.id, puzzle.id)),
                        "hints": used_hints_map[(team.id, puzzle.id)],
                        "cls": " ".join(classes_of(team.id, puzzle.id)),
                    }
                    for puzzle in puzzles
                ],
            }
        )

    annotated_puzzles = [
        {
            "puzzle": puzzle,
            "solves": solve_count_map[puzzle.id],
            "free_solves": free_answer_by_puzzle_map[puzzle.id],
            "total_guesses": total_guess_map[puzzle.id],
            "total_unlocks": unlock_count_map[puzzle.id],
            "hints": used_hints_by_puzzle_map[puzzle.id],
        }
        for puzzle in puzzles
    ]

    return render(
        request,
        "bigboard.html",
        {
            "board": board,
            "puzzles": annotated_puzzles,
        },
    )


@require_POST
@restrict_access()
def shortcuts(request):
    response = HttpResponse(content_type="text/html")
    try:
        dispatch_shortcut(request)
    except Exception as e:
        response.write(
            "<script>top.toastr.error(%s)</script>"
            % (json.dumps("<br>".join(escape(str(part)) for part in e.args)))
        )
    else:
        response.write("<script>top.location.reload()</script>")
    return response


def robots(request):
    response = HttpResponse(content_type="text/plain")
    response.write("User-agent: *\nDisallow: /\n")
    return response


@restrict_access()
def approve_profile_pic(request, user_name):
    team = Team.objects.get(user__username=user_name)
    if request.method == "POST":
        if "no" in request.POST:
            team.profile_pic.delete()
            team.profile_pic_approved = False
        elif "yes" in request.POST:
            team.profile_pic_approved = True
        team.save()
    if team.profile_pic:
        profile_pic = os.path.join(settings.MEDIA_URL, team.profile_pic.name)
    else:
        profile_pic = ""
    return render(
        request,
        "approve_picture.html",
        {
            "team_name": team.team_name,
            "picture": profile_pic,
            "approved": team.profile_pic_approved,
        },
    )


@restrict_access()
def internal_home(request):
    return render(request, "internal_home.html")


@restrict_access()
def internal_advance_team(request, user_name):
    team = Team.objects.get(user__username=user_name)

    SOLVES = {
        "hunt_start": [],
    }
    # FIXME: populate SOLVES with correct puzzle slugs.
    SOLVES["intro_meta_unlocked"] = SOLVES["hunt_start"] + []
    SOLVES["intro_meta_solved"] = SOLVES["intro_meta_unlocked"] + INTRO_META_SLUGS

    setting = None
    if request.method == "POST":
        # Wipe all submission, story, and puzzle unlocks
        setting = list(request.POST.keys())[0]
        # if key is bad, this will error before the deletes trigger
        solves_to_set = SOLVES[setting]
        # We rely on our existing deep system to propagate unlocks, and only set
        # solves, but we still need to clear up any prior unlocks.
        team.answersubmission_set.all().delete()
        team.storycardunlock_set.all().delete()
        team.puzzleunlock_set.all().delete()
        puzzles = Puzzle.objects.filter(slug__in=solves_to_set)
        for puzzle in puzzles:
            PuzzleUnlock(team=team, puzzle=puzzle).save()
            AnswerSubmission(
                team=team,
                puzzle=puzzle,
                submitted_answer="fakeanswersetbyinternaltool",
                is_correct=True,
                used_free_answer=False,
            ).save()

    return render(
        request,
        "team_progress_advance.html",
        {
            "team_name": team.team_name,
            "setting": setting,
        },
    )


@require_GET
@restrict_access()
def internal_errata(request):
    errata = Errata.objects.all().order_by("creation_time")
    return render(request, "errata_list.html", {"errata": errata})


@restrict_access()
def emails_for_errata(request, errata_pk):
    errata = Errata.objects.get(pk=errata_pk)
    puzzle = errata.puzzle
    team_and_emails = get_all_emails(unlocked_puzzle=puzzle)
    if request.method == "POST":
        # We're sending the emails.
        # Send 1 email per team.
        for team, emails in team_and_emails:
            send_mail_wrapper(
                f"Erratum issued for {puzzle.name}",
                ERRATA_EMAIL_TEMPLATE,
                {"errata": errata},
                emails,
            )
        # Redirect to a confirmation page (avoid double-sends if page refreshed.)
        return redirect("errata-email-confirm")
        # Redirect to confirmation page.
    email_template = ERRATA_EMAIL_TEMPLATE + ".html"
    email_string = render_to_string(email_template, context={"errata": errata})
    return render(
        request,
        "email_list.html",
        {"emails": team_and_emails, "email_string": email_string, "errata": errata},
    )


@require_GET
@restrict_access()
def email_confirm(request):
    return render(request, "email_confirm.html")


@require_GET
@restrict_access()
def all_emails(request):
    team_and_emails = get_all_emails()
    emails = []
    for _, addrs in team_and_emails:
        emails.extend(addrs)
    email_chunks = []
    for i in range(0, len(emails), 80):
        email_chunks.append(emails[i : i + 80])
    return render(request, "all_emails.html", {"email_chunks": email_chunks})


@require_GET
@restrict_access(after_hunt_end=True)
def all_pictures(request):
    teams = Team.leaderboard(request.context.team)
    has_pics = [team for team in teams if team["has_pic"]]
    # TODO something less awful to get sorted team objects instead of sorted json
    # don't want to touch leaderboard since it retrieves content shown to client.
    team_objs = Team.objects.filter(user_id__in=[team["user_id"] for team in has_pics])
    order = dict((team["user_id"], i) for i, team in enumerate(has_pics))
    sorted_teams = [None] * len(has_pics)
    for team in team_objs:
        sorted_teams[order[team.user_id]] = team

    profile_pics = []
    victory_pics = []
    for team in sorted_teams:
        profile_pics.append(os.path.join(settings.MEDIA_URL, team.profile_pic.name))
        victory_pics.append(
            ""
            if not team.profile_pic_victory.name
            else os.path.join(settings.MEDIA_URL, team.profile_pic_victory.name)
        )

    return render(
        request,
        "all_pictures.html",
        {"teams_with_pics": zip(sorted_teams, profile_pics, victory_pics)},
    )


@require_GET
@restrict_access()
def email_main(request):
    return render(request, "email_main.html")


def handler404(request, exception):
    # Redirect to nextjs
    return redirect("/404")


@restrict_access()
def custom_email(request):
    subject = ""
    shown_html = ""
    shown_txt = ""
    if request.POST:
        if request.POST["action"] == "html2text":
            form = CustomEmailForm(request.POST)
            if form.is_valid():
                data = dict(form.cleaned_data)
                data["plaintext_content"] = Email.html2text(
                    form["html_content"].value()
                )
                form = CustomEmailForm(data)
        else:
            form = HiddenCustomEmailForm(request.POST)

            if not form.is_valid():
                errors = form.errors
                form = CustomEmailForm(request.POST)
                form._errors = errors
            else:
                kwargs = {}
                kwargs["subject"] = form["subject"].value()
                kwargs["plaintxt"] = form["plaintext_content"].value()
                kwargs["html"] = form["html_content"].value()
                kwargs["context"] = {}

                if request.POST["action"] == "html2text":
                    form.data["plaintext_content"] = Email.html2text(kwargs["html"])
                elif request.POST["action"] == "showdraft":
                    # Show email we're about to send, then create a form with hidden
                    # fields set to the same value so that we can carry them through
                    # the next POST request. This is just the worst hack.
                    template_obj = send_mass_mail_implementation(**kwargs, dry_run=True)
                    message_id = (
                        f"messageid-to-be-computed@{settings.EMAIL_USER_DOMAIN}"
                    )
                    batch = Batch(
                        user=None, team=None, address_index=None, addresses=[]
                    )
                    email_obj = email_obj_for_batch(
                        template_obj, batch, message_id=message_id
                    )
                    email_message = email_obj.parse()
                    subject = kwargs["subject"]
                    shown_txt = email_message.get_body("plain").get_content()
                    shown_html = email_message.get_body("html").get_content()
                elif request.POST["action"] == "sendemail":
                    try:
                        template_obj = send_mass_mail_implementation(
                            **kwargs, dry_run=False
                        )
                    except Exception as e:
                        subject = (
                            f"Error in parsing POST request, should not happen: {e}"
                        )
                    else:
                        return render(request, "email_confirm.html")
                else:
                    subject = "Error in parsing POST request, should not happen."
    else:
        form = CustomEmailForm()
    return render(
        request,
        "custom_email.html",
        {
            "form": form,
            "subject": subject,
            "shown_html": shown_html,
            "shown_txt": shown_txt,
        },
    )


@require_GET
def clipboard(request):
    return render(request, "clipboard.html")


@functools.lru_cache(maxsize=1)
def _get_server_zip():
    server_dir = Path(__file__).parents[2]
    fileobj = io.BytesIO()
    with zipfile.ZipFile(fileobj, mode="w", compression=zipfile.ZIP_DEFLATED) as zipf:
        # store resource files
        for parent, dirs, filenames in os.walk(server_dir):
            for filename in filenames:
                path = os.path.join(parent, filename)
                relpath = os.path.relpath(path, server_dir)
                if any(
                    (
                        relpath.startswith("fixtures/"),
                        relpath.startswith("puzzles/migrations"),
                        relpath.startswith("puzzles/static"),
                        relpath.startswith("static/"),
                        relpath.startswith("tph/secrets.py"),
                        relpath.endswith(".npz"),
                        relpath.endswith(".pyc"),
                    )
                ):
                    continue
                zipf.write(path, relpath)

        # store staticfiles mapping
        staticfiles_bytes = json.dumps(_get_staticfiles()).encode()
        zipf.writestr("tph/staticfiles_mapping.json", staticfiles_bytes)

        # create and store sqlite database
        with tempfile.TemporaryDirectory() as tmp:
            fname = "db.sqlite3"
            subprocess.run(
                [
                    f"{server_dir}/create_pyodide_database.py",
                    f"{tmp}/{fname}",
                    f"{server_dir}/tph/fixtures/pyodide.yaml",
                    # TODO: test that this works with fixture directory.
                    *glob.glob(f"{server_dir}/tph/fixtures/puzzles/*.yaml"),
                ]
            )
            zipf.write(f"{tmp}/{fname}", fname)
    fileobj.seek(0)
    return fileobj.read()


@require_GET
@restrict_access(after_hunt_end=True)
def server_zip(request):
    return FileResponse(io.BytesIO(_get_server_zip()))


@functools.lru_cache(maxsize=1)
def _get_staticfiles():
    server_dir = Path(__file__).parents[2]
    static_directory = os.path.join(server_dir, "puzzles/static")
    staticmap = {}
    for parent, dirs, filenames in os.walk(static_directory):
        for filename in filenames:
            path = os.path.join(parent, filename)
            relpath = os.path.relpath(path, static_directory)
            staticmap[relpath] = staticfiles_storage.url(relpath)
    return staticmap


@require_POST
def reset_pyodide_db(request):
    if settings.IS_PYODIDE:
        from tph.utils import reset_db

        reset_db()
        return JsonResponse({})
    else:
        return JsonResponse({}, status=404)
