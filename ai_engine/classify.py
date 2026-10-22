"""Category detection with a small multinomial Naive Bayes classifier.

Trained on the listings that already exist in the database (title + author +
description + current category) and blended with a keyword prior so it still
works on a brand-new marketplace with a handful of books.

No model files, no downloads: training happens in memory and is cached until
the catalogue changes.
"""
import math
import time
from collections import Counter, defaultdict

from books.models import Book, Category

from .text import tokenize

# Domain knowledge for an empty or tiny catalogue. Each keyword adds evidence
# for that category even before the marketplace has examples.
CATEGORY_KEYWORDS = {
    'IIT-JEE': [
        'jee', 'iit', 'mains', 'advanced', 'cengage', 'fiitjee', 'allen',
        'hc verma', 'irodov', 'wave optics', 'rotational',
    ],
    'NEET': [
        'neet', 'aiims', 'mbbs', 'biology', 'botany', 'zoology', 'anatomy',
        'physiology', 'organic chemistry', 'morrison', 'ncert biology',
    ],
    'School': [
        'cbse', 'icse', 'class 9', 'class 10', 'class 11', 'class 12', 'board',
        'school', 'social science', 'question bank', 'sample paper', 'olympiad',
    ],
    'Engineering': [
        'engineering', 'btech', 'b.tech', 'gate', 'cse', 'ece', 'mechanical',
        'civil', 'data structures', 'algorithms', 'operating systems', 'galvin',
        'cormen', 'dbms', 'compiler', 'digital electronics', 'let us c',
    ],
    'Novels': [
        'novel', 'fiction', 'story', 'stories', 'romance', 'mystery', 'thriller',
        'fantasy', 'classic', 'harry potter', 'chetan bhagat', 'ruskin bond',
    ],
    'Self-Help': [
        'self help', 'self-help', 'habits', 'atomic habits', 'mindset', 'ikigai',
        'rich dad', 'productivity', 'motivation', 'philosophy', 'psychology',
    ],
    'Commerce': [
        'commerce', 'accountancy', 'accounts', 'economics', 'business studies',
        'ca foundation', 'cost accounting', 'financial management', 'gst',
    ],
    'Health': [
        'health', 'nutrition', 'yoga', 'fitness', 'diet', 'medicine',
        'first aid', 'human body', 'wellness',
    ],
}
# A prior hit is worth about as much as seeing the word in two listings.
PRIOR_WEIGHT = 2.0

_CACHE = {'signature': None, 'trained_at': 0, 'model': None}
CACHE_SECONDS = 120


def _catalogue_signature():
    latest = Book.objects.order_by('-updated_at').values_list('updated_at', flat=True).first()
    return (Book.objects.count(), str(latest))


def _prior_hits(tokens, text):
    hits = defaultdict(float)
    joined = ' '.join(tokens)
    raw = (text or '').lower()
    for category, words in CATEGORY_KEYWORDS.items():
        for word in words:
            if ' ' in word:
                if word in raw:
                    hits[category] += PRIOR_WEIGHT
            elif word in tokens or word in joined:
                hits[category] += PRIOR_WEIGHT
    return hits


class NaiveBayesCategoryModel:
    def __init__(self):
        self.vocabulary = set()
        self.word_counts = defaultdict(Counter)
        self.class_counts = Counter()
        self.class_tokens = Counter()
        self.classes = []
        self.total_docs = 0

    def train(self, rows):
        """rows: iterable of (tokens, category_name)."""
        for tokens, label in rows:
            if not label or not tokens:
                continue
            self.classes.append(label)
            self.class_counts[label] += 1
            self.total_docs += 1
            self.class_tokens[label] += len(tokens)
            for token in tokens:
                self.word_counts[label][token] += 1
                self.vocabulary.add(token)
        self.classes = sorted(set(self.classes))

    def log_probabilities(self, tokens):
        if not self.classes:
            return {}
        vocab_size = max(len(self.vocabulary), 1)
        scores = {}
        for label in self.classes:
            # Laplace-smoothed prior
            score = math.log((self.class_counts[label] + 1) / (self.total_docs + len(self.classes)))
            denominator = self.class_tokens[label] + vocab_size
            counts = self.word_counts[label]
            for token in tokens:
                score += math.log((counts.get(token, 0) + 1) / denominator)
            scores[label] = score
        return scores

    def predict(self, tokens, text=''):
        scores = self.log_probabilities(tokens)
        prior = _prior_hits(tokens, text)

        if not scores and not prior:
            return []
        if not scores:
            scores = {label: 0.0 for label in prior}

        # Blend the learned model with the keyword prior in log space.
        for label in set(list(scores) + list(prior)):
            scores.setdefault(label, min(scores.values()) - 5.0 if scores else 0.0)
            if prior.get(label):
                scores[label] += math.log1p(prior[label]) * 2.0

        # Softmax for readable confidences.
        top = max(scores.values())
        weights = {label: math.exp(score - top) for label, score in scores.items()}
        total = sum(weights.values()) or 1.0
        ranked = sorted(
            ((label, weight / total) for label, weight in weights.items()),
            key=lambda item: item[1],
            reverse=True,
        )
        return ranked


def get_model():
    signature = _catalogue_signature()
    now = time.time()
    if _CACHE['model'] is not None and _CACHE['signature'] == signature and now - _CACHE['trained_at'] < CACHE_SECONDS:
        return _CACHE['model']

    model = NaiveBayesCategoryModel()
    rows = []
    for book in Book.objects.select_related('category').exclude(category=None).only(
        'title', 'author', 'description', 'category__name'
    ):
        text = f'{book.title} {book.author} {book.description}'
        rows.append((tokenize(text), book.category.name))
    model.train(rows)

    _CACHE.update({'signature': signature, 'trained_at': now, 'model': model})
    return model


def predict_category(title='', description='', author='', limit=3):
    """Return [{id, name, confidence}] — best guesses for a new listing."""
    text = f'{title} {author} {description}'
    tokens = tokenize(text)
    if not tokens:
        return []

    model = get_model()
    ranked = model.predict(tokens, text=text)

    categories = {category.name: category for category in Category.objects.all()}
    results = []
    for name, probability in ranked:
        category = categories.get(name)
        if not category:
            continue
        results.append({
            'id': category.pk,
            'name': category.name,
            'confidence': round(probability, 2),
        })
        if len(results) >= limit:
            break
    return results
