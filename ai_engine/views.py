"""JSON endpoints and the AI hub page.

Everything here is defensive: an AI helper must never be able to break the
marketplace, so every view catches its own errors, returns a friendly JSON
message, and logging failures are swallowed.
"""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST

from books.models import Book
from core.ratelimit import friendly_message, throttled

from .assistant import parse_query, search
from .classify import predict_category
from .describe import draft_description
from .models import AIEvent
from .pricing import suggest_price
from .recommend import picks_for_user, taste_profile
from .trust import assess_listing


def _payload(request):
    if 'application/json' in (request.content_type or ''):
        try:
            return json.loads(request.body or b'{}')
        except (TypeError, ValueError):
            return {}
    return request.POST


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _log(kind, request, payload=None, book=None):
    try:
        AIEvent.objects.create(
            kind=kind,
            user=request.user if getattr(request.user, 'is_authenticated', False) else None,
            book=book,
            payload=payload or {},
        )
    except Exception:
        # Analytics must never take the feature down with it.
        pass


def _image_url(book):
    if not book.image:
        return ''
    try:
        return book.image.url
    except ValueError:
        return ''


def book_json(book):
    return {
        'id': book.pk,
        'title': book.title,
        'author': book.author,
        'price': float(book.price),
        'is_donation': book.is_donation or float(book.price) == 0,
        'condition': book.get_condition_display(),
        'category': book.category.name if book.category else '',
        'area': book.location_area or book.location_city or 'Nearby',
        'image': _image_url(book),
        'url': reverse('books:book_detail', args=[book.pk]),
    }


def _rate_limited(request):
    message = throttled(request, 'ai')
    if message:
        return JsonResponse({'ok': False, 'error': message}, status=429)
    return None


def suggest_price_api(request):
    """Price suggestion — GET so the sell form can call it without a token."""
    data = _payload(request)
    result = suggest_price(
        category_id=_int(data.get('category')),
        condition=(data.get('condition') or 'good').strip(),
        title=(data.get('title') or '').strip()[:200],
        original_price=_number(data.get('original_price')),
        exclude_id=_int(data.get('exclude')),
    )
    _log('price', request, {
        'category': result['basis'],
        'sample': result['sample_size'],
    })
    return JsonResponse({'ok': True, **result})


@require_POST
def describe_api(request):
    limited = _rate_limited(request)
    if limited:
        return limited

    data = _payload(request)
    description = draft_description(
        title=(data.get('title') or '').strip(),
        author=(data.get('author') or '').strip(),
        category=(data.get('category_name') or '').strip(),
        condition=(data.get('condition') or 'good').strip(),
        price=_number(data.get('price')),
        is_donation=str(data.get('is_donation')).lower() in ('1', 'true', 'yes', 'on'),
        original_price=_number(data.get('original_price')),
        area=(data.get('area') or '').strip(),
        city=(data.get('city') or '').strip(),
        notes=(data.get('notes') or '').strip()[:400],
    )
    _log('describe', request)
    return JsonResponse({'ok': True, 'description': description})


@require_POST
def classify_api(request):
    limited = _rate_limited(request)
    if limited:
        return limited

    data = _payload(request)
    categories = predict_category(
        title=(data.get('title') or '').strip(),
        description=(data.get('description') or '').strip()[:800],
        author=(data.get('author') or '').strip(),
    )
    _log('classify', request, {'results': len(categories)})
    return JsonResponse({'ok': True, 'categories': categories})


@login_required
@require_POST
def risk_api(request):
    limited = _rate_limited(request)
    if limited:
        return limited

    data = _payload(request)
    assessment = assess_listing(
        title=(data.get('title') or '').strip(),
        description=(data.get('description') or '').strip(),
        price=_number(data.get('price')),
        category_id=_int(data.get('category')),
        seller=request.user,
        image_present=str(data.get('has_image')).lower() in ('1', 'true', 'yes', 'on'),
    )
    _log('risk', request, {'level': assessment['level'], 'score': assessment['score']})
    return JsonResponse({'ok': True, **assessment})


def assistant_search_api(request):
    raw = (request.GET.get('q') or '').strip()[:200]
    if not raw:
        return JsonResponse({'ok': False, 'error': 'Type what you are looking for.'}, status=400)

    limited = _rate_limited(request)
    if limited:
        return limited

    parsed = search(raw, viewer=request.user)
    payload = {
        'ok': True,
        'query': raw,
        'filters': {
            'category': parsed['filters']['category_name'],
            'max_price': parsed['filters']['max_price'],
            'free': parsed['filters']['free'],
            'condition': parsed['filters']['condition'],
            'location': parsed['filters']['location'],
            'sort': parsed['filters']['sort'],
            'keywords': parsed['filters']['q'],
        },
        'understood': parsed['understood'],
        'explanation': parsed['explanation'],
        'count': parsed['count'],
        'results': [book_json(book) for book in parsed['results']],
    }
    _log('search', request, {'query': raw[:80], 'count': parsed['count']})
    return JsonResponse(payload)


def ai_hub(request):
    """The BookBridge AI page: assistant search, picks and an explainer."""
    picks = picks_for_user(request.user, limit=8) if request.user.is_authenticated else []
    profile = taste_profile(request.user) if request.user.is_authenticated else {'categories': [], 'authors': []}

    examples = [
        'NEET books under ₹300 near Madhapur',
        'cheapest JEE books',
        'free novels in Hyderabad',
        'engineering books like new',
        'books above 200 for commerce',
    ]

    return render(request, 'ai_engine/ai_hub.html', {
        'picks': picks,
        'taste': profile,
        'examples': examples,
        'feature_count': AIEvent.KIND_CHOICES,
    })


def similar_api(request, pk):
    """'More like this' for a book, with the reason behind each pick."""
    from .recommend import similar_books

    book = Book.objects.filter(pk=pk).first()
    if not book:
        return JsonResponse({'ok': False, 'error': 'Book not found.'}, status=404)
    results = similar_books(book, limit=6, viewer=request.user)
    return JsonResponse({
        'ok': True,
        'results': [
            {**book_json(item['book']), 'score': item['score'], 'reason': item['reason']}
            for item in results
        ],
    })


def parse_api(request):
    """Debug-friendly view of how the assistant understood a query."""
    raw = (request.GET.get('q') or '').strip()[:200]
    parsed = parse_query(raw)
    return JsonResponse({'ok': True, 'query': raw, 'filters': parsed['filters'],
                         'understood': parsed['understood']})
