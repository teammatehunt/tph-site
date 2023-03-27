"""Business logic for querying or updating the hunt state."""
import logging
from functools import lru_cache

from django.conf import settings
from django.utils.timezone import now
from spoilr.core.models import (
    HuntSetting,
    Interaction,
    InteractionAccess,
    PuzzleAccess,
    RoundAccess,
    Team,
)

from .cache import clear_memoized_cache, memoized_cache
from .events import HuntEvent, dispatch

logger = logging.getLogger(__name__)

CONFIG_CACHE_BUCKET = "config"
HUNT_REF = "hunt"

TEAM_VISIT_INTERACTION_SLUG_FORMAT = "team-visit-{}"


@memoized_cache(CONFIG_CACHE_BUCKET)
def get_site_launch_time(site_ref=HUNT_REF):
    setting, _ = HuntSetting.objects.get_or_create(
        name=f"spoilr.{site_ref}.launch_time"
    )
    return setting.date_value


@memoized_cache(CONFIG_CACHE_BUCKET)
def get_site_end_time(site_ref=HUNT_REF):
    setting, _ = HuntSetting.objects.get_or_create(name=f"spoilr.{site_ref}.end_time")
    return setting.date_value


@memoized_cache(CONFIG_CACHE_BUCKET)
def get_site_close_time(site_ref=HUNT_REF):
    setting, _ = HuntSetting.objects.get_or_create(name=f"spoilr.{site_ref}.close_time")
    return setting.date_value


def is_site_launched(site_ref=HUNT_REF):
    site_launch_time = get_site_launch_time(site_ref)
    return site_launch_time and site_launch_time <= now()


def is_site_over(site_ref=HUNT_REF):
    end_time = get_site_end_time(site_ref)
    return end_time and end_time <= now()


def is_site_closed(site_ref=HUNT_REF):
    close_time = get_site_close_time(site_ref)
    return not settings.IS_POSTHUNT and close_time and close_time <= now()


@clear_memoized_cache(CONFIG_CACHE_BUCKET)
def launch_site(site_ref=HUNT_REF):
    setting, _ = HuntSetting.objects.get_or_create(
        name=f"spoilr.{site_ref}.launch_time"
    )
    if setting.date_value is None:
        setting.date_value = now()
        setting.save()
    dispatch(
        HuntEvent.HUNT_SITE_LAUNCHED,
        site_ref=site_ref,
        message=f"Launched site {site_ref} at {setting.date_value}",
    )


@memoized_cache(CONFIG_CACHE_BUCKET)
def is_site_solutions_published(site_ref=HUNT_REF):
    setting, _ = HuntSetting.objects.get_or_create(
        name=f"spoilr.{site_ref}.solutions_released"
    )
    if setting.boolean_value is None:
        setting.boolean_value = False
        setting.save()
    return setting.boolean_value


def release_round(team, round):
    """Release a round to a team, including superrounds."""
    if round.superround:
        return release_rounds(team, [round, round.superround])
    round_access, created = RoundAccess.objects.get_or_create(team=team, round=round)
    if created:
        logger.info("released %s/round/%s", team.username, round.slug)
        dispatch(
            HuntEvent.ROUND_RELEASED,
            team=team,
            round=round,
            object_id=round.slug,
            round_access=round_access,
            message=f'Released round "{round}"',
        )
    return round_access


def release_rounds(team, rounds):
    """Release many rounds to a team."""
    # We need to verify that all superrounds are included in the release call, since the _release_many code
    # is agnostic to the model.
    all_rounds = set(rounds)
    for round in rounds:
        if round.superround and round.superround not in all_rounds:
            all_rounds.add(round.superround)
    _release_many(
        team,
        all_rounds,
        "round",
        RoundAccess,
        HuntEvent.ROUND_RELEASED,
    )


def release_puzzle(team, puzzle):
    """Release a puzzle to a team."""
    puzzle_access, created = PuzzleAccess.objects.get_or_create(
        team=team, puzzle=puzzle
    )
    if created:
        logger.info("released %s/puzzle/%s", team.username, puzzle.slug)
        dispatch(
            HuntEvent.METAPUZZLE_RELEASED
            if puzzle.is_meta
            else HuntEvent.PUZZLE_RELEASED,
            team=team,
            puzzle=puzzle,
            puzzle_access=puzzle_access,
            object_id=puzzle.slug,
            message=f"Released {puzzle}",
        )
    return puzzle_access


def release_puzzle_all_teams(puzzle):
    """Release a puzzle to every team."""
    _release_many_teams(puzzle, "puzzle", PuzzleAccess, HuntEvent.PUZZLE_RELEASED)


