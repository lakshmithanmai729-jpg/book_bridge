"""Question answering over the live marketplace.

The assistant used to be a search box.  A student asking "how much is HC Verma"
got an empty grid, because "how much is" is not a title.  This module turns a
question into an answer built from real listings:

* **price**          — "how much is X"        → price, condition, seller rating
* **availability**   — "is X available"       → available / already sold
* **seller**         — "who is selling X"     → name + rating (never a phone)
* **category**       — "books for NEET"       → the listings in that shelf
* **budget / free**  — "under 300", "free"    → matching listings
* **location**       — "near Madhapur"        → listings in that area
* **cheapest**       — "cheapest novel"       → the single cheapest match
* **recommend**      — "suggest a novel"      → the recommendation engine
* **how_to_sell / how_payment / privacy / how_many / greeting** — static help

Rules that must not be broken:

1. Every book returned comes from the live queryset
   (``is_sold=False, is_hidden=False``) and respects user blocks.
2. **No phone number is ever produced**, even if one is in the description.
3. No raw HTML — the caller escapes; we only build plain text.
4. A question we cannot map becomes a search, and if that finds nothing the
   caller shows the refusal from ``scope.refusal_message``.

Everything is rule-based and offline: no API key, no cost, no latency, and the
student can always see *why* an answer came out the way it did.
"""
import re

from django.db.models import Q

from books.models import Book

from .assistant import parse_query, search
from .classify import CATEGORY_KEYWORDS
from .recommend import picks_for_user
from .scope import classify_scope

MAX_RESULTS = 4

PRICE_RE = re.compile(
    r'\b(?:under|below|less than|cheaper than|upto|up to|within|max|maximum)\s*'
    r'(?:rs\.?|inr|₹)?\s*(\d{2,6})'
)
TELUGU_PRICE_RE = re.compile(r'(\d{2,6})\s*(?:లోపు|కంటే తక్కువ)')

STOP_TITLE_WORDS = {
    'how', 'much', 'is', 'the', 'a', 'an', 'of', 'for', 'do', 'does', 'did',
    'what', 'whats', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why',
    'price', 'prices', 'cost', 'rate', 'rates', 'rupees', 'rs', 'inr', '₹',
    'book', 'books', 'novel', 'novels', 'textbook', 'copy', 'copies',
    'available', 'availability', 'still', 'there', 'left', 'stock', 'in',
    'sell', 'selling', 'seller', 'sold', 'by', 'any', 'some', 'have', 'has',
    'tell', 'me', 'about', 'please', 'pls', 'plz', 'sir', 'madam', 'kindly',
    'find', 'show', 'give', 'recommend', 'suggest', 'best', 'good', 'cheap',
    'cheapest', 'free', 'near', 'nearby', 'around', 'under', 'below', 'above',
    'over', 'less', 'more', 'than', 'upto', 'budget', 'maximum', 'max',
    'ధర', 'ఎంత', 'పుస్తకం', 'పుస్తకాలు', 'ఉందా', 'దొరుకుతుందా', 'కావాలి',
}


def _clean(text):
    return re.sub(r'\s+', ' ', (text or '')).strip()


def _base_queryset(viewer):
    """Available listings, minus anybody this viewer has blocked."""
    queryset = Book.objects.filter(is_sold=False, is_hidden=False).select_related(
        'category', 'seller', 'seller__profile'
    )
    if viewer is not None and getattr(viewer, 'is_authenticated', False):
        from accounts.models import UserBlock

        blocked = UserBlock.blocked_ids_for(viewer)
        if blocked:
            queryset = queryset.exclude(seller_id__in=blocked)
    return queryset


def _all_matching_queryset(viewer):
    """Including sold books — needed for "is this still available?"."""
    queryset = Book.objects.filter(is_hidden=False).select_related(
        'category', 'seller', 'seller__profile'
    )
    if viewer is not None and getattr(viewer, 'is_authenticated', False):
        from accounts.models import UserBlock

        blocked = UserBlock.blocked_ids_for(viewer)
        if blocked:
            queryset = queryset.exclude(seller_id__in=blocked)
    return queryset


def _title_words(text):
    """The part of the question that is probably a book title or author."""
    words = []
    for raw in re.findall(r'[A-Za-z0-9\u0C00-\u0C7F]+', text.lower()):
        if raw in STOP_TITLE_WORDS or len(raw) < 2:
            continue
        words.append(raw)
    return words


