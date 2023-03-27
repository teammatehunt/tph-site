import csv
import datetime
import functools
import glob
import io
import os
import subprocess
import tempfile
import zipfile
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.http import require_GET, require_POST
from spoilr.core.api.hunt import (
    get_site_close_time,
    get_site_end_time,
    get_site_launch_time,
    is_site_launched,
)
from spoilr.email.models import Email
from spoilr.email.utils import get_all_emails
from spoilr.hints.models import Hint
from spoilr.registration.models import TeamRegistrationInfo
from spoilr.utils import generate_url, json
from tph.utils import load_file, staticfiles_storage

from puzzles.assets import get_hashed_url
from puzzles.emailing import Batch, email_obj_for_batch
from puzzles.forms import CustomEmailForm, HiddenCustomEmailForm
from puzzles.hunt_config import DONE_SLUG
from puzzles.messaging import send_mass_mail_implementation
from puzzles.models import (
    CustomPuzzleSubmission,
    Puzzle,
    PuzzleAccess,
    PuzzleSubmission,
    Team,
)
from puzzles.rounds.utils import rounds_by_act
from puzzles.shortcuts import dispatch_shortcut
from puzzles.views.auth import restrict_access, validate_puzzle


def get_navbar_rounds(request, team):
    """Returns which rounds to display in the navbar, grouped by act."""
    visible_acts = rounds_by_act(team.unlocked_rounds())

    return [
        [
            {
                "act": puzzle_round.act,
                "slug": puzzle_round.slug,
                "name": puzzle_round.name,
                "url": puzzle_round.url,
            }
            for puzzle_round in act
        ]
        for act in visible_acts
    ]


@require_GET
def get_hunt_info(request):
    def get_team_info_for_header():
        if request.user.is_authenticated:
            team_info = None
            team = request.context.team
            if team:
                team_info = {
                    "name": team.name,
                    "slug": team.slug,
                    "rounds": get_navbar_rounds(request, team),
                }
                # Serialize the team's hunt story progress.
                story_state = request.context.story_state
                team_info["state"] = story_state.value

            team_info = {
                "teamInfo": team_info,
            }
            if request.context.is_superuser:
                team_info["superuser"] = True
            elif team.is_public:
                team_info["public"] = True
            if hasattr(request.user, "is_impersonate") and request.user.is_impersonate:
                team_info["isImpersonate"] = True

            return team_info

        return None

    hunt_info = {
        "startTime": request.context.start_time,
        "secondsToStartTime": max(
            0, (request.context.start_time - timezone.now()).total_seconds()
        ),
        "endTime": get_site_end_time(),
        "closeTime": get_site_close_time(),
        "hintReleaseTime": request.context.hint_time,
    }
    if request.context.site:
        hunt_info["site"] = request.context.site

    return JsonResponse(
        {
            "huntInfo": hunt_info,
            "userInfo": get_team_info_for_header(),
        }
    )


@require_GET
def get_hunt_site(request):
    # For use in the registration page to redirect to the registration homepage until start time
    if not is_site_launched():
        return JsonResponse({"huntSite": "/"})
    else:
        return JsonResponse({"huntSite": generate_url("hunt", "/")})


def sort_puzzle(puzzle):
    """Sorting for internal use only."""
    return (puzzle.is_meta, puzzle.deep, puzzle.slug)


