"""tph URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from typing import Callable, List, Mapping, Tuple

from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from puzzles.views import auth, puzzles, team, views

# A map from slug to list of endpoint tuples (endpoint url, API handler)
PUZZLE_SPECIFIC_ENDPOINTS: Mapping[str, List[Tuple[str, Callable]]] = {
    # FIXME
    # "sample": [("data", sample.puzzle_data)],
}

urlpatterns = list(
    filter(
        None,
        [
            re_path(r"^admin/", admin.site.urls),
            not settings.IS_PYODIDE
            and re_path(r"^impersonate/", include("impersonate.urls")),
            # urls for password reset: request_reset, validate_token, and reset_password
            path("api/", include("pwreset.urls")),
            re_path(r"^api/teams/", team.teams),
            re_path(r"^api/team_info/(?P<slug>.+)/edit", team.edit_team),
            re_path(r"^api/team_info/(?P<slug>.+)?", team.get_team_info),
            re_path(r"^api/upload_profile_pic/(?P<slug>.+)", team.upload_profile_pic),
            re_path(r"^api/delete_profile_pic/(?P<slug>.+)", team.delete_profile_pic),
            re_path(r"^api/unlock_everything", team.unlock_everything),
            re_path(r"^api/hunt_info", views.get_hunt_info),
            re_path(r"^api/login", auth.log_in),
            re_path(r"^api/logout", auth.log_out),
            re_path(r"^api/register", auth.register),
            re_path(r"^api/puzzles", puzzles.puzzles),
            re_path(r"^api/unsubscribe", team.unsubscribe),
            path("api/solve/<slug:slug>", puzzles.solve),
            path("api/puzzle/<slug:slug>", puzzles.puzzle_data),
            path("api/puzzle/<slug:slug>/hint", puzzles.create_hint),
            path("api/puzzle/<slug:slug>/moreguesses", puzzles.request_more_guesses),
            path("api/stats/<slug:slug>", views.stats_public),
            path("api/guess_log", views.public_activity_csv),
            path("api/server.zip", views.server_zip),
            path("api/reset_local_database", views.reset_pyodide_db),
            # example puzzle page with copy-to-clipboard
            path("clipboard", views.clipboard, name="clipboard"),
            # special path only for Caddy to check whether the client should be allowed
            # access to the requested resource based on progression
            re_path(
                r"^check/(?P<original_path>.+)",
                auth.check_access_allowed,
            ),
            # Staff endpoints that aren't tied to the default Django admin site.
            re_path(
                r"^internal/approve_picture/(?P<user_name>.+)",
                views.approve_profile_pic,
                name="approve_picture",
            ),
            re_path(r"^internal/?$", views.internal_home, name="internal_home"),
            # TODO: once the hunt is over, switch to huntinfo/*
            re_path(r"^internal/bigboard", views.bigboard, name="bigboard"),
            re_path(r"^internal/finishers", views.finishers, name="finishers"),
            re_path(r"^internal/hunt_stats", views.hunt_stats, name="hunt-stats"),
            re_path(r"^internal/all_pictures", views.all_pictures, name="all-pictures"),
            # END-TODO
            re_path(r"^internal/hint_csv", puzzles.hint_csv, name="hint_csv"),
            re_path(r"^internal/hint_list", puzzles.hint_list, name="hint-list"),
            re_path(
                r"^internal/unanswered_email_list",
                puzzles.unanswered_email_list,
                name="unanswered-email-list",
            ),
            re_path(
                r"^internal/advanceteam/(?P<user_name>.+)",
                views.internal_advance_team,
                name="advance-team",
            ),
            re_path(r"^internal/single_hint/(?P<id>.+)", puzzles.hint, name="hint"),
            re_path(r"^internal/single_email/(?P<id>.+)", puzzles.email, name="email"),
            re_path(
                r"^internal/resend_emails", puzzles.resend_emails, name="resend-emails"
            ),
            re_path(
                r"^internal/extraguessgrant/(?P<id>.+)",
                puzzles.manage_extra_guess_grant,
                name="guess-grant",
            ),
            re_path(r"^internal/email_main", views.email_main, name="email-main"),
            re_path(r"^internal/all_emails", views.all_emails, name="all-emails"),
            re_path(
                r"^internal/errata_list", views.internal_errata, name="errata-list"
            ),
            re_path(
                r"^internal/errata_email/(?P<errata_pk>.+)",
                views.emails_for_errata,
                name="errata-email",
            ),
            re_path(
                r"^internal/errata_email_confirm",
                views.email_confirm,
                name="errata-email-confirm",
            ),
            path("internal/custom_email", views.custom_email, name="custom-email"),
            path("internal/add_hint", puzzles.debug_hint),
            path("internal/export_csv", views.activity_csv),
            # Puzzle-specific endpoints
            *[
                path(f"api/puzzle/{slug}/{endpoint_url}", api_handler, {"slug": slug})
                for slug, endpoints in PUZZLE_SPECIFIC_ENDPOINTS.items()
                for endpoint_url, api_handler in endpoints
            ],
        ],
    )
)

if settings.SILK_ENABLED:
    urlpatterns.append(url(r"^internal/silk/", include("silk.urls", namespace="silk")))

# serves media files in dev. Otherwise, Caddy serves them
urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))

if settings.DEBUG:
    urlpatterns.append(path("robots.txt", views.robots))
else:
    handler404 = "puzzles.views.views.handler404"
