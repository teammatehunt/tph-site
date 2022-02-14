import re
import urllib.parse
from functools import wraps
from typing import Callable, List, Mapping, Tuple

from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from puzzles.forms import TeamCreationForm
from puzzles.hunt_config import HUNT_TITLE
from puzzles.messaging import dispatch_general_alert, send_mail_wrapper
from puzzles.models import AnswerSubmission, Puzzle, PuzzleUnlock
from puzzles.utils import login_required


@require_POST
def log_in(request):
    form = AuthenticationForm(request, request.POST)
    if not form.is_valid():
        return JsonResponse({"form_errors": form.errors}, status=400)

    user = form.get_user()

    if user is not None:
        login(request, user)
        return JsonResponse({})
    return JsonResponse({}, status=401)


@login_required
def log_out(request):
    logout(request)
    return JsonResponse({})


@require_POST
def register(request):
    user_form = UserCreationForm(request.POST)
    team_form = TeamCreationForm(request.POST)

    form_errors = dict()
    if not user_form.is_valid():
        form_errors.update(user_form.errors)
    if not team_form.is_valid():
        form_errors.update(team_form.errors)
    if len(form_errors):
        return JsonResponse({"form_errors": form_errors}, status=400)

    user = user_form.save(commit=True)
    team = team_form.save(user)

    send_mail_wrapper(
        f"You’re registered for {HUNT_TITLE}!",
        "registration_email",
        {
            "username": user.username,
            "team_name": team.team_name,
            "team_link": team.team_url,
        },
        team.get_emails(),
    )

    members = ", ".join([str(member) for member in team.teammember_set.all()])
    dispatch_general_alert(f"Team {team} added teammates: {members}")

    login(request, user)
    return JsonResponse({})


def validate_puzzle(require_team=False, allow_after_hunt=False):
    """
    Indicates an endpoint that takes a single URL parameter, the slug for the
    puzzle. If the slug is invalid, report an error and redirect to /puzzles.
    If require_team is true, then the user must also be logged in.
    """

    def decorator(f):
        @wraps(f)
        def inner(request, slug, *args, **kwargs):
            is_unlocked, puzzle = request.context.is_unlocked(slug)
            if not is_unlocked:
                return JsonResponse({"error": "Invalid puzzle name."}, status=404)
            if (
                require_team
                and not request.context.team
                and not (allow_after_hunt and request.context.hunt_is_over)
            ):
                return JsonResponse(
                    {
                        "error": "You must be signed in and have a registered team to access this page.",
                    },
                    status=404,
                )
            request.context.puzzle = puzzle
            return f(request, *args, **kwargs)

        return inner

    return decorator


def restrict_access(after_hunt_end=None):
    """
    Indicates an endpoint that is hidden to all regular users. Superusers are
    always allowed access. Behavior depends on after_hunt_end:
    - if None, the page is admin-only.
    - if True, the page becomes visible when the hunt ends.
    - if False, the page becomes inaccessible when the hunt closes.
    """

    def decorator(f):
        @wraps(f)
        def inner(request, *args, **kwargs):
            is_internal = request.path.lstrip("/").split("/")[0] == "internal"
            if not request.context.is_superuser:
                if after_hunt_end is None:
                    if is_internal or request.path.lstrip("/").split("/")[0] in (
                        "huntinfo",
                        "impersonate",
                    ):
                        return redirect(
                            fr"/admin/login/?next={urllib.parse.quote(request.path)}"
                        )
                    else:
                        # api, static
                        return JsonResponse({}, status=404)
                elif is_internal:
                    return redirect(
                        fr"/admin/login/?next={urllib.parse.quote(request.path)}"
                    )
                elif after_hunt_end and not request.context.hunt_is_over:
                    return JsonResponse(
                        {"error": "Sorry, not available until the hunt ends."},
                        status=404,
                    )
                elif not after_hunt_end and request.context.hunt_is_closed:
                    return JsonResponse(
                        {"error": "Sorry, the hunt is over."}, status=404
                    )
            return f(request, *args, **kwargs)

        return inner

    return decorator


@require_GET
def check_access_allowed(request, original_path):
    """
    There are broadly two types of URLs that we need to gate access to:
    - */puzzles/{slug}/*
    - */assets/(locked|puzzle|solution|victory)/{slug}

    The former case is used in two different ways, one for static, compiled JS
    code, and the other for actual JSON responses from Next.js when it acts as
    an intermediary for data fetches required for page rendering.

    The latter case is for any assets that are manually added into the website,
    like images, fonts, etc.

    All gating is done by url paths, not parameters, but the full url is
    returned if valid.
    """
    original_path = "/" + original_path
    query_string = request.META.get("QUERY_STRING", "")
    if query_string:
        query_string = "?" + query_string
    original_uri = original_path + query_string
    stripped_path = original_path.rstrip("/")
    is_static = "/static/" in original_path
    allowed = False
    search_path = None

    # start with a basic whitelist for things that hit the @needs_check Caddy
    # matcher, but that we don't actually need to check anything for. These
    # are primarily actual pages, just with a trailing slash.
    if original_path in ["/puzzles/", "/solutions/"] or original_path.startswith(
        "/team/"
    ):
        resource_type = "allow"  # dummy value, not used
        allowed = True
    elif stripped_path == "/clipboard":
        resource_type = "public"
    elif original_path.startswith("/solutions/"):
        resource_type = "solution"
    elif original_path.startswith("/hints/"):
        resource_type = "hint"
        search_path = r"hints/([^/\.]+)"
    # FIXME: update this to the url of the main round puzzle page, if any.
    elif original_path.startswith("/round2"):
        resource_type = "locked"
    elif original_path.startswith("/victory"):
        resource_type = "winner-only"
    elif original_path.startswith("/internal_frontend/"):
        resource_type = "admin"
    elif original_path.startswith("/puzzles/"):
        resource_type = "puzzle"
        search_path = r"puzzles/([^/\.]+)"
    elif original_path.startswith("/_next/static/assets/solution/"):
        resource_type = "solution"
    elif original_path.startswith("/_next/static/assets/victory/"):
        resource_type = "winner-only"
    else:
        resource_type = "invalid"

    if resource_type in ("puzzle", "hint"):
        match = re.search(search_path, original_path)
        subpart = original_path[match.end() :].lstrip("/").split("/")[0]
        slug = match[1]
        allowed, _ = request.context.is_unlocked(slug)
        if allowed and resource_type == "puzzle" and subpart:
            allowed = request.context.is_subpuzzle_unlocked(slug, subpart)
        if not allowed:
            allowed = request.context.hunt_is_over
    elif resource_type == "solution":
        allowed = request.context.hunt_is_over or request.context.is_superuser
    elif resource_type == "locked":
        # Locked until main round is unlocked
        allowed = request.context.hunt_is_over or request.context.is_main_round_unlocked
    elif resource_type == "winner-only":
        allowed = request.context.hunt_is_over or request.context.is_hunt_complete
    elif resource_type == "admin":
        allowed = request.context.is_superuser
    elif resource_type == "invalid":
        allowed = False
    else:
        # Allow for public assets
        allowed = True

    if allowed:
        response = HttpResponse(status=200)
        response["X-Accel-Redirect"] = original_uri
        return response
    # 404 page
    response = HttpResponse(status=404)
    if is_static:
        # force Caddy to respond like it's serving a real 404 for a static request
        response["X-Accel-Redirect"] = "/static/does-not-exist"
    else:
        # force Caddy to pass-through to Next.js to serve a "front-end" 404 page
        response["X-Accel-Redirect"] = "/does-not-exist"
    return response
