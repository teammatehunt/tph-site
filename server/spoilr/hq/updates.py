import datetime

import spoilr.core.models as models
from django.conf import settings
from django.shortcuts import redirect, render
from django.utils.timezone import now
from spoilr.core.api.events import HuntEvent, dispatch
from spoilr.email.utils import send_email
from spoilr.hq.util.decorators import hq

UPDATE_EMAIL_TEMPLATE = "hqupdate_email"


def send_email_for_update(update):
    team_and_emails = update.recipients

    sent_datetime = max(now(), update.publish_time)
    # Send 1 email per team.
    for team, emails in team_and_emails:
        if not emails:
            continue
        send_email(
            update.subject,
            UPDATE_EMAIL_TEMPLATE,
            {"update": update},
            emails,
            is_prehunt=False,
            sent_datetime=sent_datetime,
        )
        sent_datetime += datetime.timedelta(milliseconds=settings.EMAIL_BATCH_DELAY)

    return [team for team, _ in team_and_emails]


@hq(require_handler=True)
def updates_view(request):
    if request.method == "POST":
        updates_to_publish = models.HQUpdate.objects.filter(
            id__in=request.POST.getlist("update_ids"),
            published=False,
        )
        for update in updates_to_publish:
            update.publish_time = now()
            update.published = True
            update.save()
            if update.send_email:
                teams = send_email_for_update(update)
            elif update.team:
                teams = [update.team]
            else:
                teams = []

            dispatch(
                HuntEvent.UPDATE_SENT,
                update=update,
                teams=teams,
                puzzle=update.puzzle,
                message=f"HQ update sent {update.subject}",
            )
        return redirect(request.path)

    hqupdates = models.HQUpdate.objects.order_by("-creation_time")
    context = {"updates": hqupdates}
    return render(request, "hq/updates.html", context)
