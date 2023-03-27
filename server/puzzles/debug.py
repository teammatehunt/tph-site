# We need to make external requests with the test_branch server to
# dynamically fetch fixtures. However, this blocks a Django thread, so
# ensure that this does not run on staging / prod.
import requests
import tempfile

from django.conf import settings
from django.core import serializers
from django.core.management import call_command

from puzzles.models import Puzzle
import spoilr.core.models


def load_puzzle_from_branch_fixture(request, slug):
    """
    Makes a request to a branch server to parse a Puzzle fixture.
    Loads everything in that fixture file to the database.
    """
    assert settings.SERVER_ENVIRONMENT == "test_branch"
    host = request.get_host()
    hostname = host.split(":")[0]
    if hostname == "django":
        # Trust X-Forwarded-Host because this was sent directly from the branch
        # frontend docker container. (Additionally, the other request path has
        # to go through Caddy, which resets any existing X-Forwarded-Host to
        # the Host header.)
        host = request.headers.get("X-Forwarded-Host", "")
    host_parts = host.split(".", 1)
    if len(host_parts) == 2 and host_parts[1] in settings.HOSTS:
        branch_hostname = f"branch-{host_parts[0]}"
    else:
        # bad domain
        return None
    port = 8765
    url = f"http://{branch_hostname}:{port}/puzzles/{slug}.yaml"
    r = requests.get(url)
    if r.status_code == 404:
        # fixture does not exist, ignore
        return None
    # else, raise if there was an error
    r.raise_for_status()
    with tempfile.NamedTemporaryFile("wb", suffix=".yaml") as f:
        f.write(r.content)
        f.flush()
        # if loading fails, the error will propagate back up
        call_command("loaddata", f.name)
