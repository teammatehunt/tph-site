from django.db.models.signals import post_save
from django.dispatch import receiver
from spoilr.hq.models import Task, TaskStatus
from spoilr.core.models import InteractionAccess
from .models import InteractionAccessTask


@receiver(post_save, sender=InteractionAccess)
def on_interaction_save(sender, instance, created, **kwargs):

    # We may re-open interaction tasks for certain interactions like answer unlocks.
    iat, _ = InteractionAccessTask.objects.get_or_create(interaction_access=instance)
    task = iat.task
    if task:
        task.status = TaskStatus.PENDING
        task.handler = None
        task.snooze_time = None
        task.snooze_until = None
        task.save()
    else:
        iat.tasks.add(Task(), bulk=False)
