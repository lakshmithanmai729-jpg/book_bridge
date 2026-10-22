"""Recommendations: content similarity + collaborative filtering.

Two signals are blended:

* **Content** — TF-IDF over title, author, category and description, so a
  biology guide is close to another biology guide even when the titles share
  no words.
* **Behaviour** — wishlist co-occurrence: "readers who saved this also saved…",
  plus a light popularity prior so a brand-new marketplace still shows
  something sensible.

Every recommendation carries a human-readable reason, because "AI says so" is
not a good enough answer for a student deciding what to buy.
"""
import math
import time
from collections import Counter, defaultdict

from books.models import Book, Wishlist

from .text import build_idf, cosine, tokenize, vectorize

_CACHE = {'signature': None, 'built_at': 0, 'index': None}


def _blocked_ids(user):
    """Sellers this viewer has blocked must never surface in AI results."""
    if not user or not getattr(user, 'is_authenticated', False):
        return set()
    try:
        from accounts.models import UserBlock
        return set(UserBlock.blocked_ids_for(user))
    except Exception:
        return set()
CACHE_SECONDS = 120


def _signature():
    latest = Book.objects.order_by('-updated_at').values_list('updated_at', flat=True).first()
    return (Book.objects.count(), str(latest))


def _document(book):
    # Repeat the title/author so they dominate the vector.
    return ' '.join([
        book.title, book.title,
        book.author or '',
        book.category.name if book.category else '',
        book.description or '',
    ])


def build_index(force=False):
    """In-memory TF-IDF index of every available book."""
    signature = _signature()
    now = time.time()
    if not force and _CACHE['index'] is not None and _CACHE['signature'] == signature \
            and now - _CACHE['built_at'] < CACHE_SECONDS:
        return _CACHE['index']

    books = list(
        Book.objects.filter(is_sold=False, is_hidden=False).select_related('category')
    )
    documents = [tokenize(_document(book)) for book in books]
    idf = build_idf(documents)
    vectors = {book.pk: vectorize(tokens, idf) for book, tokens in zip(books, documents)}

    _CACHE.update({'signature': signature, 'built_at': now, 'index': (books, vectors)})
    return _CACHE['index']


def _wishlist_pairs(exclude_user=None):
    """book_id -> Counter(other_book_id -> shared readers)."""
    pairs = defaultdict(Counter)
    rows = Wishlist.objects.values_list('user_id', 'book_id')
    by_user = defaultdict(list)
    for user_id, book_id in rows:
        if exclude_user and user_id == exclude_user:
            continue
        by_user[user_id].append(book_id)
    for book_ids in by_user.values():
        for left in book_ids:
            for right in book_ids:
                if left != right:
                    pairs[left][right] += 1
    return pairs


def similar_books(book, limit=6, viewer=None):
    """Books close to ``book``, with a short reason for each."""
    books, vectors = build_index()
    target = vectors.get(book.pk)
    if target is None:
        # The book may be sold/hidden and therefore absent from the index.
        target = vectorize(tokenize(_document(book)), build_idf([tokenize(_document(book))]))

    pairs = _wishlist_pairs()
    cooperative = pairs.get(book.pk, Counter())
    category_id = book.category_id
    hidden_sellers = _blocked_ids(viewer)

    scored = []
    for candidate in books:
        if candidate.pk == book.pk or candidate.seller_id in hidden_sellers:
            continue
        score = cosine(target, vectors.get(candidate.pk, {}))
        reasons = []

        if category_id and candidate.category_id == category_id:
            score += 0.18
            reasons.append('Same category')
        if book.author and candidate.author and book.author.strip().lower() == candidate.author.strip().lower():
            score += 0.22
            reasons.append('Same author')
        if cooperative.get(candidate.pk):
            score += 0.12 + 0.05 * min(cooperative[candidate.pk], 4)
            reasons.append('Readers who saved this also saved it')
        if book.price and candidate.price:
            gap = abs(float(book.price) - float(candidate.price)) / max(float(book.price), 1.0)
            if gap <= 0.3:
                score += 0.06

        if score <= 0.02:
            continue
        scored.append((score, candidate, reasons))

    scored.sort(key=lambda row: row[0], reverse=True)
    results = []
    for score, candidate, reasons in scored[:limit]:
        results.append({
            'book': candidate,
            'score': round(min(score, 1.0), 2),
            'reason': reasons[0] if reasons else 'Similar title and description',
        })
    return results


