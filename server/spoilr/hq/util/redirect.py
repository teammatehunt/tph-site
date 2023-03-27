import urllib.parse

from django.shortcuts import redirect, reverse


def redirect_with_message(
    request,
    default_path,
    message=None,
    default_path_args=None,
    anchor=None,
    **query_params,
):
    url = request.META.get("HTTP_REFERER") or reverse(
        default_path, args=default_path_args
    )
    if anchor:
        url += f"#{anchor}"

    params = {**query_params}
    if message:
        params["message"] = message
    if params:
        parsed = urllib.parse.urlparse(url)
        url_query = urllib.parse.parse_qs(parsed.query)
        url_query.update(params)
        updated = parsed._replace(query=urllib.parse.urlencode(url_query, doseq=True))
        return redirect(urllib.parse.urlunparse(updated))
    return redirect(url)
