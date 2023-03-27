from django.apps import AppConfig


class SpoilrHintsConfig(AppConfig):
    name = "spoilr.hints"

    # Override the prefix for database model tables.
    label = "spoilr_hints"

    def ready(self):
        # Connect the signal handlers registered in signals
        from . import signals
