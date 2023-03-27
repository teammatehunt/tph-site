import collections

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from spoilr.core.api.answer import submit_puzzle_answer
from spoilr.core.api.hunt import accomplish_interaction, release_interaction
from spoilr.core.models import Interaction, InteractionAccess, Team
from spoilr.email.models import Email, CannedEmail
from spoilr.hq.models import HqLog, Task, TaskStatus
from spoilr.hq.util.decorators import hq
from spoilr.hq.util.redirect import redirect_with_message
from spoilr.interaction.models import InteractionAccessTask

HQ_EMAIL_PREFIX = "HQ Update: "


@hq()
def dashboard_view(request):
    accesses = (
        InteractionAccess.objects.filter(interactionaccesstask__tasks__isnull=False)
        .exclude(interactionaccesstask__tasks__status=TaskStatus.IGNORED)
        .prefetch_related("interactionaccesstask__tasks")
        .order_by("create_time")
    )

    available_by_interaction = collections.defaultdict(int)
    accomplished_by_interaction = collections.defaultdict(int)
    unclaimed_by_interaction = collections.defaultdict(int)
    for access in accesses:
        if access.accomplished:
            accomplished_by_interaction[access.interaction_id] += 1
        else:
            available_by_interaction[access.interaction_id] += 1
        tasks = list(access.interactionaccesstask.tasks.all())
        if not tasks:
            continue
        task = tasks[0]
        if not task.handler:
            unclaimed_by_interaction[access.interaction_id] += 1

    interactions = Interaction.objects.order_by("order")
    interaction_infos = [
        {
            "interaction": interaction,
            "interaction_type": interaction.interaction_type,
            "available_count": available_by_interaction[interaction.id],
            "accomplished_count": accomplished_by_interaction[interaction.id],
            "unclaimed_count": unclaimed_by_interaction[interaction.id],
        }
        for interaction in interactions
    ]
    interaction_infos.sort(
        key=lambda interaction_info: (
            -interaction_info["available_count"],
            interaction_info["interaction"].order,
        )
    )
    return render(
        request,
        "spoilr/interaction/dashboard.tmpl",
        {
            "interaction_infos": interaction_infos,
        },
    )


@hq()
def interaction_view(request, interaction_slug):
    interaction = get_object_or_404(Interaction, slug=interaction_slug)
    accesses = (
        InteractionAccess.objects.select_related("team")
        .prefetch_related("interactionaccesstask__tasks")
        .filter(
            interaction=interaction,
            interactionaccesstask__tasks__isnull=False,
            interactionaccesstask__tasks__status__in=(
                TaskStatus.PENDING,
                TaskStatus.SNOOZED,
            ),
        )
    )

    teams_ready = []
    teams_claimed = []
    teams_snoozed = []
    for access in accesses:
        # tasks is cached by the prefetch already
        tasks = list(access.interactionaccesstask.tasks.all())
        if not tasks:
            continue
        task = tasks[0]
        if task.status == TaskStatus.SNOOZED:
            teams_snoozed.append(
                {
                    "team": access.team,
                    "task": task,
                    "create_time": access.create_time,
                }
            )
        elif task.handler and task.handler != request.handler:
            teams_claimed.append(
                {
                    "team": access.team,
                    "task": task,
                    "create_time": access.create_time,
                }
            )
        else:
            teams_ready.append(
                {
                    "team": access.team,
                    "task": task,
                    "create_time": access.create_time,
                }
            )

    teams_snoozed.sort(key=lambda x: x["create_time"])
    teams_ready.sort(key=lambda x: x["create_time"])
    teams_claimed.sort(key=lambda x: x["create_time"])
    teams_accomplished = []
    for access in (
        InteractionAccess.objects.select_related("team")
        .prefetch_related("interactionaccesstask__tasks")
        .filter(interaction=interaction, accomplished=True)
        .order_by("-accomplished_time")
    ):
        teams_accomplished.append(
            {
                "team": access.team,
                "task": access.interactionaccesstask.tasks.first(),
                "create_time": access.create_time,
                "accomplished_time": access.accomplished_time,
            }
        )

    teams_accomplished.reverse()

    used_team_ids = (
        [t["team"].id for t in teams_ready]
        + [t["team"].id for t in teams_snoozed]
        + [t["team"].id for t in teams_accomplished]
    )
    teams_not_ready = Team.objects.exclude(id__in=used_team_ids)

    return render(
        request,
        "spoilr/interaction/interaction.tmpl",
        {
            "interaction": interaction,
            "teams_ready": teams_ready,
            "teams_snoozed": teams_snoozed,
            "teams_claimed": teams_claimed,
            "teams_accomplished": teams_accomplished,
            "teams_not_ready": teams_not_ready,
        },
    )


