from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from spoilr.core.api.hunt import is_site_launched
from spoilr.core.models import Interaction, Team, UserTeamRole
from spoilr.email.forms import AnswerEmailForm
from spoilr.email.models import CannedEmail, Email
from spoilr.hq.models import Task, TaskStatus
from spoilr.hq.util.decorators import hq

MAX_EMAIL_LIMIT = 200


@hq()
def dashboard_view(request):
    emails = (
        Email.objects.select_related("interaction", "team")
        .prefetch_related("tasks")
        .defer("raw_content", "header_content")
        .order_by("-received_datetime")
    )
    hidden = not (request.GET.get("hidden") and request.GET["hidden"] == "0")

    if request.GET.get("email"):
        emails = emails.filter(id=request.GET["email"])
    elif hidden:
        emails = (
            emails.filter(tasks__isnull=False, tasks__status=TaskStatus.PENDING)
            .exclude(status__in=Email.HIDDEN_STATUSES)
            .exclude(is_from_us=True)
        )

    # Exclude templates associated with interactions, as those are sent from the interactions page.
    email_templates = CannedEmail.objects.filter(interaction__isnull=True).order_by(
        "slug"
    )

    email_data = []
    for email in emails:
        form = AnswerEmailForm()

        form.initial["email_in_reply_to_pk"] = email.pk
        email_data.append(
            {
                "email": email,
                "task": email.tasks.first(),
                "form": form,
                "type": "out" if email.is_from_us else "in",
            }
        )

    return render(
        request,
        "spoilr/email/dashboard.tmpl",
        {
            "emails": email_data,
            "email_templates": email_templates,
            "hidden": hidden,
            "is_active": is_site_launched(),
        },
    )


@hq()
def archive_view(request):
    incoming_emails = (
        Email.objects.select_related("interaction", "team")
        .defer("raw_content", "header_content")
        .order_by("-received_datetime")
        .filter(is_from_us=False)
    )
    outgoing_emails = (
        Email.objects.filter(is_from_us=True)
        .defer("raw_content", "header_content")
        .order_by("-sent_datetime")
    )

    interaction = None
    if request.GET.get("interaction"):
        interaction = get_object_or_404(Interaction, url=request.GET["interaction"])
        incoming_emails = incoming_emails.filter(interaction=interaction)
        outgoing_emails = outgoing_emails.filter(interaction=interaction)

    team = None
    if request.GET.get("team"):
        team = get_object_or_404(Team, username=request.GET["team"])
        captain_email = team.user_set.get(team_role=UserTeamRole.SHARED_ACCOUNT).email
        team_email = team.team_email

        team_query = Q(team=team)
        email_query = Q(from_address__icontains=captain_email) | Q(
            recipient__icontains=captain_email
        )
        if captain_email:
            email_query |= Q(from_address__icontains=captain_email) | Q(
                recipient__icontains=captain_email
            )

        incoming_emails = incoming_emails.filter(team_query | email_query)
        outgoing_emails = outgoing_emails.filter(team_query | email_query)

    email = None
    if request.GET.get("email"):
        email = request.GET["email"]
        incoming_emails = incoming_emails.filter(
            Q(from_address__icontains=email) | Q(recipient__icontains=email)
        )
        outgoing_emails = outgoing_emails.filter(
            Q(from_address__icontains=email) | Q(recipient__icontains=email)
        )

    # Note: Could totally use the postgres full-text search magic when we know we're
    # running against postgres.
    search = None
    if request.GET.get("search"):
        search = request.GET["search"]
        incoming_emails = incoming_emails.filter(
            Q(subject__icontains=search)
            | Q(body_text__icontains=search)
            | Q(body_html__icontains=search)
        )
        outgoing_emails = outgoing_emails.filter(
            Q(subject__icontains=search) | Q(body_text__icontains=search)
        )

    hidden = not (request.GET.get("hidden") and request.GET["hidden"] == "0")
    if hidden:
        incoming_emails = incoming_emails.exclude(status__in=Email.HIDDEN_STATUSES)
        outgoing_emails = outgoing_emails.exclude(status__in=Email.HIDDEN_STATUSES)

    limit = min(request.GET.get("limit", 10), MAX_EMAIL_LIMIT)
    incoming_emails = incoming_emails[:limit]
    outgoing_emails = outgoing_emails[:limit]

    emails = [{"type": "in", "email": email} for email in incoming_emails] + [
        {"type": "out", "email": email} for email in outgoing_emails
    ]

    # Sort emails by sent or received datetime
    def email_sort_key(email_ref):
        email = email_ref["email"]
        if email_ref["type"] == "out":
            return (
                email.sent_datetime
                or email.attempted_send_datetime
                or email.scheduled_datetime
            )
        return email.received_datetime

    emails.sort(key=email_sort_key, reverse=True)

    teams = Team.objects.values_list("username", flat=True).order_by("username")
    interactions = Interaction.objects.values_list("slug", flat=True).order_by("slug")

    return render(
        request,
        "spoilr/email/archive.tmpl",
        {
            "limit": limit,
            "hidden": hidden,
            "interaction": interaction.slug if interaction else None,
            "team": team.username if team else None,
            "email": email or "",
            "search": search or "",
            "emails": emails,
            "teams": teams,
            "interactions": interactions,
        },
    )
