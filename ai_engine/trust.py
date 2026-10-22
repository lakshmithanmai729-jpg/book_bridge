"""Listing risk scoring for the moderation queue.

The marketplace is peer-to-peer, so the cheap failure mode is a scam listing:
a stolen photo, a phone number buried in the description to move the deal off
platform, a duplicate repost to push it to the top, or an absurd price. This
module scores those signals so a human moderator (staff dashboard) sees the
riskiest reports first, and so the seller gets a warning before publishing.

Scores are explainable by design: every point added comes with a reason.
"""
import re
import statistics

from books.models import Book

from .text import fuzzy_ratio, tokenize

# (pattern, reason, weight) — the weight is how much it raises the risk score.
CONTACT_PATTERNS = [
    (re.compile(r'(?:\+91[\s-]?)?[6-9]\d{9}\b'), 'Phone number in the description', 60),
    (re.compile(r'\b\d{5}\s?\d{5}\b'), 'Phone number in the description', 60),
    (re.compile(r'(?:t\.me/|telegram|whatsapp|wa\.me)', re.I), 'Off-platform contact link', 45),
    (re.compile(r'https?://|www\.', re.I), 'External link in the description', 40),
    (re.compile(r'\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b', re.I), 'Email address in the description', 45),
]

LEVELS = [(60, 'high'), (30, 'medium'), (0, 'low')]


def _category_median_price(category_id, exclude_id=None):
    queryset = Book.objects.filter(
        is_sold=False, is_hidden=False, category_id=category_id,
    )
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    prices = [float(price) for price in queryset.values_list('price', flat=True)[:200] if float(price) > 0]
    return statistics.median(prices) if prices else None


def _duplicate_of(seller, title, exclude_id=None):
    if not seller or not title:
        return None
    queryset = Book.objects.filter(seller=seller, is_sold=False, is_hidden=False)
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    for existing in queryset.only('id', 'title', 'price'):
        ratio = fuzzy_ratio(title, existing.title)
        if ratio >= 0.82 and len(tokenize(title)) >= 2:
            return existing, ratio
    return None


def assess_listing(title='', description='', price=None, category_id=None,
                   seller=None, image_present=True, exclude_id=None):
    """Return {score, level, reasons, checks} for a listing."""
    reasons = []
    checks = []
    score = 0

    text = f'{title}\n{description or ""}'
    for pattern, reason, weight in CONTACT_PATTERNS:
        if pattern.search(text):
            score += weight
            reasons.append(reason)
            break  # one contact signal is enough, do not triple-count

    duplicate = _duplicate_of(seller, title, exclude_id=exclude_id)
    if duplicate:
        existing, ratio = duplicate
        score += 30
        reasons.append(
            f'Looks like a duplicate of “{existing.title}” that you already listed '
            f'({int(ratio * 100)}% match)'
        )

    try:
        price_value = float(price) if price is not None else None
    except (TypeError, ValueError):
        price_value = None

    median = _category_median_price(category_id, exclude_id=exclude_id) if category_id else None
    if price_value and median:
        ratio = price_value / median
        if ratio >= 3:
            score += 18
            reasons.append(f'Price is {ratio:.1f}× the category median (₹{median:,.0f})')
        elif ratio <= 0.25:
            score += 10
            reasons.append(f'Price is well below the category median (₹{median:,.0f})')

    clean_description = (description or '').strip()
    if not clean_description:
        score += 8
        reasons.append('No description — buyers cannot judge the condition')
    elif len(clean_description) < 30:
        score += 4
        reasons.append('Very short description')

    if not image_present:
        score += 6
        reasons.append('No photo of the actual book')

    if title and title.isupper() and len(title) > 12:
        score += 5
        reasons.append('Title is all capitals')

    exclamations = (title + (description or '')).count('!')
    if exclamations >= 4:
        score += 4
        reasons.append('Excessive punctuation')

    level = next(level for threshold, level in LEVELS if score >= threshold)

    checks.append({'label': 'No contact details in the description', 'passed': not any(
        pattern.search(text) for pattern, _, _ in CONTACT_PATTERNS
    )})
    checks.append({'label': 'Not a duplicate listing', 'passed': duplicate is None})
    checks.append({'label': 'Price in line with the category', 'passed': not (
        price_value and median and (price_value / median >= 3 or price_value / median <= 0.25)
    )})
    checks.append({'label': 'Describes the condition', 'passed': len(clean_description) >= 30})
    checks.append({'label': 'Has a real photo', 'passed': bool(image_present)})

    return {
        'score': min(score, 100),
        'level': level,
        'reasons': reasons,
        'checks': checks,
    }
