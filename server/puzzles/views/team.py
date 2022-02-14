import os
from collections import defaultdict

from django.conf import settings
from django.contrib import messages
from django.forms import modelformset_factory
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from tph.utils import generate_url

from puzzles.forms import ProfilePictureForm, TeamEditForm, UnsubscribeEmailForm
from puzzles.hunt_config import (
    HUNT_CLOSE_TIME,
    HUNT_END_TIME,
    HUNT_START_TIME,
    TEAM_SIZE,
)
from puzzles.messaging import (
    dispatch_bad_profile_pic_alert,
    dispatch_general_alert,
    dispatch_profile_pic_alert,
)
from puzzles.models import BadEmailAddress, Email, Team, TeamMember
from puzzles.utils import login_required
from puzzles.views.auth import restrict_access


def get_profile_pic_url(request, team, victory=False):
    # This returns the URL, even if the picture isn't approved yet, because we
    # use this to decide whether to display an "under review" message or not.
    if victory or request.context.hunt_is_over:
        profile_pic = team.profile_pic_victory.name or team.profile_pic.name
    else:
        profile_pic = team.profile_pic.name
    if profile_pic:
        profile_pic = os.path.join(settings.MEDIA_URL, profile_pic)
    return profile_pic


def get_team_info(request, slug=None):
    user_team = request.context.team

    if slug:
        is_own_team = user_team is not None and user_team.slug == slug
        can_view_info = (
            is_own_team or request.context.is_superuser or request.context.hunt_is_over
        )
        team_query = Team.objects.filter(slug=slug)
        if not can_view_info:
            team_query = team_query.exclude(is_hidden=True)
        team = team_query.first()
    else:
        # If no team name provided, load the current team.
        is_own_team = True
        team = user_team
        can_view_info = True
        # Special case that only applies to /victory page
        # If the team can't be found, we only want to return the 200 when no
        # team name is provided.
        if not team and request.context.hunt_is_over:
            return JsonResponse({}, status=200)

    if not team:
        return JsonResponse({}, status=404)

    team_info = {
        "name": team.team_name,
        "slug": team.slug,
        "members": team.get_members(with_emails=is_own_team),
        "profile_pic_approved": team.profile_pic_approved,
    }
    if is_own_team or team.profile_pic_approved:
        team_info["profile_pic"] = get_profile_pic_url(
            request, team, victory=request.context.is_hunt_complete
        )
    if not can_view_info:
        return JsonResponse({"teamInfo": team_info, "canModify": False})

    # This Team.leaderboard() call is expensive, but is the only way
    # right now to calculate rank accurately. Hopefully it is not an
    # issue in practice.
    leaderboard = Team.leaderboard(user_team)
    rank = None
    for i, leaderboard_team in enumerate(leaderboard):
        if team.team_name == leaderboard_team["team_name"]:
            rank = i + 1  # ranks are 1-indexed
            break

    guesses = defaultdict(int)
    correct = {}
    team_solves = {}
    unlock_time_map = {
        unlock.puzzle_id: max(HUNT_START_TIME, unlock.unlock_datetime)
        for unlock in team.db_unlocks
    }
    for submission in team.submissions:
        if submission.is_correct:
            team_solves[submission.puzzle_id] = submission.puzzle
            correct[submission.puzzle_id] = {
                "slug": submission.puzzle.solution_slug,
                "name": submission.puzzle.name,
                "is_meta": submission.puzzle.is_meta,
                "answer": submission.submitted_answer,
                "unlock_time": unlock_time_map.get(
                    submission.puzzle_id, HUNT_START_TIME
                ),
                "solve_time": submission.submitted_datetime,
                "used_free_answer": submission.used_free_answer,
                "open_duration": (
                    submission.submitted_datetime
                    - unlock_time_map.get(submission.puzzle_id, HUNT_START_TIME)
                ).total_seconds(),
            }
        else:
            guesses[submission.puzzle_id] += 1
    submissions = []
    for puzzle in correct:
        correct[puzzle]["guesses"] = guesses[puzzle]
        submissions.append(correct[puzzle])
    submissions.sort(key=lambda submission: submission["solve_time"])
    solves = [HUNT_START_TIME] + [s["solve_time"] for s in submissions]
    if solves[-1] >= HUNT_END_TIME:
        solves.append(min(request.context.now, HUNT_CLOSE_TIME))
    else:
        solves.append(HUNT_END_TIME)
    chart = {
        "hunt_length": (solves[-1] - HUNT_START_TIME).total_seconds(),
        "solves": [
            {
                "before": (solves[i - 1] - HUNT_START_TIME).total_seconds(),
                "after": (solves[i] - HUNT_START_TIME).total_seconds(),
            }
            for i in range(1, len(solves))
        ],
        "metas": [
            (s["solve_time"] - HUNT_START_TIME).total_seconds()
            for s in submissions
            if s["is_meta"]
        ],
        "end": (HUNT_END_TIME - HUNT_START_TIME).total_seconds(),
    }
    team.solves = team_solves

    return JsonResponse(
        {
            "teamInfo": team_info,
            "submissions": submissions,
            "chart": chart,
            "solves": sum(1 for s in submissions if not s["used_free_answer"]),
            "canModify": is_own_team and not request.context.hunt_is_closed,
            "rank": rank,
        }
    )


@require_GET
def teams(request):
    return JsonResponse(
        {
            "teams": Team.leaderboard(request.context.team),
        }
    )


