from datetime import timedelta

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.db import connection
from django.db.models import Count
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.static import serve as serve_from_disk

from accounts.models import BookRequest, ChatMessage, Notification, SellerReview, UserBlock
from ai_engine.models import AIEvent
from ai_engine.recommend import picks_for_user
from books.models import Book, Category, Report, Wishlist
from core.storage import DatabaseStorage


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

    # Personalised picks, with a reason on every card. Anonymous visitors get
    # an empty list and the section simply does not render.
    ai_picks = picks_for_user(request.user, limit=6) if request.user.is_authenticated else []

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
        'ai_picks': ai_picks,
    })




def safety(request):
    """Public safety centre: how to trade, report and block safely."""
    return render(request, 'core/safety.html')


def serve_media(request, path):
    """Serve an uploaded file, whichever storage backend is in use.

    Photos live in the database when ``MEDIA_STORAGE=db`` (so they survive a
    restart on a free host) and on disk otherwise. Both answer at the same
    ``/media/<path>`` URL, so templates never need to know the difference.
    """
    storage = default_storage

    if isinstance(storage, DatabaseStorage):
        from core.models import StoredFile

        try:
            row = StoredFile.objects.only('data', 'content_type', 'size').get(name=path)
        except StoredFile.DoesNotExist:
            raise Http404('No such photo.')

        response = HttpResponse(
            bytes(row.data),
            content_type=row.content_type or 'application/octet-stream',
        )
        response['Content-Length'] = row.size
        # Fingerprinted names never change content, and a book cover is not
        # secret — let the browser keep it for a day.
        response['Cache-Control'] = 'public, max-age=86400'
        return response

    return serve_from_disk(request, path, document_root=settings.MEDIA_ROOT, show_indexes=False)


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

    # --- AI layer: how much it is used, and which reported listings look risky ---
    ai_week = AIEvent.objects.filter(created_at__gte=week_ago)
    ai_usage = {
        'total': ai_week.count(),
        'by_kind': list(
            ai_week.values('kind').annotate(count=Count('id')).order_by('-count')
        ),
    }
    ai_kind_labels = dict(AIEvent.KIND_CHOICES)
    for row in ai_usage['by_kind']:
        row['label'] = ai_kind_labels.get(row['kind'], row['kind'])

    from ai_engine.trust import assess_listing
    risky_reports = []
    for report in recent_reports[:6]:
        try:
            assessment = assess_listing(
                title=report.book.title,
                description=report.book.description,
                price=report.book.price,
                category_id=report.book.category_id,
                seller=report.book.seller,
                image_present=bool(report.book.image),
                exclude_id=report.book_id,
            )
        except Exception:
            assessment = {'score': 0, 'level': 'low', 'reasons': []}
        risky_reports.append({'report': report, 'risk': assessment})

    return render(request, 'core/staff_dashboard.html', {
        'stats': stats,
        'recent_reports': recent_reports,
        'recent_books': recent_books,
        'recent_users': recent_users,
        'ai_usage': ai_usage,
        'risky_reports': risky_reports,
    })


# ---------------------------------------------------------------------------
# Backend tour — a presentation-friendly map of the whole backend.
#
# Built for demoing: every database table is listed with a live row count and a
# link straight into the Django admin, next to the API endpoints that can be
# opened in a browser. Nothing here writes data.
# ---------------------------------------------------------------------------

