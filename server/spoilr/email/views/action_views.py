from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from spoilr.core.api.events import dispatch, HuntEvent
from spoilr.email.models import Email
from spoilr.email.forms import AnswerEmailForm
from spoilr.hq.models import HqLog, TaskStatus
from spoilr.hq.util.decorators import hq
from spoilr.hq.util.redirect import redirect_with_message

assert settings.SPOILR_HQ_DEFAULT_FROM_EMAIL, "No default from email"

FROM_EMAIL_DOMAIN = settings.SPOILR_HQ_DEFAULT_FROM_EMAIL[
    settings.SPOILR_HQ_DEFAULT_FROM_EMAIL.rindex("@") :
]


@require_POST
@hq(require_handler=True)
def reply_view(request):
    action = request.POST.get("action")
    if action == AnswerEmailForm.ACTION_NO_REPLY:
        action = "no-reply"
    elif action == "submit":
        action = "submit"
        confirm = request.POST.get("confirm")
        if confirm.lower() != "reply":
            messages.error(request, "Email response was not confirmed.")
            return redirect_with_message(
                request, "spoilr.email:dashboard", "Email reply was not sent."
            )
    else:
        messages.error(request, "Invalid action!")
        return redirect_with_message(
            request, "spoilr.email:dashboard", "Email reply was not sent."
        )

    form = AnswerEmailForm(request.POST)
    if not form.is_valid():
        messages.error(request, f"Form has errors: {form.errors}")
        # TODO: email content won't be maintained across errors, back button needed?
        return redirect_with_message(
            request,
            "spoilr.email:dashboard",
            "Email reply was not sent due to form errors.",
        )

    email_in_reply_to_pk = form.cleaned_data["email_in_reply_to_pk"]
    text_content = form.cleaned_data["text_content"]

    email_in_reply_to = (
        Email.objects.select_related("team").filter(pk=email_in_reply_to_pk).first()
    )
    if not email_in_reply_to:
        messages.error(request, "Email being replied to cannot be found!")
        return redirect_with_message(
            request, "spoilr.email:dashboard", "Email reply was not sent."
        )

    reference_ids = set(
        filter(
            bool,
            (email_in_reply_to.message_id, *email_in_reply_to.reference_ids),
        )
    )
    emails_with_updated_status = Email.objects.filter(
        message_id__in=reference_ids,
        status=Email.RECEIVED_NO_REPLY,
    )

    # Not yet saved
    task = email_in_reply_to.task
    if task:
        task.status = TaskStatus.DONE
        task.snooze_time = None
        task.snooze_until = None

    if action == "no-reply":
        # Redundant with the update call, but needs to be set on the object
        # for dispatch alert to work correctly.
        email_in_reply_to.status = Email.RECEIVED_NO_REPLY_REQUIRED
        with transaction.atomic():
            count = emails_with_updated_status.update(
                status=Email.RECEIVED_NO_REPLY_REQUIRED
            )

            if task:
                task.save()

            def commit_action():
                if count:
                    dispatch(
                        HuntEvent.EMAIL_REPLIED,
                        email_in_reply_to=email_in_reply_to,
                        message=f"Resolved without response email “{email_in_reply_to.id}”",
                    )
                    messages.success(request, "Email resolved.")

            transaction.on_commit(commit_action)

        if not count:
            messages.error(request, "No emails were resolved!")
            return redirect_with_message(
                request, "spoilr.email:dashboard", "Email was not resolved."
            )
        message = "Email resolved."
    else:
        # sending a reply
        email_reply = Email.ReplyEmail(
            email_in_reply_to,
            plain=text_content,
            reply_all=True,
            check_addresses=False,
        )
        with transaction.atomic():
            author = None
            if task:
                task.save()
                author = task.handler

            email_reply.save()
            emails_with_updated_status.update(
                response=email_reply,
                author=author,
                status=Email.RECEIVED_ANSWERED,
            )

            def commit_action():
                dispatch(
                    HuntEvent.EMAIL_REPLIED,
                    email_in_reply_to=email_in_reply_to,
                    email_reply=email_reply,
                    message=f"Replied to email “{email_in_reply_to.id}”",
                )
                messages.success(request, "Email queued.")

            transaction.on_commit(commit_action)
        message = "Email sent."

    HqLog.objects.create(
        handler=request.handler,
        event_type="email-reply",
        object_id=email_in_reply_to.id,
        message=f"Resolved email: {message}",
    )

    return redirect_with_message(request, "spoilr.email:dashboard", message)


@hq(require_handler=True)
def send_view(request):
    if request.method == "POST":
        confirm = request.POST.get("confirm")
        recipient = request.POST.get("recipient")
        sender = request.POST.get("sender")
        subject = request.POST.get("subject")
        body_text = request.POST.get("body")

        error = None
        if not recipient or not sender or not subject or not body_text:
            error = "Missing fields"
        if not sender.endswith(FROM_EMAIL_DOMAIN):
            error = "Can't use that sender"
        if confirm.lower() != "send":
            error = "Did not confirm sending the email"

        if error:
            return render(
                request,
                "hq/email_send.tmpl",
                {
                    "recipient": recipient or "",
                    "sender": sender or "",
                    "subject": subject or "",
                    "body_text": body_text or "",
                    "error": error,
                },
            )

        send_mail(subject, body_text, sender, [recipient])

        # FIXME(update): This is not the proper way to write email. Update this like the dashboard and action views.
        message = Email.objects.create(
            subject=subject,
            body_text=body_text,
            from_address=sender,
            recipient=recipient,
            automated=False,
            handler=request.handler,
        )
        HqLog.objects.create(
            handler=request.handler,
            event_type="email-send",
            object_id=message.id,
            message=f"Sent email {message}",
        )

        return redirect_with_message(request, "spoilr.email:dashboard", "Email sent.")

    return render(
        request,
        "spoilr/email/send.tmpl",
        {
            "recipient": "",
            "sender": settings.SPOILR_HQ_DEFAULT_FROM_EMAIL,
            "subject": "",
            "body_text": "",
        },
    )