def profile_pic_discord_content(request, team):
    profile_pic_url = generate_url(get_profile_pic_url(request, team))
    approve_url = generate_url(reverse("approve_picture", args=[team.user.username]))
    content = f"""
    {team.team_name} updated their team photo to {profile_pic_url}.
    You may approve it at {approve_url}. React to this Discord message if you've
    done so.
    """
    return content


@require_POST
@login_required
@restrict_access(after_hunt_end=False)
def delete_profile_pic(request, slug):
    user_team = request.context.team
    is_own_team = user_team is not None and user_team.slug == slug
    if not is_own_team:
        # Stop it.
        return JsonResponse({}, status=404)
    user_team.profile_pic.delete()
    user_team.profile_pic_approved = False
    user_team.save()
    return JsonResponse({})


@require_POST
@login_required
@restrict_access(after_hunt_end=False)
def upload_profile_pic(request, slug):
    user_team = request.context.team
    is_own_team = user_team is not None and user_team.slug == slug
    if not is_own_team:
        # Stop it.
        return JsonResponse({}, status=404)

    form = ProfilePictureForm(request.POST, request.FILES, instance=user_team)
    is_valid = form.is_valid()
    if is_valid:
        # Save as new image but also toggle as unknown and send an alert to approve.
        form.save()
        user_team.profile_pic_approved = False
        user_team.save()
        dispatch_profile_pic_alert(profile_pic_discord_content(request, user_team))

    reply = {"form_errors": form.errors, "is_valid": is_valid, "profile_pic": ""}
    status = 200
    if form.errors:
        # Default to 400 bad request
        status = 400
        # check if the errors are unsupported media type errors just for fun.
        for error_msg in form.errors["profile_pic"]:
            if error_msg == ProfilePictureForm.unsupported_media_type_error_message:
                status = 415
                dispatch_bad_profile_pic_alert(
                    f":frame_photo: Team {user_team.team_name} tried to upload a bad profile picture."
                )
                break

    else:
        # Pull the new team photo.
        reply["profile_pic"] = get_profile_pic_url(request, user_team)

    return JsonResponse(reply, status=status)


@restrict_access(after_hunt_end=False)
def edit_team(request, slug):
    team = request.context.team
    if team is None:
        return JsonResponse(
            {"form_errors": {"__all__": "You must be logged in to edit this team."}},
            status=401,
        )
    elif team.slug != slug:
        return JsonResponse(
            {
                "form_errors": {
                    "__all__": "You do not have permission to edit this team."
                }
            },
            status=401,
        )

    form = TeamEditForm(team, request.POST)
    form_errors = dict()
    if not form.is_valid():
        form_errors.update(form.errors)
    if form_errors:
        return JsonResponse({"form_errors": form_errors}, status=400)

    if form.is_valid():
        data = [
            (form.cleaned_data[f"name{i+1}"], form.cleaned_data[f"email{i+1}"])
            for i in range(TEAM_SIZE)
        ]

        # Fetch all teammates and update their data
        teammates = team.teammember_set.order_by("pk").all()
        for i, (name, email) in enumerate(data):
            if i >= len(teammates) and name:
                TeamMember.objects.create(team=team, name=name, email=email)
            elif name:
                teammates[i].name = name
                teammates[i].email = email
                teammates[i].save()
            elif i < len(teammates):
                teammates[i].delete()

        members = ", ".join([str(member) for member in team.teammember_set.all()])
        dispatch_general_alert(f"Team {team} updated teammates: {members}")

    return JsonResponse({})


@restrict_access(after_hunt_end=True)
def unlock_everything(request):
    # Only available after hunt ends. Lets a team unlock everything.
    if not request.context.team:
        return JsonResponse({}, status=404)
    team = request.context.team
    team.is_prerelease_testsolver = True
    team.save()
    return JsonResponse({}, status=200)


def unsubscribe(request):
    form = UnsubscribeEmailForm(request.POST)
    message_id_prefix = request.GET.get("mid")
    message_id = (
        f"{message_id_prefix}@{settings.EMAIL_USER_DOMAIN}"
        if message_id_prefix
        else None
    )

    if request.method == "POST":
        form_errors = dict()
        if not form.is_valid():
            form_errors.update(form.errors)
        if form_errors:
            return JsonResponse({"form_errors": form_errors}, status=400)
        address = form.cleaned_data["email"]
        email = (
            message_id
            and Email.objects.filter(
                message_id=message_id,
                is_from_us=True,
            )
            .only("to_addresses", "cc_addresses", "bcc_addresses")
            .first()
        )
        valid = False
        if email is None:
            return JsonResponse({}, status=404)
        for recipient in email.all_recipients:
            if address == Email.parseaddr(recipient):
                valid = True
        if not valid:
            return JsonResponse(
                {"form_errors": {"email": f"This email was not sent to '{address}'"}},
                status=400,
            )
        BadEmailAddress.objects.get_or_create(
            defaults={
                "reason": BadEmailAddress.UNSUBSCRIBED,
            },
            email=address,
        )
        return JsonResponse({}, status=200)

    else:
        exists = (
            message_id
            and Email.objects.filter(
                message_id=message_id,
                is_from_us=True,
            ).exists()
        )
        if not exists:
            return JsonResponse({}, status=404)
        return JsonResponse({}, status=200)
