"""Price suggestions from comparable listings.

The old version used the category average, which is skewed by one expensive
set. This one looks at the individual comparable listings, normalises them to
a "good" condition baseline, takes the median (robust to outliers), applies
the seller's condition, and reports how confident it is.
"""
from statistics import median

from books.models import Book

# How much a condition is worth relative to a "good" copy.
CONDITION_FACTOR = {
    'new': 1.45,
    'like_new': 1.18,
    'good': 1.0,
    'fair': 0.72,
    'poor': 0.45,
}
CONDITION_LABEL = dict(Book.CONDITION_CHOICES)

# Typical resale value of a second-hand textbook vs its printed MRP.
RESALE_RATIO = 0.45


def _round_price(value):
    value = max(0.0, float(value))
    if value >= 200:
        return float(round(value / 10.0) * 10)
    if value >= 50:
        return float(round(value / 5.0) * 5)
    return float(round(value))


def _spread(values):
    """Inter-quartile range — a cheap, outlier-proof measure of spread."""
    ordered = sorted(values)
    if len(ordered) < 4:
        return (max(ordered) - min(ordered)) if ordered else 0.0
    low = median(ordered[: len(ordered) // 2])
    high = median(ordered[(len(ordered) + 1) // 2 :])
    return high - low


def _confidence(prices):
    """0..1 — more comparable listings and a tighter spread means more trust."""
    if not prices:
        return 0.0
    sample_score = min(len(prices) / 8.0, 1.0)
    centre = median(prices)
    spread = _spread(prices)
    consistency = 1.0 if centre <= 0 else max(0.0, 1.0 - (spread / centre))
    return round(min(1.0, 0.15 + 0.55 * sample_score + 0.3 * consistency), 2)


def comparables_for(category_id=None, title='', exclude_id=None, limit=40):
    queryset = Book.objects.filter(is_sold=False, is_hidden=False)
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)

    books = list(queryset.order_by('-created_at')[:200])
    if title:
        words = {word for word in title.lower().split() if len(word) > 3}
        books.sort(
            key=lambda book: sum(1 for word in words if word in book.title.lower()),
            reverse=True,
        )
    return books[:limit]


def suggest_price(category_id=None, condition='good', title='', original_price=None,
                  exclude_id=None):
    """Return a suggestion dict consumed by the API and the sell form."""
    condition = condition if condition in CONDITION_FACTOR else 'good'
    factor = CONDITION_FACTOR[condition]
    sample = comparables_for(category_id=category_id, title=title, exclude_id=exclude_id)
    # Free/donation listings say nothing about the going rate, so they are
    # excluded from both the maths and the "comparable listings" list.
    sample = [book for book in sample if float(book.price) > 0]
    prices = [float(book.price) for book in sample]

    basis = 'market'
    used = sample
    if len(prices) >= 3:
        # normalise each comparable to the "good" baseline before taking the median
        baseline = median(
            float(book.price) / CONDITION_FACTOR.get(book.condition, 1.0)
            for book in sample
            if float(book.price) > 0
        )
        suggestion = baseline * factor
        basis = 'comparables'
    elif original_price:
        suggestion = float(original_price) * RESALE_RATIO * factor
        basis = 'mrp'
        used = []
    elif prices:
        suggestion = median(prices)
        used = sample
    else:
        # Nothing to learn from yet: a sane default for a used textbook.
        suggestion = 250.0 * factor
        used = []

    confidence = _confidence(prices) if basis == 'comparables' else (0.35 if basis == 'mrp' else 0.15)

    if original_price and basis == 'comparables':
        # A printed MRP is a strong ceiling — never suggest above 90% of it.
        ceiling = float(original_price) * 0.9
        suggestion = min(suggestion, ceiling)
        confidence = min(1.0, confidence + 0.05)

    suggested = _round_price(suggestion)
    low = _round_price(suggested * 0.85)
    high = _round_price(suggested * 1.2)

    comparison = []
    for book in used[:3]:
        comparison.append({
            'id': book.pk,
            'title': book.title[:60],
            'price': float(book.price),
            'condition': CONDITION_LABEL.get(book.condition, book.condition),
            'area': book.location_area or book.location_city or 'Nearby',
        })

    explanation = _explain(basis, len(prices), suggested, condition, comparison)

    return {
        'suggested_price': int(suggested) if suggested == int(suggested) else suggested,
        'low': low,
        'high': high,
        'confidence': confidence,
        'confidence_label': _confidence_label(confidence),
        'sample_size': len(prices),
        'basis': basis,
        'explanation': explanation,
        'comparables': comparison,
    }


def _confidence_label(confidence):
    if confidence >= 0.7:
        return 'High confidence'
    if confidence >= 0.4:
        return 'Medium confidence'
    return 'Low confidence'


def _explain(basis, sample_size, suggested, condition, comparison):
    label = CONDITION_LABEL.get(condition, condition)
    if basis == 'comparables':
        return (
            f'Based on {sample_size} similar listing{"s" if sample_size != 1 else ""} '
            f'in the same category, adjusted for {label.lower()} condition.'
        )
    if basis == 'mrp':
        return (
            f'No close comparisons yet, so this is estimated from the printed MRP '
            f'({int(RESALE_RATIO * 100)}% resale) and {label.lower()} condition.'
        )
    if sample_size:
        return 'Estimated from the few nearby listings available right now.'
    return 'BookBridge is still learning this category — this is a starting point, not a rule.'
