"""Text utilities for BookBridge's offline AI layer.

Pure Python on purpose: the app has to run on a free Render instance with no
GPU, no model download and no paid API key, so everything here is classical
NLP — tokenisation, TF-IDF vectors, cosine similarity and fuzzy matching.
"""
import math
import re
from collections import Counter
from difflib import SequenceMatcher

TOKEN_RE = re.compile(r'[a-z0-9]+')

# Short, English-heavy stop list — enough to keep the vectors meaningful
# without shipping a 500 KB word list.
STOPWORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'been', 'but', 'by', 'can',
    'for', 'from', 'has', 'have', 'he', 'her', 'his', 'i', 'if', 'in', 'is',
    'it', 'its', 'me', 'my', 'no', 'not', 'of', 'on', 'or', 'our', 'she',
    'so', 'that', 'the', 'their', 'them', 'then', 'there', 'these', 'they',
    'this', 'to', 'was', 'we', 'were', 'will', 'with', 'you', 'your', 'book',
    'books', 'copy', 'good', 'condition', 'used', 'new', 'edition',
}

# Words that carry a little extra weight when matching listings.
BOOST_TERMS = {
    'neet', 'jee', 'iit', 'cbse', 'icse', 'ncert', 'gate', 'cat', 'upsc',
    'engineering', 'medical', 'novel', 'fiction', 'poetry', 'biography',
    'organic', 'physics', 'chemistry', 'maths', 'mathematics', 'biology',
}


def tokenize(text):
    """Lower-case word tokens with stopwords and 1-letter noise removed."""
    if not text:
        return []
    tokens = [t for t in TOKEN_RE.findall(str(text).lower()) if len(t) > 1]
    return [t for t in tokens if t not in STOPWORDS]


def normalise(text):
    return ' '.join(tokenize(text))


def term_frequencies(tokens):
    return Counter(tokens)


def build_idf(documents):
    """Inverse document frequency for a list of token lists."""
    total = max(len(documents), 1)
    df = Counter()
    for tokens in documents:
        df.update(set(tokens))
    return {term: math.log((1 + total) / (1 + count)) + 1.0 for term, count in df.items()}


def vectorize(tokens, idf):
    """L2-normalised TF-IDF vector for one document."""
    if not tokens:
        return {}
    tf = term_frequencies(tokens)
    max_tf = max(tf.values()) or 1
    vector = {}
    for term, count in tf.items():
        weight = (count / max_tf) * idf.get(term, 1.0)
        if term in BOOST_TERMS:
            weight *= 1.6
        vector[term] = weight
    norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
    return {term: value / norm for term, value in vector.items()}


def cosine(left, right):
    """Cosine similarity of two normalised sparse vectors (0..1)."""
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(weight * right.get(term, 0.0) for term, weight in left.items())


def jaccard(left_tokens, right_tokens):
    left, right = set(left_tokens), set(right_tokens)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def fuzzy_ratio(left, right):
    """Character-level similarity — catches typos and reordered words."""
    return SequenceMatcher(None, (left or '').lower(), (right or '').lower()).ratio()


def keywords(text, limit=6):
    """Most informative tokens, in first-seen order (used in explanations)."""
    seen, picked = set(), []
    for token in tokenize(text):
        if token in seen:
            continue
        seen.add(token)
        picked.append(token)
        if len(picked) >= limit:
            break
    return picked