def _find_books(text, viewer, include_sold=False, limit=MAX_RESULTS):
    """Search the catalogue using the meaningful words of a question."""
    words = _title_words(text)
    queryset = _all_matching_queryset(viewer) if include_sold else _base_queryset(viewer)

    if not words:
        return [], queryset

    # Paragraph first: one query for every word, then relax if nothing matched.
    combined = queryset
    for word in words:
        combined = combined.filter(
            Q(title__icontains=word)
            | Q(author__icontains=word)
            | Q(category__name__icontains=word)
        )
    results = list(combined.order_by('-views_count')[:limit])
    if results:
        return results, queryset

    # Try each word on its own — "HC Verma physics" should still find the book.
    seen, relaxed = {}, []
    for word in words:
        for book in queryset.filter(
            Q(title__icontains=word) | Q(author__icontains=word)
        ).order_by('-views_count')[:limit]:
            if book.pk not in seen:
                seen[book.pk] = True
                relaxed.append(book)
        if len(relaxed) >= limit:
            break
    return relaxed[:limit], queryset


def _money(book):
    if book.is_donation or float(book.price) == 0:
        return 'free'
    return f'₹{float(book.price):,.0f}'


def _seller_name(book):
    profile = getattr(book.seller, 'profile', None)
    name = (profile.name if profile and profile.name else book.seller.username) or 'a student'
    return name.strip()


def _seller_rating(book):
    from accounts.models import SellerReview

    try:
        summary = SellerReview.summary_for(book.seller)
    except Exception:  # pragma: no cover - never break an answer over a rating
        return ''
    if not summary.get('count'):
        return ''
    return f"{summary['average']}★ ({summary['count']})"


def _where(book):
    place = book.location_area or book.location_city
    return place.strip() if place else ''


def _describe_one(book):
    bits = [_money(book)]
    condition = book.get_condition_display()
    if condition:
        bits.append(f'{condition} condition')
    where = _where(book)
    if where:
        bits.append(where)
    return ' · '.join(bits)


def _book_card(book):
    """The JSON the browser renders as a card."""
    from django.urls import reverse

    image = ''
    if book.image:
        try:
            image = book.image.url
        except ValueError:
            image = ''
    return {
        'id': book.pk,
        'title': book.title,
        'author': book.author,
        'price': float(book.price),
        'price_label': _money(book),
        'is_donation': bool(book.is_donation or float(book.price) == 0),
        'condition': book.get_condition_display(),
        'category': book.category.name if book.category else '',
        'area': _where(book) or 'Nearby',
        'seller': _seller_name(book),
        'seller_rating': _seller_rating(book),
        'image': image,
        'url': reverse('books:book_detail', args=[book.pk]),
    }


def _reply(answer, books=None, intent='search', suggestions=None):
    return {
        'intent': intent,
        'answer': _clean(answer),
        'books': [_book_card(book) for book in (books or [])],
        'suggestions': list(suggestions or []),
    }


DEFAULT_SUGGESTIONS = [
    'NEET books under ₹300',
    'cheapest novel',
    'how do I sell a book?',
    'books near Madhapur',
]


# ---------------------------------------------------------------------------
# Individual intents
# ---------------------------------------------------------------------------
def _answer_price(text, viewer):
    books, _ = _find_books(text, viewer)
    if not books:
        if not _title_words(text):
            return _reply(
                'Which book? Tell me the title or the author — for example '
                '“how much is HC Verma” or “NEET Previous Year Papers price”.',
                [], 'price', ['NEET books under ₹300', 'Cheapest book', 'Free books'],
            )
        return None
    book = books[0]
    rating = _seller_rating(book)
    seller = f' Sold by {_seller_name(book)}'
    seller += f', rated {rating}.' if rating else '.'
    others = len(books) - 1
    tail = f' {others} similar listing{"" if others == 1 else "s"} too.' if others > 0 else ''
    return _reply(
        f'“{book.title}” by {book.author} is {_describe_one(book)}.{seller}{tail}',
        books,
        'price',
        ['Is it still available?', 'Any cheaper option?', 'Books near me'],
    )


def _answer_availability(text, viewer):
    books, _ = _find_books(text, viewer, include_sold=True)
    if not books:
        return None
    book = books[0]
    if book.is_sold:
        alternatives, _ = _find_books(text, viewer)
        if alternatives:
            return _reply(
                f'“{book.title}” is already sold. Here is something close:',
                alternatives,
                'availability',
                ['Show similar books'],
            )
        return _reply(
            f'“{book.title}” is already sold, and nothing similar is listed right now. '
            'You can post a request and we will notify students who have it.',
            [], 'availability', ['Request this book', 'Browse all books'],
        )
    return _reply(
        f'Yes — “{book.title}” is available for {_describe_one(book)}.',
        books, 'availability', ['How much is it?', 'Chat with the seller', 'Buy it now'],
    )


