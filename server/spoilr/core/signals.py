from django.db.models.signals import post_save
from django.dispatch import receiver

from .api.cache import nuke_cache
from .models import HuntSetting


@receiver(post_save, sender=HuntSetting)
def on_hunt_setting_changed(sender, instance, created, **kwargs):
    # Clear the cache when hunt settings have changed
    nuke_cache()