# Human descriptions shown on the tour page. Keyed by app_label.model_name.
MODEL_TOUR = {
    'books.book': {
        'label': 'Book listings',
        'icon': 'bi-book-half',
        'description': 'ప్రతి book listing — title, author, price, condition, photos, sold / hidden status.',
        'order': 1,
    },
    'books.category': {
        'label': 'Categories',
        'icon': 'bi-tags-fill',
        'description': 'Subjects / shelves: IIT-JEE, NEET, School, Engineering, Novels, Self-Help…',
        'order': 2,
    },
    'books.report': {
        'label': 'Reports',
        'icon': 'bi-flag-fill',
        'description': 'Buyers reporting a bad listing. Status: open → resolved. This is the moderation queue.',
        'order': 3,
    },
    'books.wishlist': {
        'label': 'Wishlists',
        'icon': 'bi-heart-fill',
        'description': 'Books each member saved. Feeds the AI recommendations.',
        'order': 4,
    },
    'accounts.userprofile': {
        'label': 'User profiles',
        'icon': 'bi-person-badge-fill',
        'description': 'Privacy (public/private), contact preference, Telegram handle, area, phone.',
        'order': 5,
    },
    'accounts.chatmessage': {
        'label': 'Chat messages',
        'icon': 'bi-chat-dots-fill',
        'description': 'In-app buyer ↔ seller conversations, stored per book.',
        'order': 6,
    },
    'accounts.bookrequest': {
        'label': 'Book requests',
        'icon': 'bi-search-heart-fill',
        'description': '“I need this book” requests from students.',
        'order': 7,
    },
    'accounts.sellerreview': {
        'label': 'Seller reviews',
        'icon': 'bi-star-fill',
        'description': 'Ratings and feedback that build seller trust.',
        'order': 8,
    },
    'accounts.notification': {
        'label': 'Notifications',
        'icon': 'bi-bell-fill',
        'description': 'Price-drop alerts, back-on-sale pings, request matches, review alerts.',
        'order': 9,
    },
    'accounts.userblock': {
        'label': 'Blocked members',
        'icon': 'bi-slash-circle-fill',
        'description': 'Who blocked whom. Blocked sellers are hidden everywhere, including AI results.',
        'order': 10,
    },
    'ai_engine.aievent': {
        'label': 'AI usage log',
        'icon': 'bi-stars',
        'description': 'Every AI call, as counts only (no personal text). Drives the AI usage panel.',
        'order': 11,
    },
    'auth.user': {
        'label': 'Accounts & permissions',
        'icon': 'bi-people-fill',
        'description': 'Login accounts, staff flags, granular permissions.',
        'order': 12,
    },
    'auth.group': {
        'label': 'Roles / groups',
        'icon': 'bi-person-gear',
        'description': 'Permission bundles you can assign to team members.',
        'order': 13,
    },
}

API_TOUR = [
    ('/healthz/', 'Health check', 'DB status + book count — what a load balancer pings'),
    ('/ai/api/parse/?q=neet under 300 near madhapur', 'AI query parser',
     'How the assistant understood the sentence'),
    ('/ai/api/search/?q=free novels', 'AI search', 'Parsed filters + matching books'),
    ('/ai/api/price/?category=2&condition=good', 'AI price', 'Fair price + comparables + confidence'),
    ('/ai/api/similar/1/', 'AI similar books', 'Recommendations with a reason each'),
    ('/sitemap.xml', 'Sitemap', 'SEO — every public URL'),
]


@staff_member_required
def backend_tour(request):
    """A one-page, clickable tour of the entire backend (for a demo/presentation)."""
    groups = {}
    for model in admin.site._registry:
        meta = model._meta
        key = f'{meta.app_label}.{meta.model_name}'
        info = MODEL_TOUR.get(key, {})
        try:
            count = model.objects.count()
        except Exception:                      # pragma: no cover - broker/db hiccup
            count = None
        entry = {
            'key': key,
            'label': info.get('label') or meta.verbose_name_plural.title(),
            'description': info.get('description', ''),
            'icon': info.get('icon', 'bi-table'),
            'order': info.get('order', 99),
            'count': count,
            'add_url': reverse(f'admin:{meta.app_label}_{meta.model_name}_add'),
            'url': reverse(f'admin:{meta.app_label}_{meta.model_name}_changelist'),
        }
        groups.setdefault(meta.app_label, []).append(entry)

    group_labels = {
        'books': ('Listings & marketplace', 'bi-journal-bookmark-fill', '#0284c7'),
        'accounts': ('Members & trust', 'bi-people-fill', '#7c3aed'),
        'ai_engine': ('AI layer', 'bi-stars', '#db2777'),
        'auth': ('Access control', 'bi-shield-lock-fill', '#0f766e'),
    }
    tour_groups = []
    for app_label in ('books', 'accounts', 'ai_engine', 'auth'):
        if app_label not in groups:
            continue
        label, icon, colour = group_labels[app_label]
        entries = sorted(groups[app_label], key=lambda item: item['order'])
        tour_groups.append({
            'app': app_label,
            'label': label,
            'icon': icon,
            'colour': colour,
            'models': entries,
            'total': sum(item['count'] or 0 for item in entries),
        })

    db_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:                          # pragma: no cover
        db_ok = False

    return render(request, 'core/backend_tour.html', {
        'tour_groups': tour_groups,
        'api_tour': API_TOUR,
        'db_ok': db_ok,
        'engine': connection.vendor,
        'is_superuser': request.user.is_superuser,
        'model_total': sum(len(group['models']) for group in tour_groups),
        'row_total': sum(group['total'] for group in tour_groups),
    })
