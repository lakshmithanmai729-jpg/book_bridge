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
        try:
            cat_id = int(category_id)
            avg_price = Book.objects.filter(category_id=cat_id, is_sold=False, is_hidden=False).aggregate(Avg('price'))['price__avg']
            if not avg_price:
                avg_price = Book.objects.filter(category_id=cat_id).aggregate(Avg('price'))['price__avg']
        except (ValueError, TypeError):
            avg_price = None

    if not avg_price:
        avg_price = Book.objects.filter(is_sold=False, is_hidden=False).aggregate(Avg('price'))['price__avg']
    if not avg_price:
        avg_price = Book.objects.aggregate(Avg('price'))['price__avg']
    if not avg_price:
        avg_price = 300

    multiplier = CONDITION_MULTIPLIER.get(condition, 0.7)
    return round(float(avg_price) * multiplier, 2)
