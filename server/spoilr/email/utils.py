from spoilr.core.models import PuzzleAccess, Team


def get_all_emails(unlocked_puzzle=None):
    """Retrieves all emails based on given constraints, grouped by team"""

    if unlocked_puzzle is None:
        teams = Team.objects.all()
    else:
        unlocks = PuzzleAccess.objects.filter(
            puzzle_id=unlocked_puzzle.id
        ).select_related("team")
        teams = [unlock.team for unlock in unlocks]
    return [(team, team.all_emails) for team in teams]


def send_email(*args, **kwargs):
    # FIXME(update): Update this logic for your hunt
    # send_mail_wrapper(*args, **kwargs)
    pass
