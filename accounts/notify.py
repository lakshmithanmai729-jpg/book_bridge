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


# ---------------------------------------------------------------------------
# Buy requests ("I want this book") — the missing half of the marketplace.
# ---------------------------------------------------------------------------
def notify_buy_request(buy_request):
    """Tell the seller that somebody wants to buy their book."""
    try:
        book = buy_request.book
        buyer_name = _display_name(buy_request.buyer)
        meetup = f' · pickup: {buy_request.meetup}' if buy_request.meetup else ''
        return notify(
            buy_request.seller,
            Notification.KIND_BUY_REQUEST,
            f'{buyer_name} wants to buy “{book.title}”',
            f'\u20b9{buy_request.price:.0f}{meetup}. Open the request to accept or decline.',
            reverse('accounts:buy_requests') + '?tab=incoming',
            actor=buy_request.buyer,
            book=book,
        )
    except Exception:  # pragma: no cover - never break the buy flow
        logger.exception('buy-request notification failed')
        return None


def notify_buy_answer(buy_request, accepted):
    """Tell the buyer what the seller decided."""
    try:
        book = buy_request.book
        if accepted:
            title = f'Your buy request was accepted — “{book.title}”'
            body = (
                'The seller accepted. Open the chat to agree on a safe pickup '
                'place and pay on hand-over.'
            )
        else:
            title = f'“{book.title}” is no longer available for you'
            body = 'The seller declined this request. Browse similar books nearby.'
        return notify(
            buy_request.buyer,
            Notification.KIND_BUY_ANSWER,
            title,
            body,
            reverse('accounts:chat_detail', args=[buy_request.seller_id])
            + f'?book={book.pk}',
            actor=buy_request.seller,
            book=book,
        )
    except Exception:  # pragma: no cover
        logger.exception('buy-answer notification failed')
        return None


# ---------------------------------------------------------------------------
# Book requests — a buyer asks for a book they cannot find.
# ---------------------------------------------------------------------------
def notify_book_request_posted(book_request):
    """Tell the sellers who own something close to the requested book.

    This is the half that used to be missing entirely: the confirmation message
    said "nearby students will be notified" but no notification was ever
    created, so nothing happened.  Sellers now get a real bell notification and
    the buyer gets a receipt that the request is live.
    """
    from books.models import Book

    sent = 0
    try:
        wanted = (book_request.book_title or '').lower().strip()
        words = [word for word in wanted.split() if len(word) > 2]
        city = (book_request.location or '').strip().lower()

        candidates = (
            Book.objects
            .filter(is_sold=False, is_hidden=False)
            .exclude(seller_id=book_request.user_id)
            .select_related('category')
            .only('id', 'title', 'author', 'location_city', 'seller_id', 'category_id')
            .order_by('-created_at')[:400]
        )

        notified_ids = set()
        for book in candidates:
            if book.seller_id in notified_ids:
                continue
            title = (book.title or '').lower()
            author = (book.author or '').lower()
            matches_title = bool(wanted) and (
                wanted in title or title in wanted
                or any(word in title or word in author for word in words)
            )
            same_category = bool(
                book_request.category
                and book.category
                and book.category.name == book_request.category
            )
            same_city = bool(city) and city in (book.location_city or '').lower()
            # Near enough: the title looks like what they typed, or it is the
            # same category in the same town.  A title match wins anywhere.
            if not (matches_title or (same_category and same_city)):
                continue

            created = notify(
                book.seller,
                Notification.KIND_BOOK_REQUEST,
                f'Someone is looking for “{book_request.book_title}”',
                f'{_display_name(book_request.user)} posted a request'
                + (f' in {book_request.location}' if book_request.location else '')
                + '. You have a matching book — reply in chat.',
                reverse('books:book_detail', args=[book.pk]),
                actor=book_request.user,
                book=book,
            )
            if created:
                notified_ids.add(book.seller_id)
                sent += 1
                if sent >= 25:          # never spam a whole city in one go
                    break

        # A receipt for the buyer, so the bell shows the request went live even
        # if they close the tab straight away.
        notify(
            book_request.user,
            Notification.KIND_REQUEST_MATCH,
            f'Your request for “{book_request.book_title}” is live',
            f'We told {sent} seller' + ('s' if sent != 1 else '')
            + ' who may have this book. You will be notified when someone replies.',
            reverse('accounts:request_book'),
            book=None,
        )
        return sent
    except Exception:  # pragma: no cover
        logger.exception('book-request notification failed')
        return sent


def _display_name(user):
    """Prefer the profile name, fall back to the username."""
    try:
        profile = getattr(user, 'profile', None)
        if profile and profile.name:
            return profile.name[:60]
    except Exception:  # pragma: no cover
        pass
    return getattr(user, 'username', 'Someone')
