from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from accounts.models import UserBlock
from books.models import Book, Category, Wishlist


def home(request):
    books = Book.objects.filter(is_sold=False, is_hidden=False)
    blocked_ids = UserBlock.blocked_ids_for(request.user)
    if blocked_ids:
        books = books.exclude(seller_id__in=blocked_ids)
    nearby_books = books.order_by('-created_at')[:8]
    recent_books = books.order_by('?')[:6]
    boosted_books = books.order_by('created_at')[:6]
    categories = Category.objects.all()

    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('book_id', flat=True))

    return render(request, 'core/home.html', {
        'nearby_books': nearby_books,
        'recent_books': recent_books,
        'boosted_books': boosted_books,
        'categories': categories,
        'wishlist_ids': wishlist_ids,
    })




def safety(request):
    """Public safety centre: how to trade, report and block safely."""
    return render(request, 'core/safety.html')
