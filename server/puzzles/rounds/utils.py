import os
from collections import Counter, defaultdict

from puzzles.assets import get_hashed_url
from puzzles.hunt_config import EVENTS_ROUND_SLUG, META_META_SLUGS

ROUND_DIRECTORY = "Rounds/"

SKIP_ROUNDS = EVENTS_ROUND_SLUG

# TODO: Ideally all round-specific logic should live in the database instead of this map.
ROUND_POSITIONS = {
    "intro": {"x": 5, "y": 10, "width": 12},
}

ROUND_EMOJIS = {
    "intro": "🎟️",
}
SOLVE_SOUNDS_DIRECTORY = "Solve Sounds"
SOLVE_SOUNDS = {
    "intro": get_hashed_url(os.path.join(SOLVE_SOUNDS_DIRECTORY, "intro.mp3")),
}


def get_round_emoji(puzzle_round):
    if puzzle_round.slug in ROUND_EMOJIS:
        return ROUND_EMOJIS.get(puzzle_round.slug)
    if puzzle_round.superround:
        return ROUND_EMOJIS.get(puzzle_round.superround.slug, "")
    return ""


def get_solve_sound(puzzle_round):
    if puzzle_round.slug in SOLVE_SOUNDS:
        return SOLVE_SOUNDS.get(puzzle_round.slug)
    if puzzle_round.superround:
        return SOLVE_SOUNDS.get(puzzle_round.superround.slug, None)
    return None


def rounds_by_act(all_rounds, skip_acts=None):
    """Merges subrounds into flattened list, and returns list of rounds by act."""
    acts = []
    # Assumes rounds are sorted by act.
    for puzzle_round in all_rounds:
        # Filter out subrounds
        if puzzle_round.superround_id:
            continue
        # Filter out events.
        if puzzle_round.slug in SKIP_ROUNDS:
            continue
        # Filter out skipped acts
        if skip_acts and puzzle_round.act in skip_acts:
            continue
        # At this point it's required that we will 100% add whatever round we
        # are iterating, to guarantee each act-list is non-empty after each
        # for-loop iteration.
        if not acts or acts[-1][-1].act != puzzle_round.act:
            acts.append([])
        acts[-1].append(puzzle_round)
    return acts


def get_round_data(request, puzzle_round, team, puzzle=None, images=None):
    """Helper method to retrieve round specific metadata."""
    round_images = get_image_urls(request, puzzle_round, images=images)

    data = {
        "act": puzzle_round.act,
        "slug": puzzle_round.slug,
        "name": puzzle_round.name,
        "url": puzzle_round.url,
    }
    if puzzle_round.superround:
        # For subrounds, don't leak the subround this puzzle is in.
        # Except in wyrm we want to leak subround slugs for frontend reasons. It's
        # not really a spoiler, but we still want to override the name and URL
        # with the superround slug.
        data["slug"] = puzzle_round.superround.slug
        data["name"] = puzzle_round.superround.name
        data["url"] = puzzle_round.superround.url

    if puzzle:
        # Only send the minimal assets needed on a puzzle page.
        data["wordmark"] = round_images["wordmark"]
        data["header"] = round_images["header"]
        data["background"] = round_images["background"]
        data["favicon"] = round_images["favicon"]
    else:
        for image_type, url in round_images.items():
            data[image_type] = url

    return data


def get_icons(request, puzzle, unlock):
    # Build a dict of what properties the puzzle has, then use that to filter.
    # Return a list of icons we want to retrieve.
    # Not all puzzles are guaranteed to have puzzle.solved_icon.name defined.
    solved = "answer" in unlock
    icons = {}
    puzzle_dir = get_round_images(puzzle.round, "puzzles", str(puzzle.pk))
    default_icon_path = os.path.join(puzzle_dir, "default.png")
    solved_icon_path = os.path.join(puzzle_dir, "solved.png")
    unsolved_icon_path = os.path.join(puzzle_dir, "unsolved.png")

    if request.context.hunt_is_over and request.context.team is None:
        # Retrieve all icons.
        icons["solved"] = solved_icon_path
        icons["unsolved"] = unsolved_icon_path
    elif solved:
        icons["solved"] = solved_icon_path
    else:
        icons["unsolved"] = unsolved_icon_path
    # Only include icons with defined URLs
    return {
        k: get_hashed_url(image_url) or get_hashed_url(default_icon_path)
        for k, image_url in icons.items()
    }


