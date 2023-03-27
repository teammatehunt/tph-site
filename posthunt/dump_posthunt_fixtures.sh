#!/usr/bin/bash
set -e
REAL_SOURCE="$(perl -e "use Cwd 'abs_path'; print abs_path('${BASH_SOURCE}')")"
cd "$(dirname "$(dirname "${REAL_SOURCE}")")"

# Usage: ./posthunt/dump_posthunt_fixtures.sh [user@server]
# Dump from the given server if provided or else the local machine.

if [ -n "$1" ] ; then
  SSH_CMD="ssh $1 'cd ~/tph && bash -l <(cat) </dev/null'"
  shift
else
  SSH_CMD='bash <(cat) </dev/null'
fi

bash -c "$SSH_CMD" <<"EOF_DOCKER" > server/tph/fixtures/posthunt/dump.yaml
docker-compose exec -T tph /app/server/manage.py dumpdata --format yaml spoilr_core.Round puzzles.Puzzle spoilr_core.Puzzle spoilr_core.PseudoAnswer spoilr_hints.CannedHint spoilr_events.Event puzzles.StoryCard spoilr_core.Interaction spoilr_email.CannedEmail spoilr_core.HuntSetting spoilr_core.HQUpdate | python3 /dev/fd/3 3<<-"EOF_PY"
import sys

import yaml

data = yaml.safe_load(sys.stdin)
filtered_data = []

for obj in data:
  if obj['model'] == 'spoilr_core.hqupdate':
    if obj['fields']['team'] is not None:
      continue
    if obj['fields']['puzzle'] is None:
      continue
  if obj['model'] == 'spoilr_core.huntsetting':
    if obj['fields']['name'].endswith('event_rewards'):
      continue
  filtered_data.append(obj)

yaml.dump(filtered_data, sys.stdout, sort_keys=False)
EOF_PY
EOF_DOCKER

# You should run make_posthunt_access_fixtures.py after this
