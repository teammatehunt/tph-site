from urllib.parse import urlencode

from django.conf import settings

if settings.IS_PYODIDE:
    # use builtin json module with pyodide
    import json
else:
    # ujson is faster
    import ujson as json


def generate_url(type, path, query={}):
    # FIXME(update): Update this logic for your hunt
    host = {
        "prehunt": settings.PREHUNT_HOST,
        "hunt": settings.HUNT_HOST,
        "registration": settings.REGISTRATION_HOST,
        "internal": settings.HUNT_HOST,
    }[type]
    assert host is not None
    path = path.lstrip("/")
    if settings.IS_POSTHUNT:
        # in posthunt, we change the different hosts to be base paths instead of domains
        base_url = f"/2023/{host}"
    else:
        base_url = f"https://{host}"
    if path:
        # edge case: only insert slash if path is nonempty (ie not the root)
        base_url += "/" + path
    if not query:
        return base_url

    return f"{base_url}?{urlencode(query)}"
