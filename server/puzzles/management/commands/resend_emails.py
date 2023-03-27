from django.core.management.base import BaseCommand
from puzzles.celery import celery_app


class Command(BaseCommand):
    help = "Requeue all emails with status SENDING so that they are requeued with smeared time."

    def handle(self, *args, **options):
        celery_app.send_task("puzzles.emailing.task_resend_emails")
