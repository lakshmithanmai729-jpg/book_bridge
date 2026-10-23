"""Populate BookBridge with a realistic demo dataset.

Usage:
    python manage.py seed_demo

Demo logins (password: bookbridge123):
    demo   – buyer / student account (Telegram contact preference)
    arjun  – seller, Telegram contact
    priya  – seller, WhatsApp contact
    rahul  – seller, in-app chat only

Production safety: demo accounts all share a public password, so a live site
never gets them. There are two ways to put content on a deployed demo:

    DEMO_MODE=1 (environment variable)   — seeds books, photos and chats, and
        gives every demo account an *unusable* password, so nobody can sign in
        as them. The marketplace simply looks populated. This is what the free
        Render deployment uses.

    --demo-passwords                     — also sets the shared README password.
        Only for a private staging site that nobody else can reach.
"""
import random
import tempfile
import textwrap
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from accounts.models import BookRequest, ChatMessage, Notification, SellerReview, UserProfile
from books.models import Book, Category, Report, Wishlist

PASSWORD = 'bookbridge123'

CATEGORIES = [
    'IIT-JEE', 'NEET', 'School', 'Engineering', 'Novels',
    'Self-Help', 'Commerce', 'Health',
]

USERS = [
    {
        'username': 'demo',
        'name': 'Lakshmi Thanmai',
        'email': 'demo@bookbridge.local',
        'location': 'Madhapur, Hyderabad',
        'phone': '9876500011',
        'telegram': 'bookbridge_demo',
        'preference': 'telegram',
    },
    {
        'username': 'arjun',
        'name': 'Arjun Reddy',
        'email': 'arjun@bookbridge.local',
        'location': 'Madhapur, Hyderabad',
        'phone': '9876500022',
        'telegram': 'arjun_reads',
        'preference': 'telegram',
    },
    {
        'username': 'priya',
        'name': 'Priya Sharma',
        'email': 'priya@bookbridge.local',
        'location': 'JNTU Campus, Hyderabad',
        'phone': '9876500033',
        'telegram': '',
        'preference': 'whatsapp',
    },
    {
        'username': 'rahul',
        'name': 'Rahul Verma',
        'email': 'rahul@bookbridge.local',
        'location': 'Ameerpet, Hyderabad',
        'phone': '9876500044',
        'telegram': '',
        'preference': 'in_app',
    },
]

