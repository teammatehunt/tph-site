import os
import platform

from tph.constants import IS_PYODIDE


if IS_PYODIDE:
    import pydoc

    class FakeCelery:
        @staticmethod
        def send_task(*args, **kwargs):
            pass

        @staticmethod
        def task(func):
            return func

    celery_app = FakeCelery()


else:

    from celery import Celery, signals

    # set the default Django settings module for the 'celery' program.
    server_environment = os.environ.get("SERVER_ENVIRONMENT", "dev")
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", f"tph.settings.{server_environment}"
    )

    celery_app = Celery("tph")

    # Using a string here means the worker doesn't have to serialize
    # the configuration object to child processes.
    # - namespace='CELERY' means all celery-related configuration keys
    #   should have a `CELERY_` prefix.
    celery_app.config_from_object("django.conf:settings", namespace="CELERY")

    @signals.after_setup_task_logger.connect
    def setup_task_logger(logger, *args, **kwargs):
        logger.setLevel("DEBUG")

    # Load task modules from all registered Django celery_app configs.
    celery_app.autodiscover_tasks()

    @celery_app.task(bind=True)
    def debug_task(self):
        print(f"Request: {self.request!r}")
        return "Task finished!"
