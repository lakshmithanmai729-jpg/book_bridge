import re
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from ai_engine.utils import get_recommendations

from .forms import BookForm
from .images import make_thumbnail, optimize_upload, save_optimized_image
from .models import Book, BookImage, Category, Report, Wishlist

PAGE_SIZE = 20


def _page(request, queryset, per_page=PAGE_SIZE):
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get('page'))


def _query_without_page(request):
    """Current querystring with ``page`` removed, for pagination links."""
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()


def book_list(request):
    books = Book.objects.filter(is_sold=False, is_hidden=False).select_related('category', 'seller')

    query = request.GET.get('q', '').strip()
    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(location_city__icontains=query) |
            Q(location_area__icontains=query) |
            Q(pincode__icontains=query)
        )

    location_query = request.GET.get('location', '').strip()
    if location_query:
        books = books.filter(
            Q(location_city__icontains=location_query) |
            Q(location_area__icontains=location_query) |
            Q(pincode__icontains=location_query)
        )

    city = request.GET.get('city', '').strip()
    if city:
        books = books.filter(location_city__iexact=city)

    pincode = request.GET.get('pincode', '').strip()
    if pincode:
        books = books.filter(pincode__icontains=pincode)

    category_id = request.GET.get('category', '').strip()
    if category_id:
        books = books.filter(category__id=category_id)

    condition = request.GET.get('condition', '').strip()
    if condition:
        books = books.filter(condition=condition)

    min_price = request.GET.get('min_price', '').strip()
    if min_price:
        try:
            books = books.filter(price__gte=float(min_price))
        except ValueError:
            pass

    max_price = request.GET.get('max_price', '').strip()
    if max_price:
        try:
            books = books.filter(price__lte=float(max_price))
        except ValueError:
            pass

    if request.GET.get('free') == '1':
        books = books.filter(is_donation=True)

    sort = request.GET.get('sort', '')
    if sort == 'price_low':
        books = books.order_by('price')
    elif sort == 'price_high':
        books = books.order_by('-price')
    elif sort == 'oldest':
        books = books.order_by('created_at')
    else:
        books = books.order_by('-created_at')

    page_obj = _page(request, books)
    categories = Category.objects.all()
    cities = (
        Book.objects.filter(is_hidden=False)
        .exclude(location_city='')
        .values_list('location_city', flat=True)
        .distinct()
    )

    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(
            Wishlist.objects.filter(user=request.user).values_list('book_id', flat=True)
        )

    # Chips + labels for the active filters, so they are easy to clear.
    active_filters = []
    for key, label in (
        ('q', 'Search'),
        ('location', 'Location'),
        ('category', 'Category'),
        ('condition', 'Condition'),
        ('min_price', 'Min price'),
        ('max_price', 'Max price'),
    ):
        value = request.GET.get(key)
        if value:
            active_filters.append({'key': key, 'label': label, 'value': value})

    return render(request, 'books/book_list.html', {
        'books': page_obj,
        'page_obj': page_obj,
        'paginator': page_obj.paginator,
        'categories': categories,
        'cities': cities,
        'wishlist_ids': wishlist_ids,
        'active_filters': active_filters,
        'query_without_page': _query_without_page(request),
        'conditions': Book.CONDITION_CHOICES,
        'result_count': page_obj.paginator.count,
    })


def _whatsapp_url(phone, message=''):
    """Build a wa.me link, adding India's 91 prefix to bare 10-digit numbers."""
    digits = re.sub(r'\D', '', phone or '')
    if len(digits) == 10:
        digits = '91' + digits
    if not digits:
        return ''
    url = f'https://wa.me/{digits}'
    if message:
        url += f'?text={quote(message)}'
    return url