def picks_for_user(user, limit=8):
    """Personalised picks: wishlist similarity + category interest + area."""
    if not user or not user.is_authenticated:
        return []

    books, vectors = build_index()
    if not books:
        return []

    saved_ids = list(Wishlist.objects.filter(user=user).values_list('book_id', flat=True))
    saved_vectors = [vectors[book_id] for book_id in saved_ids if book_id in vectors]

    # Categories the student keeps asking for / chatting about.
    interest_categories = Counter()
    try:
        from accounts.models import BookRequest
        for request in BookRequest.objects.filter(user=user)[:20]:
            if request.category:
                interest_categories[request.category.strip().lower()] += 3
    except Exception:
        pass

    profile = getattr(user, 'profile', None)
    my_area = ''
    if profile and profile.location:
        my_area = profile.location.split(',')[0].strip().lower()

    owned = set(Book.objects.filter(seller=user).values_list('id', flat=True))
    hidden_sellers = _blocked_ids(user)
    max_views = max((book.views_count for book in books), default=0) or 1

    scored = []
    for candidate in books:
        if candidate.pk in owned or candidate.pk in saved_ids or candidate.seller_id in hidden_sellers:
            continue

        score = 0.0
        reasons = []

        if saved_vectors:
            best = max(cosine(vector, vectors.get(candidate.pk, {})) for vector in saved_vectors)
            if best > 0.08:
                score += best * 1.4
                if not reasons:
                    reasons.append('Because of books you saved')

        if candidate.category and interest_categories.get(candidate.category.name.lower()):
            score += 0.25
            reasons.append(f'Matches your {candidate.category.name} requests')

        if my_area and my_area in (candidate.location_area or '').lower():
            score += 0.15
            if not reasons:
                reasons.append(f'Nearby in {candidate.location_area}')

        score += 0.12 * (candidate.views_count / max_views)
        if candidate.pk >= max(book.pk for book in books) - 2:
            score += 0.05
            if not reasons:
                reasons.append('Newly listed')

        if score <= 0.05:
            continue
        scored.append((score, candidate, reasons))

    if len(scored) < limit:
        # Cold start: fall back to popular listings so the row is never empty.
        seen = {candidate.pk for _, candidate, _ in scored}
        for candidate in sorted(books, key=lambda book: book.views_count, reverse=True):
            if len(scored) >= limit:
                break
            if candidate.pk in seen or candidate.pk in owned or candidate.pk in saved_ids \
                    or candidate.seller_id in hidden_sellers:
                continue
            scored.append((0.04, candidate, ['Popular on BookBridge']))

    scored.sort(key=lambda row: row[0], reverse=True)
    picks = []
    for score, candidate, reasons in scored[:limit]:
        picks.append({
            'book': candidate,
            'score': round(min(score, 1.0), 2),
            'reason': reasons[0] if reasons else 'Picked for you',
        })
    return picks


def taste_profile(user, limit=5):
    """A few words describing what the student seems to like — used on the AI page."""
    saved = list(
        Wishlist.objects.filter(user=user).select_related('book', 'book__category')[:20]
    )
    categories = Counter()
    authors = Counter()
    for item in saved:
        if item.book.category:
            categories[item.book.category.name] += 1
        if item.book.author:
            authors[item.book.author] += 1
    return {
        'categories': [name for name, _ in categories.most_common(limit)],
        'authors': [name for name, _ in authors.most_common(limit)],
    }
