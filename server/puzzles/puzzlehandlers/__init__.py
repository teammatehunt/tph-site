from functools import wraps
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from ratelimit.decorators import ratelimit
from ratelimit.utils import get_usage_count

from spoilr.utils import json


def simple_ratelimit(handler, rate):
    "A handler that silently drops requests over the rate limit."

    @require_POST
    @ratelimit(key="user_or_ip", rate=rate, block=True)
    @wraps(handler)
    def rate_limiter(request):
        return HttpResponse(handler(request))

    return rate_limiter


# Usage: mypuzzle_submit = simple_ratelimit(mypuzzle.submit, '10/s')


def check_ratelimit(request, rate, key):
    data = get_usage_count(request, group=request.path, rate=rate, key=key)
    return data["count"] >= data["limit"]


def update_ratelimit(request, rate, key):
    get_usage_count(request, group=request.path, rate=rate, key=key, increment=True)


def get_time_left(request, rate, key):
    # Get time left before rate limit comes back, in seconds.
    data = get_usage_count(request, group=request.path, rate=rate, key=key)
    if data is None:
        return 0
    return data["time_left"]


def puzzle_key(group, request):
    # Key decides what counter to check for rate-limit.
    # For puzzle solves, should be gated by anyone from team with different
    # counter per puzzle.
    if request.context.team is None:
        # Treat IP-address as name
        name = request.META["REMOTE_ADDR"]
    else:
        # Use the username, not the teamname, just to avoid potential
        # Unicode nonsense.
        name = request.context.team.username
    puzzle_name = request.context.puzzle.name
    return f"{name}-{puzzle_name}"


class RateLimitException(Exception):
    pass


def error_ratelimit(
    handler, rate, error, key="user_or_ip", check_response=None, encode_response=None
):
    """
    A handler that checks and reports errors to the client.

    Args:
        handler: A function that we wish to rate limit. It should take a request
            as its first argument, followed by any other arguments
        rate: The rate limit to apply to the function.
        error: A callable function that should take 1 number (the time left
            in seconds before the rate limit expires), and returns an error,
            which should be a string.
        key: What key to use for the rate limit. Rate limits are tracked
            separately for each key. The default key is the logged-in user, or
            the IP address if the user is not logged in. Should either by a string
            mentioned in the django-ratelimit documentation, or a callable that
            takes (group, request) and returns a string.
        check_response: If set, the rate limit only increments if
            check_response(response) is True. For example, you may only want to
            count incorrect guesses towards the limit (although we do not
            implement it that way in this codebase). By default, the rate limit
            always increments.
        encode_response: If set, encode_response is run on the response output
            for requests that are not rate-limited.
    """

    @require_POST
    @wraps(handler)
    def rate_limiter(request, *args, **kwargs):
        if check_ratelimit(request, rate, key):
            # Hit rate limit, give error.
            time_left = get_time_left(request, rate, key)
            error_message = error(time_left)
            update_ratelimit(request, rate, key)
            raise RateLimitException(error_message)
        # Did not hit rate limit, process normally and update usage.
        if check_response is None:
            update_ratelimit(request, rate, key)
        response = handler(request, *args, **kwargs)
        if check_response is not None and not check_response(response):
            update_ratelimit(request, rate, key)
        if encode_response is not None:
            response = encode_response(response)
        return response

    return rate_limiter


# Usage: mypuzzle_submit = error_ratelimit(mypuzzle.submit, '2/m', {'error': 'Please limit your attempts to twice a minute.'}, lambda response: response['was_correct'], json.dumps)
