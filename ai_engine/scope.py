"""Is this question about books, or is it off-topic?

The assistant used to be a search box: type "what's the weather" and it ran a
book query, found nothing, and showed an empty grid.  That is the wrong answer
to a question it was never able to answer, so every query now passes through
this module first.

The rules are deliberately simple and rule-based:

* **Book vocabulary** — a decent list of English *and* Telugu words.  One hit
  is enough to treat the question as ours.
* **Off-topic vocabulary** — weather, cricket, politics, coding, medical
  advice, homework solving.  These only matter when *no* book word is present,
  so "which book do I need for NEET biology" is still answered.
* **Neither** — we do not guess.  The caller runs a normal search and, if that
  finds nothing, falls back to a friendly "I only help with books".

Being instant and offline is the whole point: no API key, no model download,
and a student can see exactly why a question was refused.
"""
import re

# ---------------------------------------------------------------------------
# Words that make a question OURS.
# ---------------------------------------------------------------------------
BOOK_TERMS = {
    # the object itself, English
    'book', 'books', 'novel', 'novels', 'textbook', 'textbooks', 'title',
    'titles', 'author', 'authors', 'isbn', 'edition', 'editions', 'paperback',
    'hardcover', 'volume', 'guide', 'guides', 'notes', 'material', 'materials',
    'question bank', 'sample paper', 'workbook', 'syllabus', 'curriculum',
    'chapter', 'chapters', 'pages', 'series', 'magazine', 'comic', 'comics',
    # buying and selling
    'buy', 'buying', 'sell', 'selling', 'seller', 'sellers', 'purchase',
    'price', 'prices', 'pricing', 'cost', 'cheap', 'cheapest', 'expensive',
    'discount', 'offer', 'negotiable', 'negotiate', 'deal', 'handover',
    'pickup', 'delivery', 'available', 'availability', 'sold', 'list',
    'listing', 'listings', 'post', 'upload', 'stock',
    # condition and quality
    'condition', 'used', 'second hand', 'second-hand', 'secondhand', 'new',
    'like new', 'good', 'fair', 'poor', 'damaged', 'torn', 'worn', 'old',
    'fresh', 'review', 'reviews', 'rating', 'ratings', 'rated', 'trusted',
    'verified', 'wishlist', 'favourite', 'favorite', 'saved',
    # studies and exams
    'neet', 'jee', 'iit', 'aiims', 'gate', 'cat', 'upsc', 'cbse', 'icse',
    'ssc', 'inter', 'intermediate', 'degree', 'btech', 'b.tech', 'mba', 'ca',
    'foundation', 'exam', 'exams', 'entrance', 'semester', 'subject',
    'subjects', 'physics', 'chemistry', 'biology', 'botany', 'zoology',
    'maths', 'mathematics', 'math', 'english', 'hindi', 'telugu', 'sanskrit',
    'science', 'social', 'history', 'geography', 'economics', 'commerce',
    'accountancy', 'business', 'engineering',
    'medical', 'law', 'psychology', 'philosophy', 'literature', 'grammar',
    'atlas', 'dictionary', 'olympiad', 'competitive', 'computer science',
    'data structures', 'algorithms',
    # recommendation verbs
    'recommend', 'recommendation', 'recommendations', 'suggest', 'suggestion',
    'suggestions', 'similar', 'find', 'search', 'browse', 'discover',
    # misc helpers
    'shop', 'store', 'marketplace', 'bridge', 'student', 'students', 'college',
    'campus', 'library', 'cart', 'order', 'request',
}

