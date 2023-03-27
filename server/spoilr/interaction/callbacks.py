from django.conf import settings

from spoilr.core.api.events import HuntEvent, register, dispatch

# TODO: consider converting to a signal
def on_interaction_released(interaction_access, **kwargs):
    from spoilr.hq.models import Task, TaskStatus
    from spoilr.interaction.models import InteractionAccessTask

    # We may re-open interaction tasks for certain interactions like answer unlocks.
    iat, _ = InteractionAccessTask.objects.get_or_create(
        interaction_access=interaction_access
    )
    task = iat.tasks.first()
    if task:
        task.status = TaskStatus.PENDING
        task.handler = None
        task.snooze_time = None
        task.snooze_until = None
        task.save()
    else:
        iat.tasks.add(Task(), bulk=False)


def on_tick(last_tick, **kwargs):
    from spoilr.core.models import InteractionAccess
    from spoilr.hq.models import Task, TaskStatus
    from spoilr.email.models import Email

    # If an email was received for a snoozed interaction, and unsnooze it.
    messages = Email.objects.filter(team__isnull=False, interaction__isnull=False)
    if last_tick:
        messages = messages.filter(received_datetime__gte=last_tick)

    for message in messages:
        interaction_access = (
            InteractionAccess.objects.prefetch_related("interactionaccesstask__tasks")
            .filter(team=message.team, interaction=message.interaction)
            .filter(
                interactionaccesstask__tasks__isnull=False,
                interactionaccesstask__tasks__status=TaskStatus.SNOOZED,
                interactionaccesstask__tasks__snooze_time__lte=message.received_datetime,
            )
            .first()
        )
        if interaction_access:
            task = interaction_access.interactionaccesstask.tasks.first()
            task.status = TaskStatus.PENDING
            task.snooze_time = None
            task.snooze_until = None
            task.handler = None
            task.claim_time = None
            task.save()

            dispatch(
                HuntEvent.TASK_UNSNOOZED,
                team=message.team,
                object_id=task.id,
                message=f"Unsnoozed task {task.content_object}",
            )


register(HuntEvent.INTERACTION_RELEASED, on_interaction_released)
register(HuntEvent.INTERACTION_REOPENED, on_interaction_released)
register(HuntEvent.HUNT_TICK, on_tick)
