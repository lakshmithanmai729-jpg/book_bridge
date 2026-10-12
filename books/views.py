from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Book, Category, Wishlist
from .forms import BookForm
from ai_engine.utils import get_recommendations


def book_list(request):
    books = Book.objects.filter(is_sold=False)

    query = request.GET.get('q')
    if query:
        books = books.filter(Q(title__icontains=query) | Q(author__icontains=query))

    category_id = request.GET.get('category')
    if category_id:
        books = books.filter(category__id=category_id)

    condition = request.GET.get('condition')
    if condition:
        books = books.filter(condition=condition)

    min_price = request.GET.get('min_price')
    if min_price:
        books = books.filter(price__gte=min_price)

    max_price = request.GET.get('max_price')
    if max_price:
        books = books.filter(price__lte=max_price)

    sort = request.GET.get('sort')
    if sort == 'price_low':
        books = books.order_by('price')
    elif sort == 'price_high':
        books = books.order_by('-price')
    elif sort == 'newest':
        books = books.order_by('-created_at')

    categories = Category.objects.all()

    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = Wishlist.objects.filter(user=request.user).values_list('book_id', flat=True)

    return render(request, 'books/book_list.html', {
        'books': books,
        'categories': categories,
        'wishlist_ids': wishlist_ids,
    })


def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    recommendations = get_recommendations(book)
    return render(request, 'books/book_detail.html', {'book': book, 'recommendations': recommendations})


@login_required
def book_add(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            book.seller = request.user
            book.save()
            return redirect('books:book_list')
    else:
        form = BookForm()
    return render(request, 'books/book_form.html', {'form': form})


@login_required
def book_edit(request, pk):
    book = get_object_or_404(Book, pk=pk, seller=request.user)
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            return redirect('books:book_detail', pk=book.pk)
    else:
        form = BookForm(instance=book)
    return render(request, 'books/book_form.html', {'form': form})


@login_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk, seller=request.user)
    if request.method == 'POST':
        book.delete()
        return redirect('books:book_list')
    return render(request, 'books/book_confirm_delete.html', {'book': book})


@login_required
def wishlist_toggle(request, pk):
    book = get_object_or_404(Book, pk=pk)
    wishlist_item = Wishlist.objects.filter(user=request.user, book=book)
    if wishlist_item.exists():
        wishlist_item.delete()
    else:
        Wishlist.objects.create(user=request.user, book=book)
    return redirect(request.META.get('HTTP_REFERER', 'books:book_list'))


@login_required
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user).select_related('book')
    return render(request, 'books/wishlist.html', {'items': items})