@require_GET
@restrict_access(after_hunt_end=True)
def hunt_stats(request):
    total_teams = Team.objects.exclude(is_hidden=True).count()
    # NB: this may not be entirely accurate if some teams didn't fill out this field.
    total_participants = TeamRegistrationInfo.objects.aggregate(Sum("tm_total"))[
        "tm_total__sum"
    ]

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
        team__team__is_hidden=False,
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
    solve_times = defaultdict(lambda: get_site_close_time())
    for submission in PuzzleSubmission.objects.filter(
        used_free_answer=False,
        team__team__is_hidden=False,
        timestamp__lt=get_site_end_time(),
    ):
        total_guesses += 1
        guesses_by_puzzle[submission.puzzle_id] += 1
        guess_teams[submission.puzzle_id].add(submission.team_id)
        if submission.correct:
            total_solves += 1
            solves_by_puzzle[submission.puzzle_id] += 1
            solve_teams[submission.puzzle_id].add(submission.team_id)
            solve_times[submission.puzzle_id, submission.team_id] = submission.timestamp

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
    q = Q(team__team__is_hidden=False)
    if team:
        q |= Q(team__id=team.id)
    puzzle_submissions = (
        puzzle.puzzlesubmission_set.filter(q, timestamp__lt=get_site_end_time())
        .order_by("timestamp")
        .select_related("team", "puzzlesubmission")
    )

    solve_time_map = {}
    total_guesses_map = defaultdict(int)
    solvers_map = {}
    free_answer_map = defaultdict(lambda: False)
    free_solves = 0
    unlock_time_map = {
        unlock.team_id: unlock.timestamp for unlock in puzzle.puzzleaccess_set.all()
    }
    incorrect_guesses = Counter()
    guess_time_map = {}
    for submission in puzzle_submissions:
        team_id = submission.team_id
        total_guesses_map[team_id] += 1
        if submission.correct:
            solve_time_map[team_id] = submission.timestamp
            solvers_map[team_id] = submission.team
            if submission.puzzlesubmission.used_free_answer:
                free_answer_map[team_id] = True
                total_guesses_map[team_id] -= 1
                free_solves += 1
        else:
            incorrect_guesses[submission.answer] += 1
            guess_time_map[team_id, submission.answer] = submission.timestamp
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
            "total_guesses": max(total_guesses_map[solver.id] - 1, 0),
            "used_free_answer": free_answer_map[solver.id],
        }
        for solver in solvers_map.values()
    ]
    solvers.sort(key=lambda d: d["solve_time"])
    return {
        "solvers": solvers,
        "solves": len(solvers_map),
        "free_solves": free_solves,
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
    ] = f'attachment; filename="teammate_hunt_{slug}_histogram.csv"'
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
        pk_to_teamname[team.pk] = team.name
    rows = []
    for row in data:
        rows.append(row)
        rows[-1]["team"] = pk_to_teamname[rows[-1]["team"]]
    response = HttpResponse(content_type="text/csv")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="teammate_hunt_{slug}_histogram_by_team.csv"'
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
        puzzle=puzzle, timestamp__lt=get_site_end_time()
    ).select_related()
    rows = []
    for guess in submissions:
        rows.append(
            {
                "team": guess.team.name,
                "minipuzzle": guess.minipuzzle,
                "submission": guess.submission,
                "count": guess.count,
                "first_submit": guess.timestamp,
                "correct": guess.correct,
            }
        )
    rows.sort(key=lambda d: d["first_submit"])
    response = HttpResponse(content_type="text/csv")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="teammate_hunt_{slug}_submissions.csv"'
    fieldnames = ["team", "subpuzzle", "submission", "count", "first_submit", "correct"]
    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return response


