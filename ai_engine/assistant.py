"""Natural-language search.

Turns "neet books under 300 in madhapur" into real filters: category, budget,
condition, free-only, location and sort order. The parser is rule-based on
purpose — it is instant, free, works offline, and every interpretation can be
shown back to the student so nothing is silently misunderstood.
"""
import re

from django.db.models import Q

from books.models import Book, Category

from .classify import CATEGORY_KEYWORDS

BUDGET_PATTERNS = [
    r'(?:under|below|less than|cheaper than|upto|up to|within|max|maximum)\s*(?:rs\.?|inr|₹)?\s*(\d{2,6})',
    r'(?:rs\.?|inr|₹)\s*(\d{2,6})\s*(?:or less|max|budget)',
    r'(\d{2,6})\s*(?:లోపు|కంటే తక్కువ)',
]
MIN_PATTERNS = [
    r'(?:above|over|more than|at least)\s*(?:rs\.?|inr|₹)?\s*(\d{2,6})',
]

FREE_WORDS = ('free', 'donation', 'donate', 'no cost', 'ఉచితం')
CONDITION_WORDS = {
    'like new': 'like_new',
    'like-new': 'like_new',
    'brand new': 'new',
    'new': 'new',
    'good': 'good',
    'fair': 'fair',
    'poor': 'poor',
}
SORT_WORDS = {
    'cheapest': 'price_low',
    'lowest price': 'price_low',
    'cheap': 'price_low',
    'newest': 'newest',
    'latest': 'newest',
    'recent': 'newest',
    'popular': 'popular',
    'most viewed': 'popular',
}
STOP_QUERY_WORDS = {
    'books', 'book', 'show', 'me', 'find', 'near', 'please', 'want', 'need',
    'looking', 'for', 'any', 'some', 'in', 'at', 'under', 'below', 'less',
    'than', 'upto', 'up', 'to', 'within', 'max', 'maximum', 'free', 'donation',
    'cheapest', 'newest', 'latest', 'recent', 'popular', 'rs', 'inr', '₹',
}


def _known_locations():
    areas = set()
    for field in ('location_area', 'location_city'):
        values = (
            Book.objects.filter(is_sold=False, is_hidden=False)
            .exclude(**{f'{field}__isnull': True})
            .exclude(**{field: ''})
            .values_list(field, flat=True)
            .distinct()[:200]
        )
        for value in values:
            if value and len(value.strip()) >= 3:
                areas.add(value.strip())
    return sorted(areas, key=len, reverse=True)


def _match_category(text):
    """Return (category, matched word) so the keyword can leave the free-text query."""
    lowered = text.lower()
    for category in Category.objects.all():
        if category.name.lower() in lowered:
            return category, category.name.lower()

    tokens = set(re.findall(r'[a-z0-9]+', lowered))
    for name, words in CATEGORY_KEYWORDS.items():
        for word in words:
            if (' ' in word and word in lowered) or word in tokens or word in name.lower():
                category = Category.objects.filter(name__iexact=name).first()
                if category:
                    return category, word
    return None, ''


PLACE_STOPWORDS = {
    'books', 'book', 'for', 'with', 'and', 'the', 'a', 'an', 'any', 'some',
    'under', 'below', 'over', 'above', 'less', 'than', 'near', 'around',
    'free', 'new', 'used', 'good', 'like', 'fair', 'poor', 'cheap', 'cheapest',
}


def _match_location(text):
    lowered = text.lower()
    for place in _known_locations():
        if place.lower() in lowered:
            return place

    # Unknown places still work: "in kurnool", "near warangal".
    match = re.search(r'\b(?:in|near|around|at)\s+([a-z][a-z .]{1,40})', lowered)
    if not match:
        return ''
    words = [
        word for word in re.findall(r'[a-z]+', match.group(1))
        if word not in PLACE_STOPWORDS
    ][:3]
    if not words:
        return ''
    return ' '.join(words).title()