def book_detail(request, pk):
    book = get_object_or_404(Book.objects.select_related('seller', 'category'), pk=pk)
    is_owner = request.user.is_authenticated and request.user.id == book.seller_id

    if book.is_hidden and not is_owner:
        return render(request, 'books/book_hidden.html', {'book': book}, status=404)

    # Cheap, race-free view counter (no full row save).
    Book.objects.filter(pk=book.pk).update(views_count=F('views_count') + 1)

    recommendations = get_recommendations(book)
    seller_profile = getattr(book.seller, 'profile', None)

    # Telegram is safe to show to everyone: a @handle never reveals a phone number.
    telegram_username = seller_profile.telegram_handle if seller_profile else ''
    telegram_url = seller_profile.telegram_url if seller_profile else ''

    # A phone number is only ever surfaced through WhatsApp when the seller
    # explicitly picked the WhatsApp / Call contact preference.
    whatsapp_url = ''
    if seller_profile and seller_profile.contact_preference == 'whatsapp' and book.contact_phone:
        whatsapp_url = _whatsapp_url(
            book.contact_phone,
            f'Hi {book.seller.username}, I am interested in your book "{book.title}" on BookBridge.',
        )

    already_reported = False
    if request.user.is_authenticated and not is_owner:
        already_reported = Report.objects.filter(
            book=book, reporter=request.user, status=Report.STATUS_OPEN
        ).exists()

    return render(request, 'books/book_detail.html', {
        'book': book,
        'recommendations': recommendations,
        'seller_profile': seller_profile,
        'is_owner': is_owner,
        'telegram_username': telegram_username,
        'telegram_url': telegram_url,
        'whatsapp_url': whatsapp_url,
        'already_reported': already_reported,
    })


def _save_gallery_images(book, files):
    """Store extra photos as compressed WebP, skipping files that fail validation."""
    saved, failed = 0, 0
    for uploaded_image in files:
        try:
            optimized = optimize_upload(uploaded_image)
            if optimized:
                BookImage.objects.create(book=book, image=optimized)
                saved += 1
        except ValidationError:
            failed += 1
    return saved, failed


@login_required
def book_add(request):
    categories = Category.objects.all()
    user_profile = getattr(request.user, 'profile', None)

    def form_context(**extra):
        """Re-render the listing form without losing what the seller typed."""
        context = {
            'categories': categories,
            'user_profile': user_profile,
            'form': request.POST or {},
        }
        context.update(extra)
        return context

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        author = request.POST.get('author', '').strip() or 'Various'
        category_id = (request.POST.get('category') or '').strip()
        price_val = request.POST.get('price', '0').strip()
        is_donation = request.POST.get('is_donation') == 'true'
        listing_type = request.POST.get('listing_type', 'single')
        condition = request.POST.get('condition', 'good')
        description = request.POST.get('description', '').strip()

        if not title:
            messages.error(request, 'Please enter the book name.')
            return render(request, 'books/book_form.html', form_context())

        default_phone = user_profile.phone_number if user_profile else ''
        default_loc = user_profile.location if user_profile else 'Dhone, Andhra Pradesh'

        contact_phone = request.POST.get('contact_phone', '').strip() or default_phone
        location_area = request.POST.get('location_area', '').strip() or default_loc
        location_city = request.POST.get('location_city', '').strip() or 'Dhone'
        pincode = request.POST.get('pincode', '').strip() or '518222'

        try:
            price = float(price_val) if not is_donation else 0.0
        except (TypeError, ValueError):
            price = 0.0

        # A stale or tampered category value must never crash the form.
        category = None
        if category_id.isdigit():
            category = Category.objects.filter(pk=int(category_id)).first()

        valid_conditions = {choice[0] for choice in Book.CONDITION_CHOICES}
        if condition not in valid_conditions:
            condition = 'good'
        if listing_type not in ('single', 'set'):
            listing_type = 'single'

        # Compress the cover before it ever reaches storage.
        optimized_cover = None
        try:
            optimized_cover = optimize_upload(request.FILES.get('image'))
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            return render(request, 'books/book_form.html', form_context())

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
        )
        if optimized_cover:
            book.image = optimized_cover
            book.save(update_fields=['image'])

        saved, failed = _save_gallery_images(book, request.FILES.getlist('images'))
        if failed:
            messages.warning(request, f'{failed} extra photo(s) were skipped because they were too large or invalid.')

        if not book.image and book.images.exists():
            book.image = book.images.first().image
            book.save(update_fields=['image'])

        messages.success(request, f'“{book.title}” is live! Buyers nearby can now see it.')
        return redirect('books:book_detail', pk=book.pk)

    return render(request, 'books/book_form.html', form_context())


