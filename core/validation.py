"""Small helpers that keep user-typed text inside the model's column limits.

SQLite silently stores a 500-character value in a ``VARCHAR(100)`` column,
but PostgreSQL raises an error and the request dies with a 500. These helpers
let the views reject (or clamp) oversized input before it reaches the database.
"""


def length_error(value, max_length, label):
    """Return a friendly message when ``value`` is longer than the column."""
    if len(value or '') > max_length:
        return f'{label} is too long — please keep it under {max_length} characters.'
    return ''


def clamp(value, max_length):
    """Trim ``value`` so it always fits a CharField(max_length=...)."""
    return (value or '').strip()[:max_length]
