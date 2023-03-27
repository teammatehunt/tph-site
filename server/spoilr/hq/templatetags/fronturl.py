from django import template
from django.conf import settings
from urllib.parse import urlencode

from spoilr.utils import generate_url

register = template.Library()


@register.simple_tag
def fronturl(path, *args, query={}, site="hunt", puzzle=None):
    argspath = "/" + "/".join(args) if len(args) > 0 else ""
    path = path.lstrip("/") + argspath
    base_url = generate_url(site, f"/{path}")
    if not query:
        return base_url

    return f"{base_url}?{urlencode(query)}"
