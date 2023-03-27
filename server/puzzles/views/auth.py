import datetime
import secrets
import urllib.parse
from collections import defaultdict
from functools import wraps
from typing import Callable, List, Mapping, Tuple

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpResponse, JsonResponse, QueryDict
from django.shortcuts import redirect, render
from django.utils.timezone import now
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from spoilr.core.api.hunt import is_site_launched, is_site_solutions_published
from spoilr.core.models import UserAuth
from spoilr.registration.models import IndividualRegistrationInfo, TeamRegistrationInfo
from spoilr.utils import generate_url
from tph.utils import get_site, url_has_allowed_host_and_scheme

from puzzles.forms import (
    CustomUserCreationForm,
    IndividualCreationForm,
    IndividualEditForm,
    TeamCreationForm,
    TeamEditForm,
)
from puzzles.models import Puzzle, PuzzleAccess, PuzzleSubmission
from puzzles.utils import login_required

AUTH_TOKEN_EXPIRY = datetime.timedelta(minutes=2)
SSO_AUTH_NORMAL = "1"
TOKEN_BYTES = 32


def get_default_login_next_url(request):
    site = get_site(request)
    url = generate_url(site, "/")
    return url


@require_POST
def log_in(request):
    form = AuthenticationForm(request, request.POST)
    if not form.is_valid():
        return JsonResponse({"form_errors": form.errors}, status=400)

    user = form.get_user()

    if user is not None:
        if user.team is not None or request.get_host() == settings.REGISTRATION_HOST:
            login(request, user)
            return login_redirect(request, request.POST)
        else:
            return JsonResponse(
                {
                    "form_errors": {
                        "__all__": "Cannot log in as an individual. Please use your team login."
                    }
                },
                status=401,
            )
    return JsonResponse({}, status=401)


def login_redirect(request, parameters):
    next_url = parameters.get("next", get_default_login_next_url(request))
    auth = parameters.get("auth")
    use_json = parameters.get("json")
    if not url_has_allowed_host_and_scheme(next_url):
        next_url = get_default_login_next_url(request)
    parsed_next_url = urllib.parse.urlparse(next_url)
    next_query = QueryDict(parsed_next_url.query, mutable=True)
    if request.user.is_authenticated and auth == SSO_AUTH_NORMAL:
        # add SSO token
        user_auth = UserAuth.objects.create(
            user=request.user, token=secrets.token_hex(TOKEN_BYTES)
        )
        next_query["token"] = user_auth.token
    parsed_next_url = parsed_next_url._replace(query=next_query.urlencode(safe="/"))
    full_next_url = urllib.parse.urlunparse(parsed_next_url)
    if use_json:
        # pass back as json to let the client handle the redirect
        return JsonResponse({"redirect": full_next_url})
    return redirect(full_next_url)


@login_required
def log_out(request):
    # TODO: potentially logging out of one site should log out of all of them
    # but this is a niche case that doesn't really provide benefit
    logout(request)
    return JsonResponse({})


def get_login_redirect_url(request, url):
    """
    Return a redirect to the login page.
    """
    original_host = request.get_host()
    login_host = settings.SSO_HOST
    login_path = "/login"
    login_query = QueryDict(mutable=True)
    if not login_host or login_host == original_host:
        # same site, only needs: login -> original_url
        login_url = login_path
        login_query["next"] = url
    else:
        # separate site, needs SSO: login[login site] -> authorize_url[this site] -> original_url[this site]
        parsed_authorize_url = urllib.parse.urlparse(
            f"https://{original_host}/authorize"
        )
        authorize_query = QueryDict(mutable=True)
        authorize_query["next"] = url
        parsed_authorize_url = parsed_authorize_url._replace(
            query=authorize_query.urlencode(safe="/")
        )
        login_url = f"https://{login_host}{login_path}"
        login_query["next"] = urllib.parse.urlunparse(parsed_authorize_url)
        login_query["auth"] = SSO_AUTH_NORMAL
    parsed_login_url = urllib.parse.urlparse(login_url)
    parsed_login_url = parsed_login_url._replace(query=login_query.urlencode(safe="/"))
    full_login_url = urllib.parse.urlunparse(parsed_login_url)

    return redirect(full_login_url)


@require_GET
def authorize_view(request):
    token = request.GET.get("token")
    next_url = request.GET.get("next")
    if not url_has_allowed_host_and_scheme(next_url):
        next_url = None
    user_auth = (
        UserAuth.objects.prefetch_related("user")
        .filter(
            token=token,
            create_time__gt=now() - AUTH_TOKEN_EXPIRY,
            delete_time__isnull=True,
        )
        .first()
    )
    if not user_auth:
        # could implement error handling here but not necessary
        # go to default url since we could not authorize
        return redirect(get_default_login_next_url(request))

    user_auth.delete_time = now()
    user_auth.save()

    user = user_auth.user
    login(request, user)
    return redirect(next_url or get_default_login_next_url(request))


