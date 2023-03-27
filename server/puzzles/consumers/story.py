import functools
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import List

from puzzles.consumers import ClientConsumer
from puzzles.models import Team
from puzzles.models.interactive_cache import SessionCacheManager
from puzzles.models.story import StateEnum, StoryCard, StoryState
from puzzles.story.dialogue_tree import get_dialogue_tree, get_next_state
from puzzles.utils import redis_lock

from .base import BasePuzzleHandler

logger = logging.getLogger(__name__)


EMPIRICAL_READING_SPEED = 5.9  # words per second, based off many (2) data points


@functools.lru_cache(maxsize=50)
def slug_to_storycard_id(slug):
    story_card = StoryCard.objects.get(slug=slug)
    return story_card.id


def get_countdown(node):
    num_words = sum(
        [
            len(s.split(" "))
            for s in [
                node["text"],
                *[s.get("text", "") for s in node["transitions"]],
            ]
        ]
    )
    return timedelta(seconds=math.ceil(9 + num_words / EMPIRICAL_READING_SPEED))


def send_message(user, slug, data=None):
    group = ClientConsumer.get_puzzle_group(user=user, id=user.team_id, slug=slug)
    ClientConsumer.send_event(group, slug, data)


def add_uuid(l: List[str], uuid: str) -> List[str]:
    return list(set(l) | {uuid})


def remove_uuid(l: List[str], uuid: str) -> List[str]:
    return [v for v in l if v != uuid]


def init_timer(session):
    session["state"]["timer"] = (
        datetime.now(tz=timezone.utc) + get_countdown(session["state"]["dialogue"])
    ).isoformat()


def complete_session(slug, session, team):
    SLUG_TO_STORY_STATE = {
        # FIXME: Add mapping from slugs to new story states
        # "slug": StateEnum.NEW_STATE,
    }

    # Upon completing a story session, update the story state if necessary
    min_story = StateEnum.DEFAULT
    if slug in SLUG_TO_STORY_STATE:
        min_story = SLUG_TO_STORY_STATE[slug]
    if StoryState.get_state(team).value < min_story.value:
        StoryState.set_state(team, min_story)


def select_winner(slug, session, team, tree):
    # Compute the transition with max number of votes
    current_votes = -1
    next_state = None
    selected_text = None
    for i, option in enumerate(session["state"]["dialogue"]["transitions"]):
        state = option["state"]
        votes = session["state"].get("votes") or []
        num_votes = len(votes[i]) if votes else 0
        if num_votes > current_votes:
            next_state = state
            current_votes = num_votes
            selected_text = option.get("text")

    session["state"]["state"] = next_state
    session["state"]["selected_text"] = selected_text
    session["state"].pop("votes", None)  # Reset votes
    if next_state == "EXIT":
        # End the session
        session["is_complete"] = True
        session["finish_time"] = datetime.now(tz=timezone.utc)
        complete_session(slug, session, team)
    else:
        session["state"]["dialogue"] = get_next_state(slug, tree, team, next_state)
        init_timer(session)


class PuzzleHandler(BasePuzzleHandler):
    @staticmethod
    def serialize_data(session: dict):
        # When serializing, we only care about the number of users/votes.
        session_votes = session["state"].get("votes")
        if session_votes:
            session_votes = [len(votes) for votes in session_votes]

        time_left = None
        timer = session["state"].get("timer")
        if timer:
            dtime = datetime.fromisoformat(timer)
            time_left = max(
                dtime - datetime.now(tz=timezone.utc), timedelta(seconds=0)
            ).seconds
        selected_text = session["state"].get("selected_text")

        return {
            "session": {
                "is_complete": session.get("is_complete"),
                "users": len(session["state"]["users"]),
                "ready": len(session["state"]["ready"]),
                "time_left": time_left,
            },
            "dialogue": session["state"].get("dialogue"),
            "selectedText": session["state"].get("selected_text"),
            "votes": session_votes,
        }

    @staticmethod
    def process_data(user, uuid, data, puzzle_slug=None, **kwargs):
        tree = get_dialogue_tree(puzzle_slug)
        team = Team.objects.get(id=user.team_id)
        storycard_id = slug_to_storycard_id(puzzle_slug)
        with story_session_cache_manager(user.team_id, storycard_id) as cm:
            session = cm.get_no_create()
            if session is None:
                # should not happen unless we're mucking in admin
                raise RuntimeError(f"No story found for slug {slug}")

            if session.get("is_complete"):
                return

            if data["type"] == "ready":
                session["state"]["ready"] = add_uuid(session["state"]["ready"], uuid)
            elif data["type"] == "start":
                if session["state"].get("state"):
                    logger.warning(
                        "Tried to start but state is already set to %s",
                        session["state"]["state"],
                    )
                    return
                else:
                    session["state"]["state"] = "start"
                    session["state"]["dialogue"] = get_next_state(
                        puzzle_slug, tree, team
                    )  # initial state
                    init_timer(session)
            elif data["type"] == "next":
                # Because multiple clients may send this request, make sure it's
                # idempotent based on the current state
                if session["state"]["state"] == data["current"]:
                    select_winner(puzzle_slug, session, team, tree)
            elif data["type"] == "vote":
                # Add the uuid to the voted option
                voted_state = data["state"]
                transitions = session["state"]["dialogue"]["transitions"]
                if not session["state"].get("votes"):
                    session["state"]["votes"] = [[] for option in transitions]

                for i, votes in enumerate(session["state"]["votes"]):
                    if i == voted_state:
                        session["state"]["votes"][i] = add_uuid(votes, uuid)
                    else:
                        session["state"]["votes"][i] = remove_uuid(votes, uuid)
            cm.set(session)

        send_message(
            user,
            puzzle_slug,
            data=PuzzleHandler.serialize_data(session),
        )

    @staticmethod
    def connect(user, uuid, slug, **kwargs):
        storycard_id = slug_to_storycard_id(slug)
        with story_session_cache_manager(user.team_id, storycard_id) as cm:
            session = cm.get_or_create()
            if uuid not in session["state"]["users"]:
                session["state"]["users"] = add_uuid(session["state"]["users"], uuid)
                cm.set(session)

        send_message(
            user,
            slug,
            data=PuzzleHandler.serialize_data(session),
        )

    @staticmethod
    def disconnect(user, uuid, slug, **kwargs):
        storycard_id = slug_to_storycard_id(slug)
        with story_session_cache_manager(user.team_id, storycard_id) as cm:
            session = cm.get_no_create()
            if session is None:
                # should not happen unless we're mucking in admin
                raise RuntimeError(f"No story found for slug {slug}")

            if uuid in session["state"]["users"]:
                session["state"]["users"].remove(uuid)
                cm.set(session)

        send_message(
            user,
            slug,
            data=PuzzleHandler.serialize_data(session),
        )


def story_session_cache_manager(team_id, storycard_id, **kwargs):
    return SessionCacheManager(
        team_id=team_id,
        puzzle_id=None,
        storycard_id=storycard_id,
        initial_data={"state": {"users": [], "ready": []}},
        **kwargs,
    )