def parse_query(raw):
    """Return {filters, understood, leftover} for a natural-language query."""
    raw = (raw or '').strip()
    text = raw.lower()
    understood = []
    filters = {
        'q': '',
        'category': None,
        'category_name': '',
        'max_price': None,
        'min_price': None,
        'free': False,
        'condition': '',
        'location': '',
        'sort': '',
    }

    for pattern in BUDGET_PATTERNS:
        match = re.search(pattern, text)
        if match:
            filters['max_price'] = int(match.group(1))
            understood.append(f'Under ₹{filters["max_price"]:,}')
            text = text[:match.start()] + text[match.end():]
            break

    for pattern in MIN_PATTERNS:
        match = re.search(pattern, text)
        if match:
            filters['min_price'] = int(match.group(1))
            understood.append(f'Above ₹{filters["min_price"]:,}')
            text = text[:match.start()] + text[match.end():]
            break

    if any(word in text for word in FREE_WORDS):
        filters['free'] = True
        understood.append('Free books only')
        for word in FREE_WORDS:
            text = text.replace(word, ' ')

    category, matched_word = _match_category(text)
    if category:
        filters['category'] = category.pk
        filters['category_name'] = category.name
        understood.append(f'Category: {category.name}')
        text = re.sub(re.escape(category.name.lower()), ' ', text)
        if matched_word and matched_word != category.name.lower():
            text = re.sub(rf'\b{re.escape(matched_word)}\b', ' ', text)

    for phrase, value in CONDITION_WORDS.items():
        if re.search(rf'\b{re.escape(phrase)}\b', text):
            filters['condition'] = value
            understood.append(f'Condition: {phrase.title()}')
            text = re.sub(rf'\b{re.escape(phrase)}\b', ' ', text)
            break

    location = _match_location(text) or _match_location(raw)
    if location:
        filters['location'] = location
        understood.append(f'Near {location}')
        text = text.replace(location.lower(), ' ')

    for phrase, value in SORT_WORDS.items():
        if phrase in text:
            filters['sort'] = value
            understood.append({'price_low': 'Cheapest first', 'newest': 'Newest first',
                               'popular': 'Most viewed first'}[value])
            text = text.replace(phrase, ' ')
            break

    leftover = [
        word for word in re.findall(r'[A-Za-z0-9]+', text)
        if word not in STOP_QUERY_WORDS and len(word) > 1
    ]
    filters['q'] = ' '.join(leftover)

    return {'query': raw, 'filters': filters, 'understood': understood}


def search(raw, limit=24, viewer=None):
    """Run the parsed query against available listings."""
    parsed = parse_query(raw)
    filters = parsed['filters']

    queryset = Book.objects.filter(is_sold=False, is_hidden=False).select_related('category', 'seller')

    if viewer is not None and getattr(viewer, 'is_authenticated', False):
        from accounts.models import UserBlock
        blocked = UserBlock.blocked_ids_for(viewer)
        if blocked:
            queryset = queryset.exclude(seller_id__in=blocked)

    if filters['q']:
        for word in filters['q'].split():
            queryset = queryset.filter(
                Q(title__icontains=word)
                | Q(author__icontains=word)
                | Q(description__icontains=word)
                | Q(category__name__icontains=word)
            )

    if filters['category']:
        queryset = queryset.filter(category_id=filters['category'])
    if filters['condition']:
        queryset = queryset.filter(condition=filters['condition'])
    if filters['free']:
        queryset = queryset.filter(Q(is_donation=True) | Q(price=0))
    if filters['max_price'] is not None:
        queryset = queryset.filter(price__lte=filters['max_price'])
    if filters['min_price'] is not None:
        queryset = queryset.filter(price__gte=filters['min_price'])
    if filters['location']:
        queryset = queryset.filter(
            Q(location_area__icontains=filters['location'])
            | Q(location_city__icontains=filters['location'])
        )

    ordering = {
        'price_low': 'price',
        'newest': '-created_at',
        'popular': '-views_count',
    }.get(filters['sort'], '-created_at' if not filters['q'] else 'price')

    queryset = queryset.order_by(ordering)
    total = queryset.count()

    # A strict area filter that finds nothing is a dead end. Relax the area
    # (never the budget or the category) and say so, instead of showing zero.
    relaxed = ''
    if total == 0 and filters['location']:
        relaxed = filters['location']
        fallback = _results_without_location(raw, filters, ordering, limit, viewer=viewer)
        queryset = fallback
        total = queryset.count()

    results = list(queryset[:limit])
    parsed['count'] = total
    parsed['results'] = results
    parsed['relaxed_location'] = relaxed
    parsed['explanation'] = _explain(parsed)
    return parsed


def _results_without_location(raw, filters, ordering, limit, viewer=None):
    queryset = Book.objects.filter(is_sold=False, is_hidden=False)
    if viewer is not None and getattr(viewer, 'is_authenticated', False):
        from accounts.models import UserBlock
        blocked = UserBlock.blocked_ids_for(viewer)
        if blocked:
            queryset = queryset.exclude(seller_id__in=blocked)
    if filters['q']:
        for word in filters['q'].split():
            queryset = queryset.filter(
                Q(title__icontains=word)
                | Q(author__icontains=word)
                | Q(description__icontains=word)
                | Q(category__name__icontains=word)
            )
    if filters['category']:
        queryset = queryset.filter(category_id=filters['category'])
    if filters['condition']:
        queryset = queryset.filter(condition=filters['condition'])
    if filters['free']:
        queryset = queryset.filter(Q(is_donation=True) | Q(price=0))
    if filters['max_price'] is not None:
        queryset = queryset.filter(price__lte=filters['max_price'])
    if filters['min_price'] is not None:
        queryset = queryset.filter(price__gte=filters['min_price'])
    return queryset.order_by(ordering)


def _explain(parsed):
    understood = parsed['understood']
    if not understood:
        return 'Showing the newest books near you.'
    text = ' · '.join(understood)
    relaxed = parsed.get('relaxed_location')
    if relaxed:
        text = re.sub(r' ?· ?Near [^·]+$', '', text)
        text += f' · Nothing in {relaxed} yet, so these are from nearby areas'
    return text
