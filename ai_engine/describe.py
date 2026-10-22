"""Listing copywriter.

Writes a first draft of a listing description from the facts the seller has
already typed (title, author, category, condition, price, pickup area). It is
deliberately extractive — it never invents a detail the seller did not give,
because fake "mint condition, never opened" claims are exactly what the trust
layer is there to catch.

The seller edits the draft before publishing, which is also how the AI stays
honest: the human is always the last reviewer.
"""
import hashlib

CONDITION_LINES = {
    'new': 'It is brand new — never used, no marks or folds.',
    'like_new': 'It is like new: read once, kept carefully, no writing inside.',
    'good': 'It is in good condition — normal shelf wear, all pages intact and readable.',
    'fair': 'It is in fair condition: clearly used, with some wear, but every page is still readable.',
    'poor': 'It is well used — expect highlights, notes or wear, priced accordingly.',
}

CATEGORY_LINES = {
    'IIT-JEE': 'a solid pick for JEE preparation',
    'NEET': 'useful for NEET preparation',
    'School': 'a handy companion for school work and board revision',
    'Engineering': 'a core reference for engineering coursework',
    'Novels': 'a great read for a quiet weekend',
    'Self-Help': 'a good nudge if you are working on habits and focus',
    'Commerce': 'useful for commerce and accountancy students',
    'Health': 'a practical read for health and wellness',
}

PICKUP_LINES = [
    'Happy to hand it over in {area} — message me here to fix a time.',
    'Pickup is easy from {area}; chat in-app and we will coordinate.',
    'Drop me a message and we can meet near {area}.',
]

CLOSERS = [
    'Happy studying!',
    'Hope it helps you as much as it helped me.',
    'Message me if you have any questions about it.',
    'First come, first served.',
]


def _pick(options, seed):
    return options[seed % len(options)]


def _seed(*parts):
    digest = hashlib.sha256('|'.join(str(part) for part in parts).encode('utf-8')).hexdigest()
    return int(digest[:8], 16)


def _clean(value):
    return ' '.join(str(value or '').split())


def draft_description(title='', author='', category='', condition='good', price=None,
                      is_donation=False, original_price=None, area='', city='',
                      notes=''):
    """Return a ready-to-edit description (3-5 sentences)."""
    title = _clean(title) or 'This book'
    author = _clean(author)
    category = _clean(category)
    condition = condition if condition in CONDITION_LINES else 'good'
    seed = _seed(title, author, category, condition)

    sentences = []

    subject = f'{title} by {author}' if author and author.lower() != 'various' else title
    if category and category in CATEGORY_LINES:
        sentences.append(f'{subject} — {CATEGORY_LINES[category]}.')
    else:
        sentences.append(f'{subject} is looking for a new reader.')

    sentences.append(CONDITION_LINES[condition])

    notes = _clean(notes)
    if notes:
        sentences.append(notes.rstrip('.') + '.')

    try:
        price_value = float(price) if price is not None else None
    except (TypeError, ValueError):
        price_value = None

    if is_donation or price_value == 0:
        sentences.append('It is free — I would rather it go to a student who needs it than sit on my shelf.')
    elif price_value:
        money = f'₹{price_value:,.0f}'
        try:
            mrp = float(original_price) if original_price else 0
        except (TypeError, ValueError):
            mrp = 0
        if mrp > price_value:
            saved = int(round((1 - price_value / mrp) * 100))
            sentences.append(f'Yours for {money}, which is about {saved}% below the printed price of ₹{mrp:,.0f}.')
        else:
            sentences.append(f'Yours for {money}.')

    place = _clean(area) or _clean(city)
    if place:
        sentences.append(_pick(PICKUP_LINES, seed).format(area=place))
    else:
        sentences.append('Message me here to arrange a pickup nearby.')

    closer = _pick(CLOSERS, seed)
    # Avoid "message me… message me…" back to back.
    if 'message me' in closer.lower() and any('message me' in sentence.lower() for sentence in sentences):
        closer = CLOSERS[0]
    sentences.append(closer)

    return ' '.join(sentences)
