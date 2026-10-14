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
            avg_price = Book.objects.filter(category_id=cat_id, is_sold=False).aggregate(Avg('price'))['price__avg']
            if not avg_price:
                avg_price = Book.objects.filter(category_id=cat_id).aggregate(Avg('price'))['price__avg']
        except (ValueError, TypeError):
            avg_price = None

    if not avg_price:
        avg_price = Book.objects.filter(is_sold=False).aggregate(Avg('price'))['price__avg']
    if not avg_price:
        avg_price = Book.objects.aggregate(Avg('price'))['price__avg']
    if not avg_price:
        avg_price = 300

    multiplier = CONDITION_MULTIPLIER.get(condition, 0.7)
    return round(float(avg_price) * multiplier, 2)


def get_recommendations(book, limit=4):
    base_qs = Book.objects.filter(is_sold=False).exclude(pk=book.pk)
    rec_ids = []

    if book.category:
        cat_ids = list(base_qs.filter(category=book.category).values_list('id', flat=True)[:limit])
        rec_ids.extend(cat_ids)

    if len(rec_ids) < limit and book.author:
        author_ids = list(base_qs.filter(author__icontains=book.author).exclude(id__in=rec_ids).values_list('id', flat=True)[:limit - len(rec_ids)])
        rec_ids.extend(author_ids)

    if len(rec_ids) < limit:
        fallback_ids = list(base_qs.exclude(id__in=rec_ids).order_by('-created_at').values_list('id', flat=True)[:limit - len(rec_ids)])
        rec_ids.extend(fallback_ids)

    return Book.objects.filter(id__in=rec_ids).order_by('-created_at')