@require_http_methods(["GET", "POST"])
def registration(request, slug):
    team = request.context.team
    if team is None:
        return JsonResponse(
            {
                "form_errors": {
                    "__all__": f"You must be logged in to {request.method} registration info for this team."
                }
            },
            status=401,
        )
    elif team.slug != slug:
        return JsonResponse(
            {
                "form_errors": {
                    "__all__": f"You do not have permission to {request.method} registration info for this team."
                }
            },
            status=401,
        )
    elif not hasattr(team, "teamregistrationinfo"):
        return JsonResponse(
            {
                "form_errors": {
                    "__all__": f"You do not have any registration info. Please contact us if you are not an internal team."
                }
            },
            status=401,
        )

    # PATCH would be more correct here, but ASGIRequest doesn't seem to expose request.PATCH
    if request.method == "POST":
        if is_site_launched():
            return JsonResponse(
                {
                    "form_errors": {
                        "__all__": "Hunt has already started, and registration is closed."
                    }
                },
                status=400,
            )

        team_edit_form = TeamEditForm(request.POST, instance=team.teamregistrationinfo)

        form_errors = dict()
        if not team_edit_form.is_valid():
            form_errors.update(team_edit_form.errors)
        if len(form_errors):
            return JsonResponse({"form_errors": form_errors}, status=400)

        TeamRegistrationInfo.objects.filter(team_id=team.id).update(
            **team_edit_form.cleaned_data
        )

        return JsonResponse({})

    if request.method == "GET":
        registration_info = team.teamregistrationinfo
        return JsonResponse(
            {
                # PhoneNumberField is not serializable, so cast it to a str explicitly
                "contact_phone": str(registration_info.contact_phone),
                **model_to_dict(
                    registration_info,
                    fields=[
                        "team_name",
                        "contact_name",
                        "contact_pronouns",
                        "contact_email",
                        "bg_bio",
                        "bg_emails",
                        "bg_playstyle",
                        "bg_win",
                        "bg_started",
                        "bg_location",
                        "bg_comm",
                        "bg_on_campus",
                        "tb_room",
                        "tb_room_specs",
                        "tb_location",
                        "tm_total",
                        "tm_last_year_total",
                        "tm_undergrads",
                        "tm_grads",
                        "tm_alumni",
                        "tm_faculty",
                        "tm_other",
                        "tm_minors",
                        "tm_onsite",
                        "tm_offsite",
                        "other_unattached",
                        "other_workshop",
                        "other_puzzle_club",
                        "other_how",
                        "other",
                    ],
                ),
            }
        )


@require_POST
def register(request):
    user_form = CustomUserCreationForm(request.POST)
    team_form = TeamCreationForm(request.POST)

    form_errors = dict()
    if not user_form.is_valid():
        form_errors.update(user_form.errors)
    if not team_form.is_valid():
        form_errors.update(team_form.errors)
    if len(form_errors):
        return JsonResponse({"form_errors": form_errors}, status=400)

    with transaction.atomic():
        user = user_form.save(commit=True)
        team = team_form.save(user)

    login(request, user)
    return JsonResponse({})


@require_http_methods(["GET", "POST"])
def register_individual(request):
    # GET is for populating the form with the user's last-set fields when editing registration.
    if request.method == "GET":
        if not request.user.is_authenticated:
            return JsonResponse(
                {
                    "form_errors": {
                        "__all__": f"You must be logged in to get registration info for this user."
                    }
                },
                status=401,
            )
        return JsonResponse(
            model_to_dict(
                IndividualRegistrationInfo.objects.get(user_id=request.user.id),
                fields=[
                    "team_name",
                    "contact_first_name",
                    "contact_last_name",
                    "contact_pronouns",
                    "contact_email",
                    "bg_mh_history",
                    "bg_other_history",
                    "bg_playstyle",
                    "bg_other_prefs",
                    "bg_on_campus",
                    "bg_under_18",
                    "bg_mit_connection",
                    "other",
                ],
            )
        )

    # POST is for doing initial registration (if not logged in)
    # or actually doing the editing of registration (if logged in).
    # PATCH would be more correct for editing, but ASGIRequest doesn't seem to expose request.PATCH
    if request.method == "POST":
        if is_site_launched():
            return JsonResponse(
                {
                    "form_errors": {
                        "__all__": "Hunt has already started, and registration is closed."
                    }
                },
                status=400,
            )
        if not request.user.is_authenticated:
            user_form = CustomUserCreationForm(request.POST)
            individual_form = IndividualCreationForm(request.POST)

            form_errors = dict()
            if not user_form.is_valid():
                form_errors.update(user_form.errors)
            if not individual_form.is_valid():
                form_errors.update(individual_form.errors)
            if len(form_errors):
                return JsonResponse({"form_errors": form_errors}, status=400)

            with transaction.atomic():
                user = user_form.save(commit=True)
                individual_registration_info = individual_form.save(user)

            login(request, user)
            return JsonResponse({})
        else:
            individual_edit_form = IndividualEditForm(
                request.POST, instance=request.user.individualregistrationinfo
            )

            form_errors = dict()
            if not individual_edit_form.is_valid():
                form_errors.update(individual_edit_form.errors)
            if len(form_errors):
                return JsonResponse({"form_errors": form_errors}, status=400)

            IndividualRegistrationInfo.objects.filter(user_id=request.user.id).update(
                **individual_edit_form.cleaned_data
            )

            return JsonResponse({})