@hq()
def details_view(request, interaction_slug, team_username):
    interaction = get_object_or_404(Interaction.objects, slug=interaction_slug)
    email_templates = list(interaction.cannedemail_set.order_by("slug"))
    email_templates.extend(list(CannedEmail.objects.filter(interaction=None)))
    team = get_object_or_404(Team, username=team_username)
    access = (
        InteractionAccess.objects.prefetch_related("interactionaccesstask__tasks")
        .filter(interaction=interaction, team=team)
        .first()
    )

    task = None
    try:
        task = (
            access
            and access.interactionaccesstask
            and access.interactionaccesstask.tasks.first()
        )
    except InteractionAccessTask.DoesNotExist:
        pass

    if access and task and task.status == TaskStatus.DONE:
        status = "accomplished"
    elif access and task and task.status == TaskStatus.SNOOZED:
        status = "snoozed"
    elif access and task and task.handler and task.handler != request.handler:
        status = "claimed"
    elif access and task and task.handler:
        status = "ready"
    elif access and task:
        status = "unclaimed"
    else:
        status = "not_ready"

    extra_context = {}
    if request.method == "POST":
        if request.POST.get("subject") or request.POST.get("body"):
            extra_context, response = handle_interaction_email(
                request, interaction, team, access
            )
            if response:
                return response

    emails = (
        Email.objects.select_related("interaction", "team")
        .defer("raw_content", "header_content")
        .order_by("-received_datetime")
        .filter(interaction=interaction, team=team)
    )

    # This could be improved by using forms.
    # See email dashboard_views.py for similar code using forms.
    email_data = []
    for email in emails:
        email_data.append(
            {
                "email": email,
                "type": "out" if email.is_from_us else "in",
            }
        )

    return render(
        request,
        "spoilr/interaction/details.tmpl",
        {
            "interaction": interaction,
            "email_templates": email_templates,
            "team": team,
            "interaction_access": access,
            "task": task,
            "status": status,
            "emails": email_data,
            "allow_danger": request.GET.get("danger") == "1",
            **extra_context,
        },
    )


@require_POST
def handle_interaction_email(request, interaction, team, interaction_access):
    confirm = request.POST.get("confirm")
    subject = request.POST.get("subject", "")
    body_text = request.POST.get("body", "")
    txt_body_text = request.POST.get("text_content", "")
    allow_resend = request.POST.get("danger-resend", "") == "1"

    error = None
    if not subject or not body_text:
        error = "Missing fields"
    elif confirm.lower() != "send":
        error = "Did not confirm sending the email"
    elif not allow_resend and interaction_access.interactionaccesstask.replied:
        error = "Someone has already replied - maybe from clicking refresh?"
    elif subject.strip() == HQ_EMAIL_PREFIX.strip():
        error = "Make sure you enter a subject"

    if error:
        return {
            "subject": subject,
            "body": body_text,
            "error": error,
        }, None

    # FIXME(update): Update this logic for your hunt
    # email_or_none = send_mail_text_wrapper(
    #     subject=subject,
    #     plaintxt=txt_body_text,
    #     html=body_text,
    #     recipients=team.all_emails,
    #     is_prehunt=False,
    # )
    if email_or_none:
        # Correctly created email model.
        email = email_or_none
        email.interaction = interaction
        email.team = team
        # TODO attach the interaction task to the email correctly such that email.handler can
        # be retrieved correctly. Not needed for email sending but helpful for stats on who
        # handled which emails.
        email.save()

    interaction_access.interactionaccesstask.replied = True
    interaction_access.interactionaccesstask.save()

    HqLog.objects.create(
        handler=request.handler,
        event_type="story-send",
        object_id=interaction.slug,
        message=f"Sent story email to {team.username}: {body_text}",
    )

    return None, redirect_with_message(
        request,
        "spoilr.interaction:details",
        "Story email sent.",
        default_path_args=(interaction.slug, team.username),
    )


