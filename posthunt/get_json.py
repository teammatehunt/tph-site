#!/usr/bin/env python3
# The NEXT_DATA json is the full JSON content, including some nextjs-internal content.
# We pull out just the relevant part of the JSON data.
import re
import os
import pathlib
import json
import urllib.parse

# FIXME: update to hunt website
files = list(pathlib.Path("mypuzzlehunt.com").rglob("*"))

next_regex = re.compile(r'<script id="__NEXT_DATA__"[^>]*>([^<]*)</script>')

# We need to generate staticPaths lists for dynamic routes (teams and puzzle stats).
puzzle_names = []
team_names = []

for name in files:
    if os.path.isdir(name):
        continue
    name = str(name)
    if not name.endswith(".html"):
        continue
    # Clean up some garbage paths...
    if "[team_name]" in name:
        continue
    if "stats/start_of_puzzle" in name:
        continue
    with open(name) as f:
        text = f.read()
    newdir, base = os.path.split(name)
    newdir = newdir.replace("mypuzzlehunt.com", "json_responses")
    base = base.replace(".html", ".json")
    os.makedirs(newdir, exist_ok=True)
    if next_regex.search(text):
        # JSON exists.
        json_string = next_regex.search(text).group(1)
        json_parsed = json.loads(json_string)
        # Pull out just the pageProps
        page_props = json_parsed["props"]["pageProps"]
        # If it's a puzzle page, go deeper.
        if newdir.endswith("puzzles"):
            page_props = page_props["puzzleData"]
            puzzle_names.append({"params": {"slug": base[: -len(".json")]}})
        if newdir.endswith("team"):
            # These filenames cannot have weird characters in them so we URL encode them.
            # The static path doesn't need to be encoded because we encode it in the
            # NextJS static props function. Note that JS uses a different set of safe
            # characters than the Python default.
            # ALSO note that exclamantion marks are not handled well in filenames when
            # we do a NextJS require, so although encodeURIComponent does not excape !, we
            # will manually escape it later.
            team_name = page_props["teamInfo"]["name"]
            team_names.append({"params": {"team_name": team_name}})
            team_name_encoded = urllib.parse.quote(team_name, safe="-_.~'()")
            base = team_name_encoded + ".json"
        with open(os.path.join(newdir, base), "w") as f:
            f.write(json.dumps(page_props))
        # We need the hunt-wide context too.
        # This is identical for every page but let's just write it every time.
        with open("json_responses/hunt_info.json", "w") as f:
            f.write(json.dumps(json_parsed["props"]["huntInfo"]))


# save staticPaths lists
puzzle_paths = {
    "paths": puzzle_names,
    "fallback": False,
}
with open("json_responses/puzzle_paths.json", "w") as f:
    f.write(json.dumps(puzzle_paths))

team_paths = {
    "paths": team_names,
    "fallback": False,
}
with open("json_responses/team_paths.json", "w") as f:
    f.write(json.dumps(team_paths))
