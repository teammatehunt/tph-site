"""Config for hint management."""

from spoilr.core.models import HuntSetting

from .cache import delete_memoized_cache_entry, memoized_cache

HINTS_CACHE_BUCKET = "hints"
HINTS_REF = "hints"


@memoized_cache(HINTS_CACHE_BUCKET)
def get_hints_enabled(site_ref=HINTS_REF):
    setting, _ = HuntSetting.objects.get_or_create(name=f"spoilr.{site_ref}.enabled")
    return setting.boolean_value


@memoized_cache(HINTS_CACHE_BUCKET)
def get_max_open_hints(site_ref=HINTS_REF):
    setting, _ = HuntSetting.objects.get_or_create(
        name=f"spoilr.{site_ref}.max_open_hints"
    )
    return int(setting.text_value or 1)


@memoized_cache(HINTS_CACHE_BUCKET)
def get_solves_before_hint_unlock(site_ref=HINTS_REF):
    """The number of teams that need to solve the puzzle before hints open for that puzzle."""
    setting, _ = HuntSetting.objects.get_or_create(
        name=f"spoilr.{site_ref}.solves_before_hint_unlock"
    )
    return int(setting.text_value or 100)
