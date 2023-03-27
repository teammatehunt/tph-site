import datetime

import spoilr.email.models
import spoilr.hints.models
import spoilr.interaction.models
from django.http import HttpResponseBadRequest
from django.utils.timezone import now
from django.views.decorators.http import require_POST

from spoilr.hq.models import HqLog, Task, TaskStatus
from spoilr.hq.util.decorators import hq
from spoilr.hq.util.redirect import redirect_with_message


@require_POST
@hq(require_handler=True)
def task_claim_view(request):
    task_ids = request.POST.getlist("task_id")
    tasks = Task.objects.filter(id__in=task_ids)
    yoink = request.POST.get("yoink") == "1"
    anchor = request.POST.get("anchor")
    redirect_id = request.POST.get("redirect")

    force_reopen = request.POST.get("force_reopen") == "1"
    confirm = request.POST.get("confirm")
    if force_reopen and confirm.lower() != "reopen":
        return redirect_with_message(
            request, "spoilr.hq:dashboard", "Task was not reopened.", anchor=anchor
        )

    if not len(tasks):
        return redirect_with_message(
            request, "spoilr.hq:dashboard", "No tasks selected.", anchor=anchor
        )

    already_claimed = next(
        (
            task.handler
            for task in tasks
            if task.status != TaskStatus.SNOOZED
            and task.handler
            and task.handler != request.handler
        ),
        None,
    )
    if not yoink and already_claimed:
        return redirect_with_message(
            request,
            "spoilr.hq:dashboard",
            f"{already_claimed.name} has already claimed the task(s).",
            anchor=anchor,
        )

    if not force_reopen and any(
        task.status == TaskStatus.DONE or task.status == TaskStatus.IGNORED
        for task in tasks
    ):
        return redirect_with_message(
            request,
            "spoilr.hq:dashboard",
            "Task(s) have been done/ignored.",
            anchor=anchor,
        )

    logs = []
    for task in tasks:
        old_handler = task.handler
        task.claim_time = now()
        task.handler = request.handler

        task.status = TaskStatus.PENDING
        task.snooze_time = None
        task.snooze_until = None

        if yoink:
            logs.append(
                HqLog(
                    handler=request.handler,
                    event_type="task-yoink",
                    object_id=task.id,
                    message=f"Yoinked task {task.content_object} from {old_handler.discord}",
                )
            )
        else:
            logs.append(
                HqLog(
                    handler=request.handler,
                    event_type="task-claim",
                    object_id=task.id,
                    message=f"Claimed task {task.content_object}",
                )
            )

        # TODO: This is a hack, and assumes that the update will succeed
        if task.content_type.model_class() in (
            spoilr.email.models.Email,
            spoilr.hints.models.Hint,
            spoilr.interaction.models.InteractionAccessTask,
        ):
            obj = task.content_object
            if (
                task.content_type.model_class()
                == spoilr.interaction.models.InteractionAccessTask
            ):
                obj = task.content_object.interaction_access
            # FIXME(update): Update this logic for your hunt
            # We sent discord bot messages here.
            # dispatch_bot_alert(obj.claimed_discord_message(request.handler))

    Task.objects.bulk_update(
        tasks, ["claim_time", "handler", "status", "snooze_time", "snooze_until"]
    )
    HqLog.objects.bulk_create(logs)

    # Redirect to this task (hint or interaction etc)
    query_params = {}
    if redirect_id:
        query_params[tasks[0].content_type.model] = redirect_id

    verb = "yoinked" if yoink else "claimed"
    return redirect_with_message(
        request,
        "spoilr.hq:dashboard",
        f"Tasks {verb}." if len(tasks) > 1 else f"Task {verb}.",
        anchor=anchor,
        **query_params,
    )


