import logging

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from spoilr.core.api.hunt import release_interaction
from spoilr.core.models import InteractionType

from puzzles.views.auth import restrict_access, validate_puzzle

logger = logging.getLogger(__name__)


# Note: Assume that interactions and puzzles share the same slug.
@require_POST
@validate_puzzle(require_team=True)
@restrict_access(after_hunt_end=False)
def request_interaction(request):
    team = request.context.team
    if not team:
        return JsonResponse(
            {"message": "You must be logged in to request an interaction."}, status=404
        )

    puzzle = request.context.puzzle
    interaction = puzzle.interaction_set.filter(
        interaction_type=InteractionType.PHYSICAL
    ).first()
    if not interaction:
        return JsonResponse({"message": "This interaction does not exist."}, status=404)

    comments = request.POST.get("comments")
    release_interaction(team, interaction, request_comments=comments)
    return JsonResponse(
        {
            "message": "Your request has been confirmed. We will contact you as soon as we can."
        },
        status=201,
    )
