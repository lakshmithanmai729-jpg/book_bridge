from django.db.models import Avg
from books.models import Book

CONDITION_MULTIPLIER = {
    'new': 1.0,
    'like_new': 0.85,
    'good': 0.7,
    'fair': 0.5,
    'poor': 0.3,
}


def suggest_price(category_id, condition):
    avg_price = None
    if category_id:
        avg_price = Book.objects.filter(category_id=category_id).aggregate(Avg('price'))['price__avg']
    if not avg_price:
        avg_price = Book.objects.aggregate(Avg('price'))['price__avg']
    if not avg_price:
        avg_price = 300
    multiplier = CONDITION_MULTIPLIER.get(condition, 0.7)
    return round(float(avg_price) * multiplier, 2)


def get_recommendations(book, limit=4):
    recs = Book.objects.filter(category=book.category, is_sold=False).exclude(pk=book.pk)
    if recs.count() < limit:
        more = Book.objects.filter(author=book.author, is_sold=False).exclude(pk=book.pk)
        recs = (recs | more).distinct()
    return recs.order_by('-created_at')[:limit]



