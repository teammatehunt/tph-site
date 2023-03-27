"""Config for virtual unlock management."""
from spoilr.core.models import HuntSetting

from .cache import clear_memoized_cache, memoized_cache
from .hunt import is_site_over

VIRTUAL_CACHE_BUCKET = "virtual"
VIRTUAL_REF = "virtual"


@memoized_cache(VIRTUAL_CACHE_BUCKET)
def get_virtual_delay(site_ref=VIRTUAL_REF):
    if is_site_over():
        return 0

    setting, _ = HuntSetting.objects.get_or_create(
        name=f"spoilr.{site_ref}.virtual_delay_m"
    )
    return int(setting.text_value or 60)