@login_required
def book_edit(request, pk):
    book = get_object_or_404(Book, pk=pk, seller=request.user)
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            book = form.save()
            if book.image and not book.image.name.lower().endswith('.webp'):
                save_optimized_image(book, 'image')
            saved, failed = _save_gallery_images(book, request.FILES.getlist('images'))
            if failed:
                messages.warning(request, f'{failed} extra photo(s) were skipped.')
            if not book.image and book.images.exists():
                book.image = book.images.first().image
                book.save(update_fields=['image'])
            messages.success(request, 'Listing updated.')
            return redirect('books:book_detail', pk=book.pk)
        messages.error(request, 'Please check the highlighted fields.')
    else:
        form = BookForm(instance=book)
    return render(request, 'books/book_edit.html', {'form': form, 'book': book})


@login_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk, seller=request.user)
    if request.method == 'POST':
        title = book.title
        book.delete()
        messages.success(request, f'“{title}” was deleted.')
        return redirect('books:my_listings')
    return render(request, 'books/book_confirm_delete.html', {'book': book})


@login_required
def my_listings(request):
    """Seller dashboard: active, sold and hidden listings."""
    tab = request.GET.get('tab', 'active')
    base = Book.objects.filter(seller=request.user).select_related('category')

    if tab == 'sold':
        queryset = base.filter(is_sold=True)
    elif tab == 'hidden':
        queryset = base.filter(is_hidden=True, is_sold=False)
    else:
        tab = 'active'
        queryset = base.filter(is_sold=False, is_hidden=False)

    counts = {
        'active': base.filter(is_sold=False, is_hidden=False).count(),
        'sold': base.filter(is_sold=True).count(),
        'hidden': base.filter(is_hidden=True, is_sold=False).count(),
        'all': base.count(),
    }

    page_obj = _page(request, queryset.order_by('-created_at'), per_page=12)

    return render(request, 'books/my_listings.html', {
        'page_obj': page_obj,
        'books': page_obj,
        'tab': tab,
        'counts': counts,
        'query_without_page': _query_without_page(request),
    })


@login_required
@require_POST
def toggle_sold(request, pk):
    """Mark a listing as sold (or put it back on sale)."""
    book = get_object_or_404(Book, pk=pk, seller=request.user)
    book.mark_sold(not book.is_sold)
    if book.is_sold:
        messages.success(request, f'“{book.title}” marked as sold.')
    else:
        messages.success(request, f'“{book.title}” is back on sale.')
    return redirect(request.POST.get('next') or reverse('books:my_listings'))


@login_required
def report_book(request, pk):
    """Buyers report a listing; moderators review it in the admin."""
    book = get_object_or_404(Book, pk=pk)

    if request.user.id == book.seller_id:
        messages.info(request, 'You cannot report your own listing.')
        return redirect('books:book_detail', pk=book.pk)

    existing = Report.objects.filter(book=book, reporter=request.user, status=Report.STATUS_OPEN).first()

    if request.method == 'POST':
        if existing:
            messages.info(request, 'You already reported this listing. Our team is reviewing it.')
            return redirect('books:book_detail', pk=book.pk)

        reason = request.POST.get('reason', 'other')
        valid_reasons = {choice[0] for choice in Report.REASON_CHOICES}
        if reason not in valid_reasons:
            reason = 'other'

        details = request.POST.get('details', '').strip()[:2000]
        Report.objects.create(
            book=book,
            reporter=request.user,
            reason=reason,
            details=details,
        )
        messages.success(
            request,
            'Thanks for the report. Our moderation team will review this listing within 24 hours.',
        )
        return redirect('books:book_detail', pk=book.pk)

    return render(request, 'books/report_book.html', {
        'book': book,
        'reasons': Report.REASON_CHOICES,
        'existing': existing,
    })


@login_required
def wishlist_toggle(request, pk):
    book = get_object_or_404(Book, pk=pk)
    wishlist_item = Wishlist.objects.filter(user=request.user, book=book)
    if wishlist_item.exists():
        wishlist_item.delete()
        messages.info(request, f'Removed “{book.title}” from your favourites.')
    else:
        Wishlist.objects.create(user=request.user, book=book)
        messages.success(request, f'Saved “{book.title}” to your favourites.')
    return redirect(request.META.get('HTTP_REFERER') or reverse('books:book_list'))


@login_required
def wishlist_view(request):
    items = (
        Wishlist.objects.filter(user=request.user)
        .select_related('book', 'book__category')
        .order_by('-added_at')
    )
    page_obj = _page(request, items, per_page=20)
    return render(request, 'books/wishlist.html', {
        'items': page_obj,
        'page_obj': page_obj,
        'query_without_page': _query_without_page(request),
    })