def release_puzzles(team, puzzles):
    """Release many puzzles to a team."""
    _release_many(team, puzzles, "puzzle", PuzzleAccess, HuntEvent.PUZZLE_RELEASED)


def release_interaction(team, interaction, *, reopen=False, request_comments=None):
    """Release an interaction to a team, or update comments if it exists already."""
    interaction_access, created = InteractionAccess.objects.update_or_create(
        team=team,
        interaction=interaction,
        defaults={"request_comments": request_comments},
    )
    if created:
        logger.info("released %s/interaction/%s", team.username, interaction.slug)
        dispatch(
            HuntEvent.INTERACTION_RELEASED,
            team=team,
            interaction=interaction,
            interaction_access=interaction_access,
            object_id=interaction.slug,
            message=f'Released interaction "{interaction}"',
        )
    elif not created and reopen:
        interaction_access.accomplished = False
        interaction_access.accomplished_time = None
        interaction_access.save()
        logger.info("reopened %s/interaction/%s", team.username, interaction.slug)
        dispatch(
            HuntEvent.INTERACTION_REOPENED,
            team=team,
            interaction=interaction,
            interaction_access=interaction_access,
            object_id=interaction.slug,
            message=f'Reopened interaction "{interaction}"',
        )
    return interaction_access


def release_interactions(team, interactions):
    """Release many interactions to a team."""
    _release_many(
        team,
        interactions,
        "interaction",
        InteractionAccess,
        HuntEvent.INTERACTION_RELEASED,
    )


def accomplish_interaction(*, interaction_access=None, team=None, interaction=None):
    """Mark an interaction as completed by a team."""
    if not interaction_access:
        assert team and interaction
        interaction_access = InteractionAccess.objects.get(
            team=team, interaction=interaction
        )
    team = interaction_access.team
    interaction = interaction_access.interaction

    if interaction_access.accomplished:
        return

    interaction_access.accomplished = True
    interaction_access.accomplished_time = now()
    interaction_access.save()

    logger.info(
        "accomplished interaction %s/interaction/%s", team.username, interaction.slug
    )
    dispatch(
        HuntEvent.INTERACTION_ACCOMPLISHED,
        team=team,
        interaction=interaction,
        interaction_access=interaction_access,
        object_id=interaction.slug,
        message=f'Accomplished interaction "{interaction}"',
    )


def _release_many_teams(model, model_name, AccessModel, event_type):
    existing_ids = set(
        [access.team_id for access in AccessModel.objects.filter(**{model_name: model})]
    )

    missing_accesses = [
        AccessModel(team=team, **{model_name: model})
        for team in Team.objects.exclude(id__in=existing_ids)
    ]
    AccessModel.objects.bulk_create(missing_accesses)

    for access in missing_accesses:
        model = getattr(access, model_name)
        logger.info(f"released {access.team.username}/{model_name}/{model.slug}")
        dispatch(
            event_type,
            team=access.team,
            **{model_name: model, f"{model_name}_access": access},
            object_id=model.slug,
            message=f'Released {model_name} "{model}"',
        )


def _release_many(team, models, model_name, AccessModel, event_type):
    existing_ids = set(
        [
            getattr(access, f"{model_name}_id")
            for access in AccessModel.objects.filter(
                team=team, **{f"{model_name}__in": models}
            )
        ]
    )

    missing_accesses = [
        AccessModel(team=team, **{model_name: model})
        for model in models
        if model.id not in existing_ids
    ]
    AccessModel.objects.bulk_create(missing_accesses)

    for access in missing_accesses:
        model = getattr(access, model_name)
        logger.info(f"released {team.username}/{model_name}/{model.slug}")
        dispatch(
            event_type,
            team=team,
            **{model_name: model, f"{model_name}_access": access},
            object_id=model.slug,
            message=f'Released {model_name} "{model}"',
        )


@lru_cache(maxsize=None)
def _get_team_visit_interaction(visit_num):
    slug = TEAM_VISIT_INTERACTION_SLUG_FORMAT.format(visit_num)
    return Interaction.objects.get(slug=slug)


def release_team_visit_interactions(visit_num):
    teams_with_at_least_one_solved = Team.objects.exclude(
        team__last_solve_time__isnull=True
    )
    interaction = _get_team_visit_interaction(visit_num)
    for team in teams_with_at_least_one_solved:
        release_interaction(team, interaction)

    return [team.name for team in teams_with_at_least_one_solved]