@require_GET
@restrict_access()
def activity_csv(request):
    END_TIME = get_site_end_time()
    answers = (
        PuzzleSubmission.objects.filter(timestamp__lt=END_TIME, team__is_hidden=False)
        .order_by("timestamp")
        .select_related()
    )
    unlocks = (
        PuzzleAccess.objects.filter(timestamp__lt=END_TIME, team__team__is_hidden=False)
        .order_by("timestamp")
        .select_related()
    )

    csv_header = ["team", "event", "puzzle", "time", "submission", "correct"]
    date_pattern = "%Y-%m-%d %H:%M:%S"

    def process_guess(guess):
        out = []
        out.append(
            [
                guess.team.name,
                "guess",
                guess.puzzle.name,
                guess.timestamp.strftime(date_pattern),
                guess.answer,
                guess.correct,
            ]
        )
        if guess.correct:
            out.append(
                [
                    guess.team.name,
                    "solve",
                    guess.puzzle.name,
                    guess.timestamp.strftime(date_pattern),
                    "",
                    "",
                ]
            )
        return out

    def process_unlock(unlock):
        unlock_time = max(unlock.timestamp, get_site_launch_time())
        return [
            [
                unlock.team.name,
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
        if answers[i].timestamp <= unlocks[j].timestamp:
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
    response[
        "Content-Disposition"
    ] = 'attachment; filename="teammate_hunt_submit_log.csv"'
    writer = csv.writer(response)
    writer.writerow(csv_header)
    for row in rows:
        writer.writerow(row)
    return response


@require_GET
@restrict_access(after_hunt_end=True)
def public_activity_csv(request):
    # Downloads a static version of the CSV generated earlier.
    with load_file(
        "views/teammate_hunt_submit_log.csv", base_module="puzzles"
    ).open() as f:
        content = f.read()
        response = HttpResponse(content, content_type="text/csv")
        response[
            "Content-Disposition"
        ] = 'attachment; filename="teammate_hunt_submit_log.csv"'
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
        solver["team"] = team.name
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
    stats_dict["puzzle_url"] = request.context.puzzle.url
    return JsonResponse(stats_dict)


@require_GET
@restrict_access(after_hunt_end=True)
def finishers(request):
    END_TIME = get_site_end_time()
    teams = OrderedDict()
    solves_by_team = defaultdict(list)
    metas_by_team = defaultdict(list)
    unlock_times = defaultdict(lambda: END_TIME)
    wrong_times = {}

    for submission in PuzzleSubmission.objects.filter(
        puzzle___slug=DONE_SLUG,
        team__is_hidden=False,
        timestamp__lt=END_TIME,
    ).order_by("timestamp"):
        if submission.correct:
            teams[submission.team_id] = None
        else:
            wrong_times[submission.team_id] = submission.timestamp
    for unlock in PuzzleAccess.objects.filter(
        team__id__in=teams, puzzle___slug=DONE_SLUG
    ):
        unlock_times[unlock.team_id] = unlock.timestamp
    for solve in PuzzleSubmission.objects.select_related().filter(
        team__id__in=teams,
        used_free_answer=False,
        correct=True,
        timestamp__lt=END_TIME,
    ):
        solves_by_team[solve.team_id].append(solve.timestamp)
        if solve.puzzle.is_meta:
            metas_by_team[solve.team_id].append(solve.timestamp)
        if solve.puzzle.slug == DONE_SLUG:
            teams[solve.team_id] = (solve.team, unlock_times[solve.team_id])

    data = []
    START_TIME = get_site_launch_time()
    START_TIME = get_site_end_time()
    for team_id, (team, unlock) in teams.items():
        solves = [START_TIME] + solves_by_team[team_id] + [END_TIME]
        solves = [
            {
                "before": (solves[i - 1] - START_TIME).total_seconds(),
                "after": (solves[i] - START_TIME).total_seconds(),
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
                "hunt_length": (END_TIME - START_TIME).total_seconds(),
                "solves": solves,
                "metas": [(ts - START_TIME).total_seconds() for ts in metas],
            }
        )
    if request.context.is_superuser:
        data.reverse()
    return render(request, "finishers.html", {"data": data})


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
            "name": team.name,
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
    # FIXME(update): populate SOLVES with correct puzzle slugs.
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
        team.puzzlesubmission_set.all().delete()
        team.storycardaccess_set.all().delete()
        team.puzzleaccess_set.all().delete()
        puzzles = Puzzle.objects.filter(slug__in=solves_to_set)
        for puzzle in puzzles:
            PuzzleAccess(team=team.spoilr_team, puzzle=puzzle.spoilr_puzzle).save()
            PuzzleSubmission(
                team=team.spoilr_team,
                puzzle=puzzle.spoilr_puzzle,
                answer="fakeanswersetbyinternaltool",
                correct=True,
                used_free_answer=False,
            ).save()

    return render(
        request,
        "team_progress_advance.html",
        {
            "name": team.name,
            "setting": setting,
        },
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
@restrict_access()
def email_main(request):
    return render(request, "email_main.html")


def handler404(request, exception):
    # Redirect to nextjs
    return redirect("/404")


# This code is not used - was part of TPH email code, but going through spoilr now instead.
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

        # store media files mapping
        if os.path.exists(settings.ASSET_MAPPING):
            zipf.write(settings.ASSET_MAPPING, "tph/media_mapping.yaml")

        # create and store sqlite database
        with tempfile.TemporaryDirectory() as tmp:
            fname = "db.sqlite3"
            subprocess.run(
                [
                    f"{server_dir}/create_pyodide_database.py",
                    f"{tmp}/{fname}",
                    f"{server_dir}/tph/fixtures/posthunt/team.yaml",
                    f"{server_dir}/tph/fixtures/posthunt/dump.yaml",
                    f"{server_dir}/tph/fixtures/posthunt/access.yaml",
                ],
                check=True,
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