BOOKS = [
    # title, author, category, price, mrp, seller, condition, area, city, pincode, description, donation, color pair
    ('Concepts of Physics — Volume 1', 'H. C. Verma', 'IIT-JEE', 260, 460, 'arjun', 'good',
     'Madhapur', 'Hyderabad', '500081',
     'Barely used HC Verma Vol 1. All pages intact, a few pencil notes in chapter 3. Perfect for JEE preparation.',
     False, ('#0284c7', '#0f172a')),
    ('Concepts of Physics — Volume 2', 'H. C. Verma', 'IIT-JEE', 240, 460, 'rahul', 'like_new',
     'Ameerpet', 'Hyderabad', '500016',
     'Like new condition, no markings. Bought last year for coaching but barely opened.',
     False, ('#0d9488', '#0f172a')),
    ('Objective NCERT at your Fingertips — Biology', 'MTG Editorial', 'NEET', 320, 650, 'priya', 'good',
     'JNTU Campus', 'Hyderabad', '500085',
     'Complete NEET biology companion. Chapter-wise questions with solutions. Slight wear on the cover.',
     False, ('#059669', '#14532d')),
    ('NCERT Physics Class 12 — Part 1', 'NCERT', 'School', 120, 200, 'arjun', 'good',
     'Madhapur', 'Hyderabad', '500081',
     'Latest NCERT edition, clean pages, name written on the first page. Great for board exam revision.',
     False, ('#4f46e5', '#1e1b4b')),
    ('NCERT Chemistry Class 12 — Part 2', 'NCERT', 'School', 110, 200, 'rahul', 'fair',
     'Ameerpet', 'Hyderabad', '500016',
     'Used for one academic year. Some highlighted lines, binding is strong.',
     False, ('#7c3aed', '#2e1065')),
    ('Engineering Mathematics', 'B. S. Grewal', 'Engineering', 380, 795, 'priya', 'good',
     'JNTU Campus', 'Hyderabad', '500085',
     'Standard B.Tech reference for semesters 1–2. Includes solved question papers tucked inside.',
     False, ('#b45309', '#451a03')),
    ('Introduction to Algorithms', 'Cormen, Leiserson, Rivest', 'Engineering', 640, 1295, 'arjun', 'like_new',
     'Madhapur', 'Hyderabad', '500081',
     'Third edition. Pristine condition, kept on a shelf through my CS degree.',
     False, ('#1d4ed8', '#0c1a3a')),
    ('Atomic Habits', 'James Clear', 'Self-Help', 190, 550, 'priya', 'good',
     'JNTU Campus', 'Hyderabad', '500085',
     'Read once, no markings. A practical guide to building better habits.',
     False, ('#ea580c', '#7c2d12')),
    ('The Alchemist', 'Paulo Coelho', 'Novels', 90, 250, 'rahul', 'fair',
     'Ameerpet', 'Hyderabad', '500016',
     'Well-loved paperback with a slightly worn spine — still a beautiful read.',
     False, ('#0f766e', '#042f2e')),
    ('Wings of Fire', 'A. P. J. Abdul Kalam', 'Novels', 100, 299, 'arjun', 'good',
     'Madhapur', 'Hyderabad', '500081',
     'Autobiography of Dr. Kalam. A must-read for every student.',
     False, ('#be123c', '#4c0519')),
    ('Indian Polity', 'M. Laxmikanth', 'Commerce', 350, 750, 'priya', 'good',
     'JNTU Campus', 'Hyderabad', '500085',
     'Sixth edition. Useful for UPSC and state service aspirants.',
     False, ('#334155', '#0f172a')),
    ('Gray\'s Anatomy for Students', 'Richard Drake', 'Health', 520, 1450, 'rahul', 'good',
     'Ameerpet', 'Hyderabad', '500016',
     'First-year MBBS anatomy textbook with clean diagrams. Light shelf wear.',
     False, ('#e11d48', '#4c0519')),
    ('Class 10 Science Question Bank', 'Educart', 'School', 0, 350, 'arjun', 'good',
     'Madhapur', 'Hyderabad', '500081',
     'Giving away this question bank for free — I have finished my boards. Come pick it up.',
     True, ('#16a34a', '#052e16')),
    ('Let Us C', 'Yashavant Kanetkar', 'Engineering', 140, 399, 'demo', 'good',
     'Madhapur', 'Hyderabad', '500081',
     'Classic C programming guide used for my first semester. No torn pages, a few pencil notes.',
     False, ('#0369a1', '#0c1a3a')),
    ('Ikigai', 'Héctor García', 'Self-Help', 160, 499, 'demo', 'like_new',
     'Madhapur', 'Hyderabad', '500081',
     'Read once, kept in perfect condition. A gentle book about finding purpose every day.',
     False, ('#b45309', '#451a03')),
    ('NEET Previous Year Papers', 'Allen Career Institute', 'NEET', 0, 400, 'priya', 'good',
     'JNTU Campus', 'Hyderabad', '500085',
     'Free to a serious aspirant. Includes 2015–2023 papers with answer keys.',
     True, ('#0e7490', '#083344')),
]


