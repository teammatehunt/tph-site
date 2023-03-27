from django.db.models.signals import post_save
from django.dispatch import receiver
from spoilr.hq.models import Task
from .models import Email
from .callbacks import should_create_email_tasks


@receiver(post_save, sender=Email)
def on_email_received(sender, instance, created, **kwargs):
    if (
        should_create_email_tasks()
        and created
        and not instance.interaction
        and not instance.is_from_us
    ):
        instance.tasks.add(Task(), bulk=False)