def _answer_seller(text, viewer):
    books, _ = _find_books(text, viewer)
    if not books:
        return None
    book = books[0]
    rating = _seller_rating(book)
    detail = f' — rated {rating}' if rating else ''
    sold = book.seller.books.filter(is_sold=True).count()
    return _reply(
        f'“{book.title}” is listed by {_seller_name(book)}{detail}. '
        f'They have {sold} completed sale{"" if sold == 1 else "s"} on BookBridge. '
        'Open the chat to talk to them — your phone number stays private.',
        books, 'seller', ['Open this book', 'Chat with the seller'],
    )


def _answer_cheapest(text, viewer):
    from .assistant import search as assistant_search

    result = assistant_search(text, limit=12, viewer=viewer)
    books = result['results']
    shelf = result['filters'].get('category_name') or ''

    if not books:
        # "cheapest novel" on an empty shelf should still say something useful
        # rather than "nothing found" — fall back to the whole shop.
        cheap = list(_base_queryset(viewer).order_by('price')[:MAX_RESULTS])
        if not cheap:
            return None
        if shelf:
            return _reply(
                f'No {shelf} listings right now, so here are the cheapest books '
                'on BookBridge:',
                cheap, 'cheapest', ['Browse all books', 'Free books'],
            )
        return None

    cheapest = min(books, key=lambda b: (float(b.price), b.title.lower()))
    others = [b for b in books if b.pk != cheapest.pk][:MAX_RESULTS - 1]
    scope = f' in {shelf}' if shelf else ''
    free = cheapest.is_donation or float(cheapest.price) == 0
    tail = ' — free!' if free else '.'
    detail = ' · '.join(
        part for part in (
            cheapest.get_condition_display() + ' condition'
            if cheapest.get_condition_display() else '',
            _where(cheapest),
        ) if part
    )
    price_part = '' if free else f' at {_money(cheapest)}'
    return _reply(
        f'The cheapest{scope} is “{cheapest.title}”{price_part}'
        + (f' ({detail})' if detail else '')
        + tail,
        [cheapest] + others, 'cheapest',
        ['Show more options', 'Any free books?'],
    )


def _answer_recommend(text, viewer):
    # Use the shared parser: it already knows that "novel" means the Novels
    # shelf, and that "organic chemistry" means NEET.  (_title_words cannot do
    # this, because it deliberately strips words like "book" and "novel".)
    category_word = parse_query(text)['filters'].get('category_name') or ''
    if not category_word:
        tokens = set(_title_words(text))
        for name, words in CATEGORY_KEYWORDS.items():
            if name.lower() in text.lower() or any(w in tokens for w in words):
                category_word = name
                break

    queryset = _base_queryset(viewer)
    if category_word:
        queryset = queryset.filter(category__name__iexact=category_word)
    books = list(queryset.order_by('-views_count', '-created_at')[:MAX_RESULTS])

    if not books and category_word:
        # The shelf exists but is empty — do not pretend these are novels.
        return _reply(
            f'Nothing is listed under {category_word} this minute. '
            'Here is what students are looking at instead:',
            list(_base_queryset(viewer).order_by('-views_count')[:MAX_RESULTS]),
            'recommend', ['Books under ₹300', 'Free books', 'Post a request'],
        )
    if not books and viewer is not None and getattr(viewer, 'is_authenticated', False):
        books = [item['book'] for item in picks_for_user(viewer, limit=MAX_RESULTS)]
    if not books:
        books, _ = _find_books(text, viewer)
    if not books:
        return None

    shelf = f' for {category_word}' if category_word else ''
    return _reply(
        f'Good picks{shelf} right now:',
        books, 'recommend', ['Cheapest option', 'Free books', 'Books near me'],
    )


def _answer_free(text, viewer):
    books = list(
        _base_queryset(viewer)
        .filter(Q(is_donation=True) | Q(price=0))
        .order_by('-created_at')[:MAX_RESULTS]
    )
    if not books:
        return _reply(
            'No free books are listed this minute — but they appear often, so '
            'save a search or post a request and we will notify you.',
            [], 'free', ['Post a request', 'Browse all books'],
        )
    return _reply(
        f'{len(books)} free book{"" if len(books) == 1 else "s"} available:',
        books, 'free', ['Books under ₹200'],
    )


