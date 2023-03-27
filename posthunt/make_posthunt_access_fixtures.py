#!/usr/bin/env python3
"""
Creates RoundAccess, PuzzleAccess, and StoryCardAccess fixtures for a team from
a dump of the round, puzzle, and storycard fixtures.

Run this after dump_posthunt_fixtures.sh.
"""
from pathlib import Path

import yaml

TEAM_PK = 1
TIMESTAMP = "2023-01-13T20:00:00Z"
# should be 0 unless testing and need to not clobber existing access objects
ACCESS_OFFSET = 0

repo_dir = Path(__file__).absolute().parents[1]
fixtures_dir = repo_dir / "server" / "tph" / "fixtures" / "posthunt"
input_yaml = fixtures_dir / "dump.yaml"
output_yaml = fixtures_dir / "access.yaml"

puzzle_pks = []
round_pks = []
storycard_pks = []

with open(input_yaml) as f:
    data = yaml.safe_load(f)
for obj in data:
    if obj["model"] == "spoilr_core.round":
        round_pks.append(obj["pk"])
    if obj["model"] == "spoilr_core.puzzle":
        puzzle_pks.append(obj["pk"])
    if obj["model"] == "puzzles.storycard":
        storycard_pks.append(obj["pk"])

fixtures = []

for pk in round_pks:
    fixtures.append(
        {
            "model": "spoilr_core.roundaccess",
            "pk": pk + ACCESS_OFFSET,
            "fields": {
                "round": pk,
                "team": TEAM_PK,
                "timestamp": TIMESTAMP,
            },
        }
    )

for pk in puzzle_pks:
    fixtures.append(
        {
            "model": "spoilr_core.puzzleaccess",
            "pk": pk + ACCESS_OFFSET,
            "fields": {
                "puzzle": pk,
                "team": TEAM_PK,
                "timestamp": TIMESTAMP,
            },
        }
    )

for pk in storycard_pks:
    fixtures.append(
        {
            "model": "puzzles.storycardaccess",
            "pk": pk + ACCESS_OFFSET,
            "fields": {
                "story_card": pk,
                "team": TEAM_PK,
                "timestamp": TIMESTAMP,
            },
        }
    )

with open(output_yaml, "w") as f:
    yaml.dump(fixtures, f, sort_keys=False)
