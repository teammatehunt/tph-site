import datetime

from django.conf import settings
from django.utils import timezone

# This is not ideal, but our answer handling is a bit hunt specific.
# In the future, consider hooking into spoilr properly.
from spoilr.core.api.answer import (
    _handle_puzzle_correct_answer,
    _handle_puzzle_incorrect_answer,
)
from spoilr.core.api.hunt import get_site_end_time

from puzzles.hunt_config import EVENTS_ROUND_SLUG
from puzzles.models import PuzzleSubmission, build_guess_data
from puzzles.rounds import CUSTOM_ROUND_VALIDATORS
from puzzles.rounds.utils import SKIP_ROUNDS

# Set of rounds that allow empty submissions
ROUNDS_ALLOW_EMPTY_SUBMISSIONS = {}
ROUNDS_SHOW_EXACT_ANSWER = {}


def process_guess(solve_time, team, puzzle, normalized_answer, used_free_answer=False):
    correct = used_free_answer or puzzle.is_correct(normalized_answer, team)
    if team.is_admin and normalized_answer == settings.SPOILR_ADMIN_MAGIC_ANSWER:
        correct = True
    answer_submission = PuzzleSubmission(
        team_id=team.id,
        puzzle_id=puzzle.id,
        # NB: the "normalized" answer might not match the expected display for some
        # special rounds due to illegal round gimmicks. Just show the correct answer
        # as displayed in our database if it's correct. This has the side effect
        # of adding spaces where applicable, but it's fine if it's consistent.
        answer=puzzle.answer
        if correct and puzzle.round.slug not in ROUNDS_SHOW_EXACT_ANSWER
        else normalized_answer,
        correct=correct,
        used_free_answer=used_free_answer,
    )
    guess_data = build_guess_data(answer_submission)
    if guess_data["partial"]:
        answer_submission.partial = True
    # Return response for public teams without saving
    if team.is_public and not settings.IS_PYODIDE:
        return guess_data

    answer_submission.save()

    if correct:
        puzzle.on_solved(team)

        if solve_time < get_site_end_time():
            team.last_solve_time = solve_time
            team.save()
            # report the answer correct submission to spoilr: see note about changing this in the future
            _handle_puzzle_correct_answer(team.spoilr_team, puzzle.spoilr_puzzle)

        # Check if any puzzles unlocked
        # Because deep has likely changed, we can't use any cached values.
        team.unlock_puzzles(team.compute_deep(team.correct_puzzle_submissions()))
    else:
        _handle_puzzle_incorrect_answer(
            team.spoilr_team, puzzle.spoilr_puzzle, normalized_answer
        )

    return guess_data


def get_ratelimit(puzzle, team, puzzle_submissions=None):
    from puzzles.rounds import CUSTOM_RATE_LIMITERS

    if puzzle_submissions is None:
        puzzle_submissions = PuzzleSubmission.objects.filter(
            team_id=team.id,
            puzzle_id=puzzle.id,
        )
    assert all(
        submission.team_id == team.id and submission.puzzle_id == puzzle.id
        for submission in puzzle_submissions
    )
    curr_time = timezone.now()
    guesses_made = sorted(
        [submission for submission in puzzle_submissions],
        key=lambda submission: submission.timestamp,
    )

    rate_limit = CUSTOM_RATE_LIMITERS.get(
        puzzle.round.slug, lambda i: datetime.timedelta(minutes=i**2 / 1.5)
    )
    expiration = max(
        (
            submission.timestamp + rate_limit(i)
            for i, submission in enumerate(
                guess
                for guess in reversed(guesses_made)
                # Filter out partial or correct guesses
                if not (guess.partial or guess.correct)
            )
        ),
        default=None,
    )

    should_limit = expiration is not None and expiration >= curr_time
    data = {
        "shouldLimit": should_limit,
        "guessesMade": [g.answer for g in guesses_made],
    }
    if should_limit:
        # Adding a small buffer to the submit time. This should guarantee that
        # by the time countdown expires, the server will be ready to respond to
        # guesses.
        data["secondsToWait"] = (
            expiration + datetime.timedelta(seconds=1) - timezone.now()
        ).total_seconds()
    return data