def perform_validate_puzzle(
    request,
    slug,
    require_team=False,
    allow_after_hunt=False,
):
    """
    Validates access to the puzzle slug and populates request.context.puzzle.
    Returns an error response if there was an error and None otherwise.
    """
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
    return None


def validate_puzzle(require_team=False, allow_after_hunt=False):
    """
    Indicates an endpoint that takes a single URL parameter, the slug for the
    puzzle. If the slug is invalid, report an error and redirect to /puzzles.
    If require_team is true, then the user must also be logged in.
    """

    def decorator(f):
        @wraps(f)
        def inner(request, slug, *args, **kwargs):
            if resp := perform_validate_puzzle(
                request,
                slug,
                require_team=require_team,
                allow_after_hunt=allow_after_hunt,
            ):
                return resp
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
                            rf"/admin/login/?next={urllib.parse.quote(request.path)}"
                        )
                    else:
                        # api, static
                        return JsonResponse({}, status=404)
                elif is_internal:
                    return redirect(
                        rf"/admin/login/?next={urllib.parse.quote(request.path)}"
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


def solution_allowed(request):
    return (
        request.context.hunt_is_over and is_site_solutions_published()
    ) or request.context.is_superuser


@require_GET
def check_access_allowed(request, original_path):
    """
    All gating is done by url paths, not parameters, but the full url is
    returned if valid.
    """
    parts = defaultdict(lambda: None, enumerate(original_path.split("/")))
    stripped_path = "/" + original_path.rstrip("/")
    original_path = "/" + original_path
    query_string = request.META.get("QUERY_STRING", "")
    if query_string:
        query_string = "?" + query_string
    original_uri = original_path + query_string
    is_static = "/static/" in original_path
    allowed = False

    a3 = None
    slug = None
    subpart = None
    resource_type = "invalid"

    if stripped_path == "/login":
        resource_type = "login"
    elif stripped_path == "/clipboard":
        resource_type = "public"
    elif parts[0] == "solutions":
        resource_type = "solution"
    elif parts[0] == "hints":
        resource_type = "hint"
        slug = parts[1]
    elif stripped_path == "/puzzles":
        resource_type = "all_puzzles"
    elif parts[0] == "rounds":
        resource_type = "round"
    elif parts[0] == "victory":
        resource_type = "winner-only"
    elif parts[0] == "internal_frontend":
        resource_type = "admin"
    elif parts[0] == "puzzles":
        resource_type = "puzzle"
        slug = parts[1]
        subpart = parts[2]

    if resource_type in ("puzzle", "hint"):
        if slug:
            allowed, _ = request.context.is_unlocked(slug)
        if allowed and resource_type == "puzzle" and subpart:
            allowed = request.context.is_minipuzzle_unlocked(slug, subpart)
        if not allowed:
            allowed = request.context.hunt_is_over
    elif resource_type == "solution":
        allowed = solution_allowed(request)
    elif resource_type == "all_puzzles":
        allowed = request.context.hunt_is_over or (
            request.context.hunt_has_started and request.context.team
        )
    elif resource_type == "round":
        # TODO: round access logic
        allowed = request.context.hunt_is_over or True
    elif resource_type == "winner-only":
        allowed = request.context.hunt_is_over or request.context.is_hunt_complete
    elif resource_type == "admin":
        allowed = request.context.is_superuser
    elif resource_type == "login":
        allowed = True
    elif resource_type == "invalid":
        allowed = False
    else:
        allowed = False

    if allowed:
        if resource_type == "login":
            # check if already authenticated
            if request.user.is_authenticated:
                return login_redirect(request, request.GET)
        response = HttpResponse(status=200)
        response["X-Accel-Redirect"] = original_uri
        return response
    # 404 page
    response = HttpResponse(status=404)
    if is_static:
        # force Caddy to respond like it's serving a real 404 for a static request
        response["X-Accel-Redirect"] = "/static/does-not-exist"
    else:
        if not request.user.is_authenticated:
            # if accessing a protected page but not logged in, redirect to the login page
            if redirect_response := get_login_redirect_url(request, original_uri):
                return redirect_response
        # force Caddy to pass-through to Next.js to serve a "front-end" 404 page
        response["X-Accel-Redirect"] = "/does-not-exist"
    return response