def _answer_budget(text, viewer):
    match = PRICE_RE.search(text.lower()) or TELUGU_PRICE_RE.search(text)
    if not match:
        return None
    budget = int(match.group(1))

    # Drop the budget phrase, then search what is left — but always honour the
    # promise the answer makes: every card shown is inside the budget.
    leftover = PRICE_RE.sub(' ', text)
    leftover = TELUGU_PRICE_RE.sub(' ', leftover)
    books, _ = _find_books(leftover, viewer) if _title_words(leftover) else ([], None)
    books = [b for b in books if float(b.price) <= budget]
    if not books:
        queryset = _base_queryset(viewer).filter(price__lte=budget)
        words = _title_words(leftover)
        if words:
            matching = [
                b for b in queryset
                if any(word in b.title.lower() or word in b.author.lower()
                       for word in words)
            ]
            if matching:
                queryset = _base_queryset(viewer).filter(
                    pk__in=[b.pk for b in matching]
                )
        books = list(queryset.order_by('price')[:MAX_RESULTS])
    if not books:
        return _reply(
            f'Nothing under ₹{budget:,} right now. The cheapest books are usually '
            'school and engineering guides — try a wider budget.',
            [], 'budget', ['Books under ₹500', 'Free books'],
        )
    return _reply(
        f'{len(books)} match{"" if len(books) == 1 else "es"} under ₹{budget:,}, '
        'cheapest first:',
        books, 'budget', ['Show more', 'Free books'],
    )


def _answer_category(text, viewer):
    from .assistant import search as assistant_search

    result = assistant_search(text, limit=MAX_RESULTS, viewer=viewer)
    if not result['results']:
        return None
    names = result['filters'].get('category_name')
    label = f'{names} books' if names else 'Books'
    extra = result.get('explanation') or ''
    return _reply(
        f'{label} available now{" — " + extra if extra else ""}:',
        result['results'], 'category', ['Cheapest in this list', 'Free books'],
    )


def _answer_count(text, viewer):
    base = _base_queryset(viewer)
    total = base.count()
    sold = Book.objects.filter(is_sold=True, is_hidden=False).count()

    # "how many NEET books?" wants the shelf count, not the whole shop.
    shelf = parse_query(text)['filters'].get('category_name') or ''
    if shelf:
        same = base.filter(category__name__iexact=shelf)
        count = same.count()
        noun = 'book' if count == 1 else 'books'
        if count:
            return _reply(
                f'There {"is" if count == 1 else "are"} {count} {shelf} {noun} '
                f'listed right now, out of {total} books in total:',
                list(same.order_by('price')[:MAX_RESULTS]), 'how_many',
                [f'Cheapest {shelf}', f'{shelf} books under \u20b9300'],
            )
        return _reply(
            f'No {shelf} books are listed right now. There are {total} books in '
            'other shelves — shall I show the cheapest ones?',
            list(base.order_by('price')[:MAX_RESULTS]), 'how_many',
            ['Cheapest book', 'Free books', 'Post a request'],
        )

    return _reply(
        f'There are {total} books listed right now, and {sold} have already been sold '
        'through BookBridge.',
        [], 'how_many', ['Browse all books', 'Newest listings'],
    )


def _answer_how_to_sell():
    return _reply(
        'Selling takes about two minutes:\n'
        '1. Tap “+ Sell Now” in the bottom bar.\n'
        '2. Add the title, author, price and a photo — the AI suggests a fair price.\n'
        '3. Save. Your listing appears instantly and buyers can chat with you.\n'
        'When someone taps Buy Now, you choose Accept or Decline. '
        'Your phone number is never shown.',
        [], 'how_to_sell', ['What price should I ask?', 'How does buying work?'],
    )


def _answer_how_payment():
    return _reply(
        'No money moves inside BookBridge, so there is nothing to pay here and no '
        'card details are ever stored. The buyer taps Buy Now, the seller accepts, '
        'you agree on a public place in chat, and you pay in cash or UPI when you '
        'meet. Never pay in advance.',
        [], 'how_payment', ['How do I sell a book?', 'Is my number private?'],
    )


def _answer_privacy():
    return _reply(
        'Your phone number is never shown on BookBridge. Buyers reach you through '
        'in-app chat, and you can also share a Telegram handle (which is not a phone '
        'number). Nobody can see your number unless you type it into a message '
        'yourself.',
        [], 'privacy', ['How does buying work?', 'How do I sell a book?'],
    )


