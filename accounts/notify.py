"""Notification helpers — one place for every "tell the user something" rule.

Notifications are stored in the database so they survive restarts and show up in
the bell menu.  Each helper is defensive: a notification must never break the
action that triggered it (saving a listing, posting a review, …).
"""
import logging

from django.urls import reverse

from .models import Notification, UserBlock

logger = logging.getLogger(__name__)


def notify(user, kind, title, body='', url='', actor=None, book=None):
    """Create one notification for ``user`` (silently ignored if not allowed)."""
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    if actor is not None and actor.pk == user.pk:
        return None
    if actor is not None and UserBlock.exists_between(user, actor):
        return None
    try:
        return Notification.objects.create(
            recipient=user,
            actor=actor,
            book=book,
            kind=kind,
            title=title[:200],
            body=body,
            url=url[:500],
        )
    except Exception:  # pragma: no cover - notifications must never break a save
        logger.exception('Could not create notification for %s', getattr(user, 'pk', None))
        return None


def _book_url(book):
    if not book:
        return ''
    try:
        return reverse('books:book_detail', args=[book.pk])
    except Exception:
        return ''


def _wishlist_users(book):
    """Everyone who saved this book, except the seller."""
    from books.models import Wishlist

    return (
        Wishlist.objects
        .filter(book=book)
        .exclude(user_id=book.seller_id)
        .select_related('user')
    )


def notify_price_drop(book, old_price, new_price):
    """Tell everyone who saved the book that the price just fell."""
    try:
        if old_price is None or new_price is None or float(new_price) >= float(old_price):
            return 0
        saved = float(old_price) - float(new_price)
        sent = 0
        for item in _wishlist_users(book):
            created = notify(
                item.user,
                Notification.KIND_PRICE_DROP,
                f'Price drop: {book.title}',
                f'Now ₹{float(new_price):.0f} — down ₹{saved:.0f} from ₹{float(old_price):.0f}.',
                _book_url(book),
                actor=book.seller,
                book=book,
            )
            if created:
                sent += 1
        return sent
    except Exception:  # pragma: no cover
        logger.exception('price-drop notifications failed for book %s', getattr(book, 'pk', None))
        return 0


def notify_back_on_sale(book):
    """A sold book was relisted — ping the people who wanted it."""
    try:
        sent = 0
        for item in _wishlist_users(book):
            created = notify(
                item.user,
                Notification.KIND_BACK_ON_SALE,
                f'Back on sale: {book.title}',
                'The seller relisted this book. Grab it before someone else does.',
                _book_url(book),
                actor=book.seller,
                book=book,
            )
            if created:
                sent += 1
        return sent
    except Exception:  # pragma: no cover
        logger.exception('relist notifications failed for book %s', getattr(book, 'pk', None))
        return 0


def notify_request_matches(book):
    """Match a brand-new listing against open book requests."""
    from .models import BookRequest

    try:
        title_words = [word for word in (book.title or '').lower().split() if len(word) > 2]
        if not title_words:
            return 0

        candidates = (
            BookRequest.objects
            .filter(status='open')
            .exclude(user_id=book.seller_id)
            .select_related('user')
        )

        sent = 0
        for request in candidates:
            wanted = (request.book_title or '').lower()
            if not wanted:
                continue
            matches_title = wanted in (book.title or '').lower() or any(
                word in wanted for word in title_words
            )
            same_category = bool(
                request.category and book.category and request.category == book.category.name
            )
            if not (matches_title or same_category):
                continue

            created = notify(
                request.user,
                Notification.KIND_REQUEST_MATCH,
                f'A book you asked for: {book.title}',
                f'Listed in {book.location_city or book.location_area or "your area"} '
                f'for ₹{float(book.price):.0f}.',
                _book_url(book),
                actor=book.seller,
                book=book,
            )
            if created:
                sent += 1
        return sent
    except Exception:  # pragma: no cover
        logger.exception('request matching failed for book %s', getattr(book, 'pk', None))
        return 0


def notify_new_review(review):
    """Tell a seller that a buyer rated them."""
    try:
        stars = '★' * int(review.rating)
        body = review.comment.strip() if review.comment else 'No comment left.'
        return notify(
            review.seller,
            Notification.KIND_REVIEW,
            f'New {review.rating}-star review {stars}',
            body[:300],
            reverse('accounts:seller_profile', args=[review.seller_id]) + '#reviews',
            actor=review.reviewer,
            book=review.book,
        )
    except Exception:  # pragma: no cover
        logger.exception('review notification failed for review %s', getattr(review, 'pk', None))
        return None
