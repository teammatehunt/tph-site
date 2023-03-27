from django.apps import AppConfig


class RegistrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "spoilr.registration"

    # Override the prefix for database model tables.
    label = "spoilr_registration"
