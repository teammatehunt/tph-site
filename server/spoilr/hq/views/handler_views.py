from django.conf import settings
from django.db.models import Count, Q
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render, reverse
from django.utils.timezone import now
from django.views.decorators.http import require_POST
from spoilr.hq.models import Handler, TaskStatus
from spoilr.hq.util.decorators import hq


@require_POST
@hq()
def handler_sign_in_view(request):
    name = request.POST.get("name")
    discord = request.POST.get("discord")
    phone = request.POST.get("phone")
    if not name or not discord:
        return HttpResponseBadRequest("Missing required fields")

    handler, _ = Handler.objects.update_or_create(
        discord__iexact=discord,
        defaults={
            "name": name,
            "discord": discord,
            "phone": phone,
            "activity_time": now(),
            "sign_in_time": now(),
        },
    )
    request.session["handler_id"] = handler.id
    request.session.save()

    next_url = request.META.get("HTTP_REFERER")
    return redirect(next_url or reverse("spoilr.hq:dashboard"))


@hq()
def handler_sign_out_view(request):
    discord = request.GET.get("discord")
    maybe_handler = Handler.objects.filter(discord__iexact=discord).first()
    if maybe_handler:
        maybe_handler.sign_in_time = None
        maybe_handler.save()

    next_url = request.META.get("HTTP_REFERER")
    return redirect(next_url or reverse("spoilr.hq:dashboard"))


@hq()
def handler_stats(request):
    handlers = Handler.objects.annotate(
        num_hints=Count(
            "task",
            filter=Q(task__content_type__model="hint", task__status=TaskStatus.DONE),
        ),
        num_emails=Count(
            "task",
            filter=Q(task__content_type__model="email", task__status=TaskStatus.DONE),
        ),
        num_interactions=Count(
            "task",
            filter=Q(
                task__content_type__model="interactionaccesstask",
                task__status=TaskStatus.DONE,
            ),
        ),
    ).all()

    return render(request, "hq/handler_stats.html", {"handler_stats": handlers})