def submit_answer(
    puzzle,
    team,
    guess="",
    puzzle_answer=None,
    guesses_remaining=None,
    puzzle_submissions=None,
    submission_time=None,
):
    if not puzzle_answer:
        puzzle_answer = team.puzzle_answer(puzzle)
    if not guesses_remaining:
        guesses_remaining = team.guesses_remaining(puzzle)
    if not puzzle_submissions:
        puzzle_submissions = team.puzzle_submissions(puzzle)
    if not submission_time:
        submission_time = timezone.now()

    guess_data = None
    error_msg = ""
    normalized_guess = puzzle.normalize_answer(guess, team)
    ratelimit_data = get_ratelimit(puzzle, team)
    status = 200

    if team.is_admin and normalized_guess == settings.SPOILR_ADMIN_MAGIC_ANSWER:
        normalized_guess = puzzle.normalized_answer

    # Filter out illegitimate guesses
    if puzzle_answer:
        error_msg = "You've already solved this puzzle!"
        status = 400
    elif guesses_remaining <= 0:
        error_msg = "You have no more guesses for this puzzle!"
        status = 400
    elif (
        not normalized_guess and puzzle.round.slug not in ROUNDS_ALLOW_EMPTY_SUBMISSIONS
    ):
        error_msg = "Sorry, your submission was invalid. Please try again."
        status = 400
    elif len(normalized_guess) > 500:
        error_msg = "Please limit your guess to 500 characters maximum."
        status = 400
    elif ratelimit_data["shouldLimit"]:
        # Client writes custom error message so we don't need one here
        # (This shouldn't really happen anyway since client stops teams from
        # submitting if they're rate-limited)
        status = 429
    else:
        tried_before = any(
            normalized_guess == submission.answer for submission in puzzle_submissions
        )
        if tried_before:
            error_msg = f'You\'ve already tried calling in the answer "{normalized_guess}" for this puzzle.'
            status = 400
        elif puzzle.round.slug in CUSTOM_ROUND_VALIDATORS:
            error_msg = CUSTOM_ROUND_VALIDATORS[puzzle.round.slug](
                normalized_guess, puzzle_submissions, slug=puzzle.slug
            )
            if error_msg:
                status = 400

    if status == 200:
        # Yay, a legitimate guess
        guess_data = process_guess(submission_time, team, puzzle, normalized_guess)
        if not guess_data["isCorrect"]:
            ratelimit_data = get_ratelimit(puzzle, team)
        if ratelimit_data["shouldLimit"]:
            # Was a valid guess, but now we are limited.
            ratelimit_data["justLimited"] = True
            status = 429

    return guess_data, status, error_msg, ratelimit_data


def get_allowed_free_puzzles(request):
    # Ignore solved puzzles
    slugs_to_exclude = {
        submission.puzzle.slug
        for submission in request.context.correct_puzzle_submissions
    }

    rounds_to_exclude = {*SKIP_ROUNDS}
    return [
        puzzle
        for puzzle in request.context.puzzle_unlocks
        if puzzle.slug not in slugs_to_exclude
        and puzzle.round.slug not in rounds_to_exclude
        and not puzzle.is_meta
        and puzzle.round.act <= 2
    ]


def get_allowed_a3_free_puzzles(request):
    # Poorly named - works on anything aside from a few crazy things
    # Ignore solved puzzles
    slugs_to_exclude = {
        submission.puzzle.slug
        for submission in request.context.correct_puzzle_submissions
    }
    rounds_to_exclude = {*SKIP_ROUNDS}
    return [
        puzzle
        for puzzle in request.context.puzzle_unlocks
        if puzzle.slug not in slugs_to_exclude
        and puzzle.round.slug not in rounds_to_exclude
        and not puzzle.is_meta
    ]
