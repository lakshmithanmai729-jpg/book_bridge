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
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(location_city__icontains=query) |
            Q(location_area__icontains=query) |
            Q(pincode__icontains=query)
        )

    location_query = request.GET.get('location')
    if location_query:
        books = books.filter(
            Q(location_city__icontains=location_query) |
            Q(location_area__icontains=location_query) |
            Q(pincode__icontains=location_query)
        )

    city = request.GET.get('city')
    if city:
        books = books.filter(location_city__iexact=city)

    pincode = request.GET.get('pincode')
    if pincode:
        books = books.filter(pincode__icontains=pincode)

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
    cities = Book.objects.exclude(location_city='').values_list('location_city', flat=True).distinct()

    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = Wishlist.objects.filter(user=request.user).values_list('book_id', flat=True)

    return render(request, 'books/book_list.html', {
        'books': books,
        'categories': categories,
        'cities': cities,
        'wishlist_ids': wishlist_ids,
    })


def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    recommendations = get_recommendations(book)
    return render(request, 'books/book_detail.html', {'book': book, 'recommendations': recommendations})


@login_required
def book_add(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        author = request.POST.get('author', '').strip() or 'Various'
        category_id = request.POST.get('category')
        price_val = request.POST.get('price', '0').strip()
        is_donation = request.POST.get('is_donation') == 'true'
        listing_type = request.POST.get('listing_type', 'single')
        condition = request.POST.get('condition', 'good')
        description = request.POST.get('description', '')

        # User profile defaults
        user_profile = getattr(request.user, 'profile', None)
        default_phone = user_profile.phone_number if user_profile else ''
        default_loc = user_profile.location if user_profile else 'Dhone, Andhra Pradesh'

        contact_phone = request.POST.get('contact_phone', '').strip() or default_phone
        location_area = request.POST.get('location_area', '').strip() or default_loc
        location_city = request.POST.get('location_city', '').strip() or 'Dhone'
        pincode = request.POST.get('pincode', '').strip() or '518222'

        image_file = request.FILES.get('image')

        try:
            price = float(price_val) if not is_donation else 0.0
        except ValueError:
            price = 0.0

        category = Category.objects.filter(id=category_id).first() if category_id else None

        book = Book.objects.create(
            seller=request.user,
            title=title,
            author=author,
            category=category,
            price=price,
            is_donation=is_donation,
            listing_type=listing_type,
            condition=condition,
            description=description,
            location_area=location_area,
            location_city=location_city,
            pincode=pincode,
            contact_phone=contact_phone,
            image=image_file,
        )
        return redirect('books:book_detail', pk=book.pk)
    else:
        categories = Category.objects.all()
        user_profile = getattr(request.user, 'profile', None)
    return render(request, 'books/book_form.html', {
        'categories': categories,
        'user_profile': user_profile,
    })


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
