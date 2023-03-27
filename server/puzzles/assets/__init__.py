import os

import yaml
from django.conf import settings

from tph.utils import load_file

asset_map = dict()

if settings.IS_PYODIDE:
    with load_file("media_mapping.yaml").open() as f:
        _map = yaml.safe_load(f)
    asset_map.update(_map["media"])
else:
    try:
        with open(settings.ASSET_MAPPING, "r") as f:
            _map = yaml.safe_load(f)
        asset_map.update(_map["media"])
    except FileNotFoundError:
        pass


def get_hashed_path(path):
    result = asset_map.get(path, None)
    if not result:
        return None
    return os.path.join(settings.SRV_DIR, "media", result)


def get_hashed_url(*paths):
    try:
        # Finds the first asset that exists in the map
        result = next(
            asset for path in paths if (asset := asset_map.get(path, None)) is not None
        )
    except StopIteration:
        return None
    return os.path.join(settings.ASSET_URL, result)