@require_POST
@hq(require_handler=True)
def task_unclaim_view(request):
    task_ids = request.POST.getlist("task_id")
    tasks = Task.objects.filter(id__in=task_ids)
    if not len(tasks):
        return redirect_with_message(
            request, "spoilr.hq:dashboard", "No tasks selected."
        )

    if any(task.handler != request.handler for task in tasks):
        return redirect_with_message(
            request, "spoilr.hq:dashboard", f"You are no longer handling the task(s)."
        )

    if any(task.status == TaskStatus.DONE for task in tasks):
        return redirect_with_message(
            request, "spoilr.hq:dashboard", "Task(s) are already done."
        )

    logs = []
    for task in tasks:
        task.claim_time = None
        task.handler = None

        task.status = TaskStatus.PENDING
        task.snooze_time = None
        task.snooze_until = None

        logs.append(
            HqLog(
                handler=request.handler,
                event_type="task-unclaim",
                object_id=task.id,
                message=f"Unclaimed task {task.content_object}",
            )
        )

        # TODO: This is a hack, and assumes that the update will succeed
        if task.content_type.model_class() in (
            spoilr.email.models.Email,
            spoilr.hints.models.Hint,
            spoilr.interaction.models.InteractionAccessTask,
        ):
            obj = task.content_object
            if (
                task.content_type.model_class()
                == spoilr.interaction.models.InteractionAccessTask
            ):
                obj = task.content_object.interaction_access
            dispatch_bot_alert(obj.unclaimed_discord_message())

    Task.objects.bulk_update(
        tasks, ["claim_time", "handler", "status", "snooze_time", "snooze_until"]
    )
    HqLog.objects.bulk_create(logs)

    return redirect_with_message(
        request,
        "spoilr.hq:dashboard",
        "Tasks unclaimed." if len(tasks) > 1 else "Task unclaimed",
    )


@require_POST
@hq(require_handler=True)
def task_snooze_view(request):
    task_ids = request.POST.getlist("task_id")
    tasks = Task.objects.filter(id__in=task_ids)
    snooze_hours = float(request.POST.get("snooze_hours"))
    if not len(tasks):
        return redirect_with_message(
            request, "spoilr.hq:dashboard", "No tasks selected."
        )
    if not snooze_hours or not (0 < snooze_hours <= 24):
        return HttpResponseBadRequest("Missing or invalid fields")

    if any(task.handler and task.handler != request.handler for task in tasks):
        return redirect_with_message(
            request, "spoilr.hq:dashboard", f"You are no longer handling the task(s)."
        )
    if any(task.status == TaskStatus.DONE for task in tasks):
        return redirect_with_message(
            request, "spoilr.hq:dashboard", "Task(s) are already done."
        )

    logs = []
    for task in tasks:
        task.claim_time = task.claim_time if task.handler == request.handler else now()
        task.handler = request.handler

        task.status = TaskStatus.SNOOZED
        task.snooze_time = now()
        task.snooze_until = task.snooze_time + datetime.timedelta(hours=snooze_hours)

        logs.append(
            HqLog(
                handler=request.handler,
                event_type="task-snoozed",
                object_id=task.id,
                message=f"Snoozed task {task.content_object} for {snooze_hours:.2f} hour(s)",
            )
        )

    Task.objects.bulk_update(
        tasks, ["claim_time", "handler", "status", "snooze_time", "snooze_until"]
    )
    HqLog.objects.bulk_create(logs)

    return redirect_with_message(
        request,
        "spoilr.hq:dashboard",
        "Tasks snoozed." if len(tasks) > 1 else "Task snoozed.",
    )


@require_POST
@hq(require_handler=True)
def task_ignore_view(request):
    confirm = request.POST.get("confirm")
    if confirm.lower() != "dismiss":
        return redirect_with_message(
            request, "spoilr.email:dashboard", "Task was not dismissed."
        )

    task_id = request.POST.get("task_id")
    task = Task.objects.get(id=task_id) if task_id else None
    if not task:
        return HttpResponseBadRequest("Missing or invalid fields")

    if not task.handler or task.handler != request.handler:
        return redirect_with_message(
            request, "spoilr.hq:dashboard", f"You are no longer handling this task."
        )
    if task.status == TaskStatus.DONE:
        return redirect_with_message(
            request, "spoilr.hq:dashboard", "Task is already done."
        )

    task.status = TaskStatus.IGNORED
    task.snooze_time = None
    task.snooze_until = None
    task.save()

    HqLog.objects.create(
        handler=request.handler,
        event_type="task-ignored",
        object_id=task_id,
        message=f"Ignored task {task.content_object}",
    )

    return redirect_with_message(request, "spoilr.hq:dashboard", "Task dismissed.")
