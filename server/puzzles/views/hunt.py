from django.http import JsonResponse
from django.views.decorators.http import require_GET
from spoilr.events.models import Event


@require_GET
def get_events(request):
    events = Event.objects.all().order_by("expected_start_time")
    data = {
        "events": [
            {
                "slug": event.slug if event.status == "post" else "",
                "name": event.name,
                "location": event.location,
                "expected_start_time": event.expected_start_time.isoformat(),
                "min_participants": event.min_participants,
                "max_participants": event.max_participants,
                "description": event.description,
                "status": event.status,
            }
            for event in events
        ]
    }

    team = request.context.team
    if team:
        data["currency"] = request.context.num_event_rewards
        data["strongCurrency"] = request.context.num_a3_event_rewards

    data[
        "info"
    ] = "Each event reward may be redeemed for a non-meta answer in the initial rounds or a puzzle unlock within a round."

    return JsonResponse(data)