def _answer_greeting(viewer):
    total = _base_queryset(viewer).count()
    return _reply(
        f'Hello! 👋 I am the BookBridge assistant. There are {total} books listed '
        'right now. Ask me about a book, a price, or how buying and selling works.',
        [], 'greeting', DEFAULT_SUGGESTIONS,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def answer_question(raw, viewer=None):
    """Answer a marketplace question, or explain politely why we cannot.

    Returns::

        {'ok': True, 'in_scope': bool, 'refused': bool, 'intent': str,
         'answer': str, 'books': [card, ...], 'suggestions': [str, ...],
         'decision': {...}}
    """
    from .scope import refusal_message

    text = _clean(raw)
    decision = classify_scope(text)

    if decision['is_empty']:
        return {
            'ok': True,
            'in_scope': True,
            'refused': False,
            'intent': 'empty',
            'answer': 'Ask me anything about books — a title, a subject, a price '
                      'limit, or how buying and selling works here.',
            'books': [],
            'suggestions': DEFAULT_SUGGESTIONS,
            'decision': decision,
        }

    if not decision['in_scope']:
        message, suggestions = refusal_message(text)
        return {
            'ok': True,
            'in_scope': False,
            'refused': True,
            'intent': 'off_topic',
            'answer': message,
            'books': [],
            'suggestions': suggestions,
            'decision': decision,
        }

    intent = decision['intent']

    # Order matters.  A question marked "price" that names nothing we recognise
    # should still fall through to a plain search.
    handlers = []
    if intent == 'greeting':
        handlers.append(lambda: _answer_greeting(viewer))
    if intent == 'price':
        handlers.append(lambda: _answer_price(text, viewer))
    if intent == 'how_many':
        # "how many books are there" also looks like availability, so the
        # count handler gets first refusal.
        handlers.append(lambda: _answer_count(text, viewer))
    if intent == 'availability':
        handlers.append(lambda: _answer_availability(text, viewer))
    if intent == 'seller':
        handlers.append(lambda: _answer_seller(text, viewer))
    if intent == 'how_to_sell':
        handlers.append(_answer_how_to_sell)
    if intent == 'how_payment':
        handlers.append(_answer_how_payment)
    if intent == 'privacy':
        handlers.append(_answer_privacy)
    if intent == 'free':
        handlers.append(lambda: _answer_free(text, viewer))
    if intent == 'cheapest':
        handlers.append(lambda: _answer_cheapest(text, viewer))
    if intent == 'recommend':
        handlers.append(lambda: _answer_recommend(text, viewer))
    if PRICE_RE.search(text.lower()) or TELUGU_PRICE_RE.search(text):
        handlers.append(lambda: _answer_budget(text, viewer))
    if intent == 'location' or decision['reason'] == 'book_vocabulary':
        handlers.append(lambda: _answer_category(text, viewer))

    for handler in handlers:
        try:
            reply = handler()
        except Exception:  # pragma: no cover - an answer must never 500
            reply = None
        if reply and (reply['answer']):
            reply['ok'] = True
            reply['in_scope'] = True
            reply['refused'] = False
            reply['decision'] = decision
            return reply

    # Nothing specific matched: run the normal search.
    try:
        result = search(text, limit=MAX_RESULTS, viewer=viewer)
        books = result['results']
    except Exception:  # pragma: no cover
        books = []

    if books:
        return {
            'ok': True,
            'in_scope': True,
            'refused': False,
            'intent': 'search',
            'answer': f'Here is what I found — {result["explanation"].lower()}',
            'books': [_book_card(book) for book in books],
            'suggestions': ['Cheapest option', 'Free books', 'Books near me'],
            'decision': decision,
        }

    # We understood nothing and found nothing.  Rather than an empty grid, say
    # so and offer something useful.
    if decision['reason'] == 'unknown':
        message, suggestions = refusal_message(text)
        return {
            'ok': True,
            'in_scope': False,
            'refused': True,
            'intent': 'off_topic',
            'answer': message,
            'books': [],
            'suggestions': suggestions,
            'decision': decision,
        }

    return {
        'ok': True,
        'in_scope': True,
        'refused': False,
        'intent': 'no_results',
        'answer': 'No listing matches that yet. Post a request and I will notify '
                  'students who have the book.',
        'books': [],
        'suggestions': ['Post a request', 'Books under ₹300', 'Cheapest novel'],
        'decision': decision,
    }
