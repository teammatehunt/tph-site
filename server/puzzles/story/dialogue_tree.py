import csv
import re
from functools import lru_cache

from puzzles.assets import get_hashed_url
from spoilr.core.models import PuzzleSubmission
from tph.utils import load_file

OPTIONS = ("Option 1", "Option 2", "Option 3", "Option 4")


@lru_cache(maxsize=None)
def get_dialogue_tree(storycard: str):
    """
    Loads a CSV for a dialogue tree into memory.
    Supports raw text, html, and selectable options. See data/story/sample.csv.
    """
    tree = {}
    with load_file(f"data/story/{storycard}.csv", base_module="puzzles").open() as f:
        reader = csv.DictReader(f)
        temp_state = 0
        for row in reader:
            state = row["State"]
            text = row["Dialogue"].replace("\n", "<br>")  # Support line breaks
            sprite = row.get("Sprite")
            if not text:
                continue

            if not state:
                state = f"temp{temp_state}"
                temp_state += 1

            assert state not in tree, f"Duplicate state found: {state}"

            transitions = []
            if row["Next State"]:
                transitions.append({"state": row["Next State"]})
            elif not any((row.get(option) for option in OPTIONS)):
                # If there are no options, default to the next available state
                transitions.append({"state": f"temp{temp_state}"})

            for option in OPTIONS:
                if row.get(option):
                    match = re.match(
                        r"\[\[(\(IF:(.+?)\))?(.+?)\|(.+?)\]\]\Z", row[option].strip()
                    )
                    assert match, f"No match found for option {row[option]}"
                    groups = match.groups()
                    assert (
                        groups and len(groups) == 4
                    ), f"Invalid syntax found for state {state}, option {option}: {row[option]}"

                    transitions.append({"state": groups[3], "text": groups[2]})
                    if groups[1]:
                        transitions[-1]["condition"] = groups[1]

            tree[state] = {
                "state": state,
                "sprite": sprite,
                "text": text,
                "transitions": transitions,
            }

    assert "start" in tree, "Missing start node"

    return tree


def get_next_state(slug, tree, team, state="start"):
    node = tree[state]
    sprite = node.get("sprite")
    # FIXME set sprite
    return {
        **node,
        "sprite": sprite,
        "transitions": [transition for transition in node["transitions"]],
    }