# Telugu / transliterated Telugu.  The owner speaks Telugu and so do most of
# the students, so the guard must not refuse a question written in Telugu.
BOOK_TERMS_TELUGU = {
    'పుస్తకం', 'పుస్తకాలు', 'పుస్తకాల', 'పుస్తకము', 'బుక్', 'బుక్స్',
    'ధర', 'ధరలు', 'ఖరీదు', 'రేటు', 'ఎంత', 'ఎంతకు', 'తక్కువ', 'చౌక',
    'అమ్మాలి', 'అమ్ముతాను', 'అమ్మకం', 'అమ్మే', 'అమ్ముతున్నారు',
    'కొనాలి', 'కొంటాను', 'కొనడం', 'కొనే', 'కొనుగోలు',
    'ఉచితం', 'ఉచిత', 'ఫ్రీ', 'ఇవ్వాలి',
    'రచయిత', 'రచయితలు', 'ప్రచురణ', 'ఎడిషన్', 'కండిషన్', 'పరిస్థితి',
    'పాఠ్య', 'పాఠ్యపుస్తకం', 'నోట్స్', 'మెటీరియల్', 'సిలబస్',
    'పరీక్ష', 'పరీక్షలు', 'ఇంటర్', 'డిగ్రీ', 'ఇంజనీరింగ్', 'మెడికల్',
    'ఫిజిక్స్', 'కెమిస్ట్రీ', 'బయాలజీ', 'మ్యాథ్స్', 'సైన్స్', 'ఇంగ్లీష్',
    'తెలుగు', 'హిందీ', 'చరిత్ర', 'భూగోళం', 'ఎకనామిక్స్', 'కామర్స్',
    'సూచన', 'సూచించు', 'కావాలి', 'కావాలి?', 'దొరుకుతుందా', 'ఉందా',
    'ఎక్కడ', 'ఎవరు', 'అమ్మేవాళ్ళు', 'కొనేవాళ్ళు',
}

# Short words that are genuinely useful but too noisy on their own.
SHORT_BOOK_TERMS = {'rs', 'inr', '₹', 'ai'}

# ---------------------------------------------------------------------------
# Words that mean the question is not ours.  Matched only when no book word is
# present, so "which book helps with NEET biology" is still answered.
# ---------------------------------------------------------------------------
OFF_TOPIC_GROUPS = {
    'weather': {
        'weather', 'rain', 'raining', 'temperature', 'forecast', 'humidity',
        'climate', 'monsoon', 'sunny', 'cloudy', 'వాతావరణం', 'వర్షం',
    },
    'sports': {
        'cricket', 'cricketer', 'match', 'score', 'ipl', 'football', 'kabaddi',
        'tennis', 'olympics', 'goal', 'wicket', 'bcci', 'క్రికెట్', 'మ్యాచ్',
    },
    'entertainment': {
        'movie', 'movies', 'film', 'cinema', 'actor', 'actress', 'song',
        'songs', 'netflix', 'episode', 'episodes', 'serial', 'serials',
        'tv show', 'web series', 'trailer', 'నాటకం', 'సినిమా', 'పాట',
    },
    'politics': {
        'politics', 'election', 'elections', 'minister', 'cm', 'pm', 'party',
        'vote', 'government', 'parliament', 'రాజకీయ', 'ఎన్నిక', 'మంత్రి',
    },
    'coding': {
        'python', 'javascript', 'java', 'c++', 'html', 'css', 'react',
        'django', 'sql', 'program', 'programming', 'code', 'coding', 'debug',
        'debugging', 'compile', 'compiler error', 'stack trace', 'syntax error',
        'error in code', 'write a program', 'sql query', 'కోడ్',
    },
    'medical': {
        'symptom', 'symptoms', 'fever', 'headache', 'medicine dose',
        'tablet', 'doctor', 'hospital', 'covid', 'pain', 'జ్వరం', 'మందు',
        'డాక్టర్', 'ఆసుపత్రి',
    },
    'homework': {
        'homework', 'assignment', 'assignments', 'essay', 'essays',
        'solve this', 'solve the equation', 'answer this question',
        'essay on', 'write an essay', 'grammar correction', 'translate this',
        'homework help', 'do my homework',
    },
    'relationships': {
        'girlfriend', 'boyfriend', 'love', 'relationship', 'crush',
        'breakup', 'ప్రేమ', 'పెళ్లి',
    },
    'money': {
        'loan', 'emi', 'interest rate', 'investment', 'stock', 'share market',
        'crypto', 'bitcoin', 'salary', 'job vacancy', 'అప్పు',
    },
    'identity': {
        'who is', 'who was', 'what is the capital', 'president of',
        'chief minister', 'history of the world', 'ఎవరు',
    },
}

# Phrases that ask the assistant to answer a question that is not about books.
OFF_TOPIC_PHRASES = (
    'tell me a joke', 'write a poem', 'sing a song', 'what is the time',
    'what time is it', 'translate to', 'what is my name', 'how old are you',
    'are you human', 'are you real', 'who made you', 'who created you',
)

# Words that, on their own, mean nothing.  They are removed before we look for
# a book term, so "hi" or "hello there" is a greeting rather than a search.
GREETINGS = {'hi', 'hii', 'hello', 'hey', 'yo', 'namaste', 'namaskaram',
             'నమస్తే', 'నమస్కారం', 'హాయ్', 'హలో'}