@require_POST
@hq(require_handler=True)
def resolve_answer_view(request):
    unlock_id = int(request.POST.get("unlock_id"))
    task_id = int(request.POST.get("task_id"))
    action = request.POST.get("action")
    if not unlock_id or action not in ("solve", "cancel"):
        return HttpResponseBadRequest("Missing or invalid fields")

    confirm = request.POST.get("confirm")
    if confirm.lower() != action:
        return redirect_with_message(
            request, "spoilr.interaction:dashboard", "Interaction was not resolved."
        )

    if action == "solve":
        submit_puzzle_answer(unlock.team, unlock.puzzle, unlock.puzzle.answer)

    resolve_task(request, task)

    return redirect_with_message(
        request,
        "spoilr.interaction:dashboard",
        "Free answer approved." if action == "solve" else "Free answer cancelled.",
    )


@require_POST
@hq(require_handler=True)
def resolve_view(request):
    confirm = request.POST.get("confirm")
    if confirm.lower() != "resolve":
        return redirect_with_message(
            request, "spoilr.interaction:dashboard", "Interaction was not resolved."
        )

    task_id = int(request.POST.get("task_id"))
    task = Task.objects.get(id=task_id) if task_id else None
    if not task:
        return HttpResponseBadRequest("Missing or invalid fields")

    resolve_task(request, task)

    return redirect_with_message(
        request, "spoilr.interaction:dashboard", "Interaction resolved."
    )


@require_POST
@hq(require_handler=True)
def danger_release_view(request):
    confirm = request.POST.get("confirm")
    if confirm.lower() != "release":
        return redirect_with_message(
            request, "spoilr.interaction:dashboard", "Interaction was not released."
        )

    interaction_id = int(request.POST.get("interaction_id"))
    interaction = get_object_or_404(Interaction, id=interaction_id)
    team_id = int(request.POST.get("team_id"))
    team = get_object_or_404(Team, id=team_id)

    release_interaction(team, interaction)

    HqLog.objects.create(
        handler=request.handler,
        event_type="interaction-released-danger",
        object_id=interaction.slug,
        message=f"Release interaction {interaction} for team {team}",
    )

    return redirect_with_message(
        request, "spoilr.interaction:dashboard", "Interaction released."
    )


def resolve_task(request, task):
    if task.handler != request.handler:
        return redirect_with_message(
            request,
            "spoilr.interaction:dashboard",
            f"You are no longer handling this task.",
        )
    if task.status == TaskStatus.DONE:
        return redirect_with_message(
            request, "spoilr.interaction:dashboard", "Task is already done."
        )

    if task.content_type != ContentType.objects.get_for_model(InteractionAccessTask):
        return HttpResponseBadRequest("Invalid task type")

    interaction_access = task.content_object.interaction_access
    accomplish_interaction(interaction_access=interaction_access)

    task.status = TaskStatus.DONE
    task.snooze_time = None
    task.snooze_until = None
    task.save()

    HqLog.objects.create(
        handler=request.handler,
        event_type="interaction-resolved",
        object_id=interaction_access.interaction.slug,
        message=f"Resolve interaction {interaction_access.interaction} for team {interaction_access.team}",
    )