def make_cover(title, author, colors, target):
    """Create a simple, attractive placeholder cover so the demo looks complete."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    width, height = 480, 640
    top, bottom = colors
    image = Image.new('RGB', (width, height), top)
    draw = ImageDraw.Draw(image)

    # Vertical gradient
    top_rgb = tuple(int(top[i:i + 2], 16) for i in (1, 3, 5))
    bottom_rgb = tuple(int(bottom[i:i + 2], 16) for i in (1, 3, 5))
    for y in range(height):
        ratio = y / height
        color = tuple(int(top_rgb[i] * (1 - ratio) + bottom_rgb[i] * ratio) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)

    # Decorative shapes
    draw.ellipse([width - 190, -70, width + 90, 210], outline=(255, 255, 255), width=3)
    draw.ellipse([-90, height - 170, 160, height + 80], outline=(255, 255, 255), width=3)

    bold = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    regular = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    try:
        font_title = ImageFont.truetype(bold, 40)
        font_author = ImageFont.truetype(regular, 24)
        font_small = ImageFont.truetype(bold, 18)
    except Exception:
        font_title = font_author = font_small = ImageFont.load_default()

    y = 110
    for line in textwrap.wrap(title, width=17):
        draw.text((44, y), line, font=font_title, fill=(255, 255, 255))
        y += 50

    draw.text((44, y + 16), textwrap.shorten(author, width=30), font=font_author, fill=(226, 232, 240))
    draw.line([(44, height - 96), (width - 44, height - 96)], fill=(255, 255, 255), width=2)
    draw.text((44, height - 72), 'BOOKBRIDGE', font=font_small, fill=(203, 213, 225))

    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, 'JPEG', quality=88)
    return target


class Command(BaseCommand):
    help = 'Seed BookBridge with demo users, books, chats and book requests.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete previously seeded demo users and their listings first.',
        )
        parser.add_argument(
            '--if-empty',
            action='store_true',
            help='Only seed when the marketplace has no books yet (used by the start scripts).',
        )
        parser.add_argument(
            '--with-admin',
            action='store_true',
            help=(
                'Give the demo account full admin access so every backend screen '
                'can be shown in a demo (local preview only).'
            ),
        )
        parser.add_argument(
            '--force-demo',
            action='store_true',
            help='Seed the demo data even when DEBUG is off and DEMO_MODE is unset.',
        )
        parser.add_argument(
            '--demo-passwords',
            action='store_true',
            help=(
                'Give the demo accounts the shared README password. Only for a '
                'private staging site — on a public site DEMO_MODE seeds the '
                'same content with unusable passwords.'
            ),
        )

    def handle(self, *args, **options):
        demo_usernames = [spec['username'] for spec in USERS]

        # "--if-empty" means "until the demo content exists". Counting all
        # books would skip the demo whenever the owner had already added one
        # listing of their own — which is exactly what happens in practice.
        if options['if_empty'] and User.objects.filter(
            username__in=demo_usernames
        ).exists():
            self.stdout.write('Demo data is already present — skipping.')
            return

        demo_mode = getattr(settings, 'DEMO_MODE', False)
        allowed = (
            settings.DEBUG
            or demo_mode
            or options['force_demo']
            or options['demo_passwords']
        )

        # A live site must never get accounts whose password is printed in the
        # README. Categories are harmless and needed by the sell form, so those
        # are still created.
        if not allowed:
            created = 0
            for name in CATEGORIES:
                _, was_created = Category.objects.get_or_create(name=name)
                created += int(was_created)
            self.stdout.write(self.style.WARNING(
                'DEBUG is off and DEMO_MODE is not set — demo accounts were NOT '
                f'created (public password). Ensured {created} categories. Set '
                'DEMO_MODE=1 to fill the marketplace with demo books whose '
                'accounts cannot be signed into, or run this command with '
                '--demo-passwords on a private staging site.'
            ))
            return

        # Who is allowed to have a password that other people know?
        share_passwords = settings.DEBUG or options['force_demo'] or options['demo_passwords']
        if demo_mode and not share_passwords:
            self.stdout.write(
                'DEMO_MODE: seeding demo content with unusable passwords '
                '(nobody can sign in as these accounts).'
            )

        random.seed(7)

        if options['reset']:
            User.objects.filter(username__in=[u['username'] for u in USERS]).delete()
            self.stdout.write(self.style.WARNING('Removed previous demo users.'))

        categories = {}
        for name in CATEGORIES:
            category, _ = Category.objects.get_or_create(name=name)
            categories[name] = category

        users = {}
        for spec in USERS:
            user, created = User.objects.get_or_create(
                username=spec['username'],
                defaults={'email': spec['email']},
            )
            if created:
                if share_passwords:
                    user.set_password(PASSWORD)
                else:
                    # The content is public, the accounts are not.
                    user.set_unusable_password()
                user.save()
            profile = user.profile
            profile.name = spec['name']
            profile.phone_number = spec['phone']
            profile.location = spec['location']
            profile.telegram_username = spec['telegram']
            profile.contact_preference = spec['preference']
            # demo stays private (first name + hidden area), priya is public,
            # so the two modes can be compared side by side in the preview.
            profile.account_privacy = 'public' if spec['username'] == 'priya' else 'private'
            profile.save()
            if spec['username'] == 'demo' and options['with_admin'] and share_passwords:
                # Local preview / demo only. A live site never seeds demo
                # accounts at all (see the DEBUG guard above), so this stays a
                # presentation account that can open every backend screen.
                from django.contrib.auth.models import Permission

                user.is_staff = True
                user.is_superuser = True
                user.save(update_fields=['is_staff', 'is_superuser'])
                user.user_permissions.set(
                    Permission.objects.filter(
                        content_type__app_label__in=['books', 'accounts', 'auth'],
                        content_type__model__in=[
                            'book', 'report', 'category', 'bookimage',
                            'sellerreview', 'userblock', 'chatmessage',
                            'bookrequest', 'userprofile', 'notification',
                            'user', 'group',
                        ],
                    )
                )
            users[spec['username']] = user

        books = {}
        for spec in BOOKS:
            (title, author, category_name, price, mrp, seller_name, condition,
             area, city, pincode, description, donation, colors) = spec

            seller = users[seller_name]
            book, created = Book.objects.get_or_create(
                title=title,
                seller=seller,
                defaults={
                    'author': author,
                    'category': categories.get(category_name),
                    'price': price,
                    'original_price': mrp,
                    'condition': condition,
                    'description': description,
                    'location_area': area,
                    'location_city': city,
                    'pincode': pincode,
                    'contact_phone': seller.profile.phone_number,
                    'is_donation': donation,
                    'is_negotiable': not donation,
                },
            )
            books[title] = book

            if created and not book.image:
                filename = f"seed_{slugify(title)[:40]}.jpg"
                stored_name = f'book_images/{filename}'
                # Generate into a temporary folder, then hand the bytes to the
                # configured storage. That way the covers land in the database
                # (MEDIA_STORAGE=db) just as happily as on local disk.
                if not default_storage.exists(stored_name):
                    with tempfile.TemporaryDirectory() as tmp:
                        target = Path(tmp) / filename
                        make_cover(title, author, colors, target)
                        if target.exists():
                            with open(target, 'rb') as handle:
                                default_storage.save(stored_name, File(handle))
                if default_storage.exists(stored_name):
                    book.image.name = stored_name
                    book.save(update_fields=['image'])

        # A small, believable set of conversations.
        demo = users['demo']
        arjun = users['arjun']
        priya = users['priya']
        rahul = users['rahul']
        hv1 = books['Concepts of Physics — Volume 1']
        anatomy = books["Gray's Anatomy for Students"]

        ChatMessage.objects.filter(
            sender__in=[demo, arjun, priya], receiver__in=[demo, arjun, priya]
        ).delete()

        ChatMessage.objects.create(
            sender=demo, receiver=arjun, book=hv1,
            text='Hi Arjun! Is the HC Verma Vol 1 still available?', is_read=True,
        )
        ChatMessage.objects.create(
            sender=arjun, receiver=demo, book=hv1,
            text='Yes it is! Barely used, only a few pencil notes in chapter 3.', is_read=True,
        )
        ChatMessage.objects.create(
            sender=demo, receiver=arjun, book=hv1,
            text='Great. Could you do ₹220 if I pick it up in Madhapur tomorrow?', is_read=False,
        )

        ChatMessage.objects.create(
            sender=demo, receiver=priya, book=anatomy,
            text='Hello Priya, is the anatomy book still there? I need it for first year.',
            is_read=True,
        )
        ChatMessage.objects.create(
            sender=priya, receiver=demo, book=anatomy,
            text='It is available. I can meet near JNTU metro around 5 pm.', is_read=True,
        )
        ChatMessage.objects.create(
            sender=demo, receiver=priya, book=anatomy,
            text='Perfect, see you there. Please keep it aside for me.', is_read=True,
        )

        BookRequest.objects.filter(user=demo).delete()
        BookRequest.objects.create(
            user=demo,
            book_title='Organic Chemistry — Morrison & Boyd',
            category='NEET',
            location='Madhapur, Hyderabad',
            notes='Need the 7th edition. Budget around ₹300. Can pick up anywhere in Hyderabad.',
        )
        BookRequest.objects.create(
            user=demo,
            book_title='Operating Systems — Galvin',
            category='Engineering',
            location='Madhapur, Hyderabad',
            notes='Any recent edition is fine, even with highlights.',
            status='fulfilled',
        )

        # ---- Trust & safety demo data: a few honest reviews so the badges show ----
        SellerReview.objects.filter(seller__username__in=['demo', 'arjun', 'priya']).delete()
        demo_books = list(Book.objects.filter(seller=demo))
        if demo_books:
            SellerReview.objects.create(
                reviewer=priya, seller=demo, book=demo_books[0],
                rating=5,
                comment='Very responsive and the book was exactly as described. Smooth pickup near the metro.',
            )
            SellerReview.objects.create(
                reviewer=arjun, seller=demo, book=demo_books[-1],
                rating=5,
                comment='Genuine seller. Kept the book aside for me and replied within minutes.',
            )
            SellerReview.objects.create(
                reviewer=rahul, seller=demo, book=demo_books[0],
                rating=4,
                comment='Good condition, fair price. Would buy again.',
            )
            SellerReview.invalidate_summary(demo.pk)

        arjun_books = list(Book.objects.filter(seller=arjun))
        if arjun_books:
            SellerReview.objects.create(
                reviewer=demo, seller=arjun, book=arjun_books[0],
                rating=4,
                comment='Slightly worn cover but all pages intact — good deal for the price.',
            )
            SellerReview.invalidate_summary(arjun.pk)

        # ---- Phase 3 demo notifications for the demo account ----
        Notification.objects.filter(recipient=demo).delete()
        if demo_books:
            Notification.objects.create(
                recipient=demo,
                actor=priya,
                book=demo_books[0],
                kind=Notification.KIND_PRICE_DROP,
                title=f'Price drop: {demo_books[0].title}',
                body='A book on your wishlist just got cheaper.',
                url=f'/books/{demo_books[0].pk}/',
            )
            Notification.objects.create(
                recipient=demo,
                actor=arjun,
                kind=Notification.KIND_REVIEW,
                title='New 5-star review ★★★★★',
                body='Genuine seller. Kept the book aside for me and replied within minutes.',
                url='/accounts/profile/',
            )

        # ---- Wishlists, a report and an AI usage log so every backend table
        #      has something to show during a demo. All of it is local-only
        #      demo data (a live site never seeds any of this). ----
        Wishlist.objects.filter(user__username__in=['demo', 'priya', 'rahul']).delete()
        sample_books = list(Book.objects.filter(is_sold=False, is_hidden=False)[:8])
        for index, book in enumerate(sample_books):
            if book.seller_id == demo.pk:
                continue
            buyer = [priya, rahul, demo][index % 3]
            if buyer.pk != book.seller_id:
                Wishlist.objects.get_or_create(user=buyer, book=book)

        Report.objects.filter(reporter__username__in=['arjun', 'priya', 'rahul']).delete()
        report_target = next((b for b in sample_books if b.seller_id != arjun.pk), None)
        if report_target:
            Report.objects.get_or_create(
                book=report_target,
                reporter=arjun,
                defaults={
                    'reason': 'wrong_price',
                    'details': 'Price looks higher than the printed MRP — please check.',
                },
            )

        from ai_engine.models import AIEvent

        AIEvent.objects.all().delete()
        ai_samples = [
            (AIEvent.KIND_PRICE, {'category': 'comparables', 'sample': 6}),
            (AIEvent.KIND_PRICE, {'category': 'comparables', 'sample': 4}),
            (AIEvent.KIND_PRICE, {'category': 'mrp', 'sample': 0}),
            (AIEvent.KIND_DESCRIBE, {}),
            (AIEvent.KIND_DESCRIBE, {}),
            (AIEvent.KIND_CLASSIFY, {'results': 3}),
            (AIEvent.KIND_CLASSIFY, {'results': 3}),
            (AIEvent.KIND_SEARCH, {'query': 'neet under 300', 'count': 2}),
            (AIEvent.KIND_SEARCH, {'query': 'free novels', 'count': 1}),
            (AIEvent.KIND_RISK, {'level': 'low', 'score': 8}),
            (AIEvent.KIND_RISK, {'level': 'medium', 'score': 34}),
            (AIEvent.KIND_RISK, {'level': 'high', 'score': 70}),
        ]
        for kind, payload in ai_samples:
            AIEvent.objects.create(kind=kind, user=demo, payload=payload)

        self.stdout.write(self.style.SUCCESS(
            f'Demo data ready: {len(users)} users, {Book.objects.count()} books, '
            f'{ChatMessage.objects.count()} chat messages, {BookRequest.objects.count()} requests, '
            f'{SellerReview.objects.count()} reviews, {Wishlist.objects.count()} wishlists, '
            f'{Report.objects.count()} reports, {AIEvent.objects.count()} AI events.'
        ))
        if share_passwords:
            self.stdout.write(
                'Sign in with demo / bookbridge123 (or arjun, priya, rahul — same password).'
            )
        else:
            self.stdout.write(
                'Demo accounts have unusable passwords on purpose: the marketplace '
                'looks populated but nobody can sign in as demo/arjun/priya/rahul. '
                'Use your own admin account.'
            )