FILLER = {
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'am', 'do',
    'does', 'did', 'can', 'could', 'would', 'should', 'will', 'shall', 'may',
    'might', 'must', 'i', 'me', 'my', 'mine', 'we', 'our', 'you', 'your',
    'he', 'she', 'it', 'its', 'they', 'them', 'their', 'this', 'that',
    'these', 'those', 'what', 'which', 'who', 'whom', 'whose', 'when',
    'where', 'why', 'how', 'any', 'some', 'please', 'pls', 'plz', 'sir',
    'madam', 'and', 'or', 'but', 'if', 'then', 'so', 'for', 'from', 'with',
    'without', 'of', 'to', 'in', 'on', 'at', 'by', 'about', 'near', 'around',
    'under', 'below', 'above', 'over', 'less', 'more', 'than', 'upto',
    'cheapest', 'cheap', 'newest', 'latest', 'recent', 'popular', 'show',
    'give', 'get', 'tell', 'need', 'want', 'looking', 'look', 'help', 'there',
    'here', 'now', 'today', 'ok', 'okay', 'thanks', 'thank', 'you', 'much',
    'many', 'very', 'really', 'im', 'iam', 'na', 'naku', 'nenu', 'meeku',
    'మీరు', 'నేను', 'నాకు', 'ఏమి', 'ఏం', 'ఎలా', 'ఎందుకు', 'దయచేసి',
}

TOKEN_RE = re.compile(r'[a-z0-9]+')
TELUGU_RE = re.compile(r'[\u0C00-\u0C7F]+')
PUNCT_RE = re.compile(r'[^\w\s\u0C00-\u0C7F]+')


