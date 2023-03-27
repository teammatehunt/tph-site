from spoilr.email.models import Email
from django.conf import settings
from django.core.management.base import BaseCommand
from puzzles.celery import celery_app
import datetime as dt


class Command(BaseCommand):
    help = "Requeue all emails with status SENDING so that they are requeued with smeared time."

    def handle(self, *args, **options):
        mails = Email.objects.all().filter(status=Email.SENDING)
        t = dt.datetime.now()
        for mail in mails:
            t = t + dt.timedelta(milliseconds=settings.EMAIL_BATCH_DELAY)
            celery_app.send_task(
                "puzzles.emailing.task_send_email",
                args=[mail.pk],
                eta=t,
            )
        self.stdout.write(
            self.style.SUCCESS(f"Successfully requeued {len(mails)} email(s).")
        )