def alphanumeric_name(name):
    return "".join(c for c in name.lower() if c.isalnum())


def default_round_sort_key(unlock):
    # Group by metameta, then capstone, then meta, then alpha
    puzzle = unlock["puzzle"]
    is_metameta = puzzle.slug in META_META_SLUGS
    # False < True in Python, some need to be inverted.
    return (
        not is_metameta,
        not puzzle.is_meta,
        alphanumeric_name(puzzle.name),
        puzzle.deep,
    )


def get_round_puzzles(request, round_slug=None):
    """
    Helper method to fetch round data and unlocked puzzles for a round page,
    or the all puzzles page (if no round_slug is passed).
    """
    team = request.context.team
    rounds = {}
    if not team:
        return rounds

    if round_slug:
        unlocked_rounds = team.unlocked_rounds()
        try:
            puzzle_round = next(
                round_ for round_ in unlocked_rounds if round_.slug == round_slug
            )
        except StopIteration:
            return {}

        rounds[puzzle_round.slug] = puzzle_round

    solved = {
        submission.puzzle_id: submission.answer
        for submission in team.puzzlesubmission_set.filter(correct=True).all()
    }
    hints = Counter(team.hint_set.values_list("puzzle_id", flat=True))

    unlocks = [{"puzzle": puzzle} for puzzle in request.context.puzzle_unlocks]
    for data in unlocks:
        puzzle_id = data["puzzle"].id
        if puzzle_id in solved:
            data["answer"] = solved[puzzle_id]
        if puzzle_id in hints:
            data["hints"] = hints[puzzle_id]

    puzzles_map = defaultdict(list)

    def sort_key(unlock):
        # Group by round (or superround), then the round's internal sort key.
        puzzle = unlock["puzzle"]
        puzzle_round = puzzle.round.superround or puzzle.round
        return (puzzle_round.order, default_round_sort_key(unlock))

    # This relies on Python 3.7+ behavior that a dictionary's iter order matches
    # the insertion order.
    puzzle_unlocks = sorted(unlocks, key=sort_key)
    for unlock in puzzle_unlocks:
        puzzle = unlock["puzzle"]
        puzzle_round_slug = puzzle.round.slug
        # Skip puzzles in the events round.
        if puzzle_round_slug == EVENTS_ROUND_SLUG:
            continue
        if round_slug:
            # Skip puzzles if they aren't in the specified round.
            if puzzle_round_slug != round_slug:
                continue
        else:
            # For rounds with superrounds, just return one giant list
            superround = puzzle.round.superround or puzzle.round
            puzzle_round_slug = superround.slug
            if puzzle_round_slug not in rounds:
                rounds[puzzle_round_slug] = superround

        puzzle_data = {
            "name": puzzle.name,
            "slug": puzzle.slug,
            "isMeta": puzzle.is_meta,
            "iconURLs": get_icons(request, puzzle, unlock),
            "iconSize": puzzle.icon_size,
            "position": [puzzle.icon_x, puzzle.icon_y],
            "textPosition": [puzzle.text_x, puzzle.text_y],
            "answer": unlock.get("answer"),
            # FIXME: inject url if multiple kinds (eg /events/slug and /puzzles/slug)
            # "url": puzzle.url,
        }
        puzzles_map[puzzle_round_slug].append(puzzle_data)

    # If no puzzles have been unlocked, return 404.
    if not puzzles_map:
        return {}

    return {
        "theme": request.context.site,
        "puzzles": puzzles_map,
        "rounds": {
            slug: get_round_data(request, puzzle_round, team)
            for slug, puzzle_round in rounds.items()
        },
    }


def get_superround_urls(act, image_type=None):
    image = "map.png"
    return get_hashed_url(os.path.join(ROUND_DIRECTORY, "maps", image))


def get_round_positions(act, slug):
    positions = ROUND_POSITIONS
    return positions.get(slug, {})


def get_round_images(puzzle_round, *subdirectories):
    return os.path.join(ROUND_DIRECTORY, puzzle_round.slug, *subdirectories)


def get_image_urls(request, puzzle_round, images=None):
    if not images:
        images = ("header", "footer", "wordmark", "background", "roundart", "favicon")

    round_dir = get_round_images(puzzle_round, "other")
    image_map = {
        image_type: get_hashed_url(os.path.join(round_dir, f"{image_type}.png"))
        for image_type in images
    }
    return image_map