def _normalise(text):
    """Lower-case, strip punctuation and collapse whitespace."""
    text = (text or '').lower().replace('₹', ' rs ')
    text = PUNCT_RE.sub(' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _tokens(normalised):
    return TOKEN_RE.findall(normalised)


def _book_hits(normalised, tokens):
    """Words in ``text`` that belong to the book domain."""
    hits = set()
    token_set = set(tokens)

    # Multi-word terms ("question bank", "like new") need a substring test.
    for term in BOOK_TERMS:
        if ' ' in term:
            if term in normalised:
                hits.add(term)
        elif term in token_set:
            hits.add(term)

    for word in SHORT_BOOK_TERMS:
        if word in token_set:
            hits.add(word)

    # Telugu words are matched as substrings: agglutination means "పుస్తకాలు",
    # "పుస్తకాలను" and "పుస్తకం" all share one stem.
    for word in BOOK_TERMS_TELUGU:
        if word in normalised:
            hits.add(word)

    return hits


def _off_topic_hits(normalised, tokens):
    """Return {group: matched words} for every off-topic group that fires."""
    found = {}
    token_set = set(tokens)
    for group, words in OFF_TOPIC_GROUPS.items():
        matched = set()
        for word in words:
            if ' ' in word:
                if word in normalised:
                    matched.add(word)
            elif word in token_set:
                matched.add(word)
        if matched:
            found[group] = matched

    for phrase in OFF_TOPIC_PHRASES:
        if phrase in normalised:
            found.setdefault('chit-chat', set()).add(phrase)
    return found


# Which intent does the question look like?  Used to pick the answer shape.
INTENT_PATTERNS = [
    ('greeting', re.compile(r'^(hi|hii|hello|hey|yo|namaste|namaskaram|నమస్తే|నమస్కారం|హాయ్|హలో)\b')),
    ('price', re.compile(
        r'\b(how much|price|cost|rate|kitna|ధర|ఎంత|ఖరీదు|రేటు)\b')),
    ('how_many', re.compile(
        r'\b(how many|count|total|number of)\b|\bఎన్ని\b')),
    ('availability', re.compile(
        r'\b(is|are|still).{0,20}(available|left|in stock)'
        r'|\bavailable\b|\bదొరుకుతుందా\b|\bఉందా\b')),
    ('seller', re.compile(
        r'\b(who|which)\b.{0,25}\b(sell|selling|seller|sold|అమ్మే)\b')),
    ('how_to_sell', re.compile(
        r'\bhow\b.{0,25}\b(sell|list|post|upload|అమ్మ)\b'
        r'|\b(ammanali|ammali|అమ్మాలి)\b')),
    ('how_payment', re.compile(
        r'\b(pay|payment|upi|cash|money|చెల్లించ|డబ్బు)\b')),
    ('privacy', re.compile(
        r'\b(phone|number|privacy|private|whatsapp|contact|నంబర్|ఫోన్)\b')),
    ('free', re.compile(r'\b(free|donation|donate|ఉచిత|ఫ్రీ)\b')),
    ('cheapest', re.compile(r'\b(cheap|cheapest|lowest|తక్కువ)\b')),
    ('recommend', re.compile(
        r'\b(recommend|suggest|similar|good|best|సూచన|మంచి)\b')),
    ('location', re.compile(r'\b(near|around|in)\s+\w+')),
]


def _detect_intent(normalised):
    for name, pattern in INTENT_PATTERNS:
        if pattern.search(normalised):
            return name
    return 'search'


def classify_scope(raw):
    """Decide whether a question belongs to BookBridge.

    Returns a plain dict so the caller (and the tests) can inspect exactly why
    a decision was made::

        {
            'in_scope': True,
            'reason': 'book_vocabulary',
            'confidence': 0.95,
            'intent': 'price',
            'matched': ['book', 'price'],
            'off_topic': {},
            'is_greeting': False,
            'is_empty': False,
        }
    """
    normalised = _normalise(raw)
    tokens = _tokens(normalised)
    meaningful = [t for t in tokens if t not in FILLER]

    result = {
        'query': (raw or '').strip(),
        'normalised': normalised,
        'in_scope': False,
        'reason': '',
        'confidence': 0.0,
        'intent': _detect_intent(normalised) if normalised else 'empty',
        'matched': [],
        'off_topic': {},
        'is_greeting': bool(tokens) and set(tokens) <= (GREETINGS | FILLER),
        'is_empty': not meaningful and not TELUGU_RE.search(normalised),
    }

    if not normalised:
        result['reason'] = 'empty'
        return result

    book_hits = _book_hits(normalised, tokens)
    off_hits = _off_topic_hits(normalised, tokens)
    result['matched'] = sorted(book_hits)[:8]
    result['off_topic'] = {group: sorted(words) for group, words in off_hits.items()}

    if book_hits:
        # A book word always wins: "which book for NEET biology" mentions
        # biology, which is also a medical word, and must still be answered.
        result['in_scope'] = True
        result['reason'] = 'book_vocabulary'
        result['confidence'] = 0.95
        if result['intent'] == 'search' and off_hits:
            # e.g. "movie based on this book" — still ours, just vague.
            result['confidence'] = 0.8
        return result

    if result['is_greeting']:
        result['in_scope'] = True
        result['reason'] = 'greeting'
        result['confidence'] = 1.0
        result['intent'] = 'greeting'
        return result

    if off_hits:
        result['reason'] = 'off_topic'
        result['confidence'] = 0.9
        result['off_topic_groups'] = sorted(off_hits)
        return result

    # No book word, no known off-topic word.  We honestly do not know: let the
    # caller try a normal search and decide based on whether anything matched.
    result['reason'] = 'unknown'
    result['confidence'] = 0.4
    result['in_scope'] = True
    return result


def refusal_message(raw='', suggestions=None):
    """The polite "this is a book shop" answer.

    Deliberately friendly rather than an error: the student asked a real
    question, we simply cannot help with that one.
    """
    suggestions = suggestions or [
        'NEET books under ₹300',
        'cheapest novel',
        'how do I sell a book?',
    ]
    decision = classify_scope(raw)
    topic = ''
    groups = decision.get('off_topic_groups') or list(decision.get('off_topic', {}))
    labels = {
        'weather': 'the weather',
        'sports': 'sports scores',
        'entertainment': 'TV shows, films and songs',
        'politics': 'politics',
        'coding': 'programming help',
        'medical': 'medical advice',
        'homework': 'solving homework for you',
        'relationships': 'personal advice',
        'money': 'loans and investments',
        'identity': 'general knowledge',
        'chit-chat': 'that',
    }
    if groups:
        topic = labels.get(groups[0], 'that')

    if topic:
        opener = f'I can only help with books — I cannot help with {topic}.'
    else:
        opener = 'I can only help with books and this marketplace.'

    return (
        f'{opener} 📚\n'
        'I can find books, tell you prices, check whether something is still '
        'available, and explain how buying and selling works here.\n'
        'Try one of these:'
    ), suggestions
