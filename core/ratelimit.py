"""A tiny cache-backed rate limiter for the trust & safety features.

Every write action (sending a chat message, publishing a listing, reporting a
listing, leaving a review, posting a book request) is counted per user in the
cache.  When the limit for the window is crossed the request is refused with a
friendly "slow down" message instead of an error page.

Limits live in ``settings.RATE_LIMITS`` so they can be tuned without a code
change, and the cache backend can be swapped for Redis in production without
touching this module.
"""
from django.conf import settings
from django.core.cache import cache

# (allowed actions, window in seconds) — used when settings has no entry.
DEFAULTS = {
    'chat': (25, 5 * 60),       # 25 messages / 5 minutes
    'listing': (10, 60 * 60),   # 10 new listings / hour
    'report': (5, 60 * 60),     # 5 reports / hour
    'review': (10, 60 * 60),    # 10 reviews / hour
    'request': (5, 60 * 60),    # 5 book requests / hour
    'ai': (120, 60 * 60),       # 120 AI helper calls / hour
}


def _limits(action):
    configured = getattr(settings, 'RATE_LIMITS', None) or {}
    return configured.get(action) or DEFAULTS.get(action, (30, 5 * 60))


def _ttl(key, fallback):
    try:
        remaining = cache.ttl(key)
    except Exception:
        return fallback
    if not remaining:
        return fallback
    return max(1, int(remaining))


def check(action, identity):
    """Count one hit. Returns ``(allowed, seconds_until_reset)``."""
    limit, window = _limits(action)
    key = f'ratelimit:{action}:{identity}'

    if cache.add(key, 1, window):        # first hit inside this window
        return True, 0

    try:
        count = cache.incr(key)
    except ValueError:                   # key expired between add and incr
        cache.set(key, 1, window)
        return True, 0

    if count <= limit:
        return True, 0
    return False, _ttl(key, window)


def identity_for(request):
    """A stable per-person key: the user id, or the IP for anonymous visitors."""
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_authenticated', False):
        return f'user:{user.pk}'
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    ip = forwarded.split(',')[0].strip() or request.META.get('REMOTE_ADDR', 'unknown')
    return f'ip:{ip}'


def friendly_message(seconds):
    """Human wording for the cool-down period."""
    if seconds >= 120:
        minutes = max(1, round(seconds / 60))
        wait = f'about {minutes} minutes'
    elif seconds >= 60:
        wait = 'about a minute'
    else:
        wait = f'{max(1, int(seconds))} seconds'
    return f'You are going a bit fast. Please try again in {wait}.'


def throttled(request, action):
    """Return a message when the visitor is over the limit, else ``None``."""
    allowed, retry_after = check(action, identity_for(request))
    if allowed:
        return None
    return friendly_message(retry_after)
