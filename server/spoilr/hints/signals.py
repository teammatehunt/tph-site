from django.db.models.signals import post_save
from django.dispatch import receiver
from spoilr.hq.models import Task
from .models import Hint

# Be aware that if the hint is not created in a transaction then the hint can be committed without an associated task.
# While this is a race, it is not expected to cause any issues or errors so long as the task is eventually created.
@receiver(post_save, sender=Hint)
def on_hint_requested(sender, instance, created, **kwargs):
    if created and instance.is_request:
        instance.tasks.add(Task(), bulk=False)
