import functools
import json
from pathlib import Path
from urllib.parse import urlencode
import zipfile

from importlib_resources import files

from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser


DEFAULT_USERNAME = "default"


def generate_url(path, query={}):
    path = path.lstrip("/")
    base_url = f"https://{settings.DOMAIN}/{path}"
    if not query:
        return base_url

    return f"{base_url}?{urlencode(query)}"


def DefaultUserMiddleware(get_response):
    """
    Replace request.user with the default user.
    """

    def middleware(request):
        user = User.objects.filter(username=DEFAULT_USERNAME).first()
        if user:
            request.user = user
        return get_response(request)

    return middleware


@functools.lru_cache(maxsize=1)
def get_client():
    from django.test import Client

    return Client()


if not settings.IS_PYODIDE:
    from django.contrib.staticfiles.storage import staticfiles_storage

else:
    import js
    import pyodide

    @functools.lru_cache(maxsize=1)
    def staticfiles_json():
        parent_module = files(".".join(__name__.split(".")[:-1]))
        with parent_module.joinpath("staticfiles_mapping.json").open() as f:
            return json.load(f)

    class KnownStaticfiles:
        @staticmethod
        def url(filename):
            return staticfiles_json().get(filename)

    staticfiles_storage = KnownStaticfiles()

    from django.db import models

    @pyodide.to_js
    def js_noop(*args, **kwargs):
        pass

    def sync_indexeddb(populate=False):
        """
        Emscripten to IndexedDB if populate=False and IndexedDB to Emscripten
        if populate=True.
        """
        js.pyodide.FS.syncfs(populate, js_noop)

    def reset_db(old_crc=None):
        "Reset the sqlite3 database if old_crc does not match."
        dbcrc_path = "/indexeddb/dbcrc.txt"
        with zipfile.ZipFile("/server.zip") as zipf:
            dbinfo = zipf.getinfo("db.sqlite3")
            crc = f"{dbinfo.CRC:08x}"
            if crc != old_crc:
                zipf.extract(dbinfo, "/indexeddb")
                with open(dbcrc_path, "w") as f:
                    f.write(crc)
        sync_indexeddb()

    def get_mock_response(
        path, method="GET", body=None, headers=None, cookie=None, **kwargs
    ):
        "Get mock response, for pyodide."
        client = get_client()
        request_kwargs = {}
        if cookie is not None:
            request_kwargs["HTTP_COOKIE"] = cookie
        if method == "GET":
            response = client.get(path, **request_kwargs)
        else:
            assert method == "POST"
            content_type = headers and headers.get("Content-Type")
            post_kwargs = {}
            if content_type is not None:
                post_kwargs["content_type"] = content_type
            if body is not None:
                post_kwargs["data"] = body
            response = client.post(path, **post_kwargs, **request_kwargs)
        result = {
            "status": response.status_code,
            "content": response.content,
        }
        sync_indexeddb()
        return result
