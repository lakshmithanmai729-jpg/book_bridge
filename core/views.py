from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.models import BookRequest, ChatMessage, Notification, SellerReview, UserBlock
from books.models import Book, Category, Report, Wishlist


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

    # "Near me" must use the member's own area, never a hardcoded city.
    my_area = ''
    if request.user.is_authenticated:
        location = (getattr(getattr(request.user, 'profile', None), 'location', '') or '').strip()
        my_area = location.split(',')[0].strip() if location else ''
    my_area = my_area or request.GET.get('location', '').strip()

    novels = categories.filter(name__iexact='Novels').first()

    return render(request, 'core/home.html', {
        'nearby_books': nearby_books,
        'recent_books': recent_books,
        'boosted_books': boosted_books,
        'categories': categories,
        'wishlist_ids': wishlist_ids,
        'my_area': my_area,
        'novels_category_id': novels.pk if novels else '',
    })




def safety(request):
    """Public safety centre: how to trade, report and block safely."""
    return render(request, 'core/safety.html')


def healthz(request):
    """Liveness/readiness probe for load balancers and uptime monitors."""
    checks = {'database': 'ok'}
    healthy = True
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception as exc:  # pragma: no cover - only when the DB is down
        checks['database'] = f'error: {exc.__class__.__name__}'
        healthy = False

    checks['books'] = Book.objects.count()
    return JsonResponse(
        {'status': 'ok' if healthy else 'error', 'checks': checks},
        status=200 if healthy else 503,
    )


@staff_member_required
def staff_dashboard(request):
    """A one-page overview of the marketplace for the team."""
    now = timezone.now()
    week_ago = now - timedelta(days=7)

    books = Book.objects.all()
    stats = {
        'users': User.objects.count(),
        'new_users': User.objects.filter(date_joined__gte=week_ago).count(),
        'listings': books.count(),
        'active_listings': books.filter(is_sold=False, is_hidden=False).count(),
        'sold_listings': books.filter(is_sold=True).count(),
        'hidden_listings': books.filter(is_hidden=True).count(),
        'new_listings': books.filter(created_at__gte=week_ago).count(),
        'open_reports': Report.objects.filter(status=Report.STATUS_OPEN).count(),
        'reviews': SellerReview.objects.filter(is_hidden=False).count(),
        'messages': ChatMessage.objects.count(),
        'requests': BookRequest.objects.filter(status='open').count(),
        'notifications': Notification.objects.filter(is_read=False).count(),
        'blocks': UserBlock.objects.count(),
        'wishlist_saves': Wishlist.objects.count(),
    }

    recent_reports = (
        Report.objects.filter(status=Report.STATUS_OPEN)
        .select_related('book', 'reporter')
        .order_by('-created_at')[:8]
    )
    recent_books = books.select_related('seller').order_by('-created_at')[:8]
    recent_users = User.objects.order_by('-date_joined')[:8]

    return render(request, 'core/staff_dashboard.html', {
        'stats': stats,
        'recent_reports': recent_reports,
        'recent_books': recent_books,
        'recent_users': recent_users,
    })
