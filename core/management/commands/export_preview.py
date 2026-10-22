"""Export the whole app to plain HTML files — no server needed.

Usage:
    python manage.py export_preview
    python manage.py export_preview --out ~/Desktop/bookbridge-preview
    python manage.py export_preview --zip

Why this exists: demos and reviews sometimes happen on a machine where you
cannot (or do not want to) start a web server. This command renders the pages
through Django's test client, rewrites the links so they work from the file
system, copies the static files and photos, and writes a cover page. The result
is a folder you can double-click, email, or put on a USB stick.

Limitations (by design, and stated on the cover page): forms do not submit and
JavaScript that calls the API does nothing — those need a running server or the
deployed site. Everything you would *show* in a walkthrough is real output from
the real templates.
"""
import json
import shutil
import re
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.test import Client, override_settings

from books.models import Book

# (url, file name, title, group, note)
PAGES = [
    ('/', 'index.html', 'Home', 'Frontend', 'Nearby books, category tiles and personalised AI picks.'),
    ('/books/', 'books.html', 'Browse books', 'Frontend', 'Search, filters and pagination over every listing.'),
    ('/ai/', 'ai.html', 'BookBridge AI', 'Frontend', 'Natural-language assistant plus explainable picks.'),
    ('/books/add/', 'sell.html', 'Sell a book', 'Frontend', 'Listing form with the AI helper panel (price, category, description, risk).'),
    ('/accounts/profile/', 'profile.html', 'Account', 'Frontend', 'Profile, privacy mode, contact preference and the staff menu.'),
    ('/books/my/', 'my-books.html', 'My books', 'Frontend', 'Seller dashboard: active, sold and hidden listings.'),
    ('/accounts/messages/', 'messages.html', 'Chats', 'Frontend', 'Buyer ↔ seller conversations.'),
    ('/accounts/notifications/', 'notifications.html', 'Notifications', 'Frontend', 'Price drops, back-on-sale pings, reviews.'),
    ('/accounts/analytics/', 'analytics.html', 'Seller analytics', 'Frontend', 'Views, saves, chats and per-listing performance.'),
    ('/accounts/request-book/', 'request-book.html', 'Book requests', 'Frontend', 'Ask nearby students for a book you cannot find.'),
    ('/books/wishlist/', 'wishlist.html', 'Wishlist', 'Frontend', 'Saved books.'),
    ('/safety/', 'safety.html', 'Safety centre', 'Frontend', 'How to trade safely, spot scams and report.'),

    ('/staff/', 'staff.html', 'Team dashboard', 'Backend', 'Marketplace numbers, AI usage and the risk queue.'),
    ('/backend/', 'backend-tour.html', 'Backend tour', 'Backend', 'All 13 tables with live counts, plus the API list.'),
    ('/admin/', 'admin.html', 'Django admin', 'Backend', 'Admin home — every model group.'),
    ('/admin/books/book/', 'admin-books.html', 'Admin · Books', 'Backend', 'All listings, searchable and filterable.'),
    ('/admin/books/report/', 'admin-reports.html', 'Admin · Reports', 'Backend', 'The moderation queue.'),
    ('/admin/books/category/', 'admin-categories.html', 'Admin · Categories', 'Backend', 'The shelves: IIT-JEE, NEET, School…'),
    ('/admin/accounts/notification/', 'admin-notifications.html', 'Admin · Notifications', 'Backend', 'Every alert sent to members.'),
    ('/admin/ai_engine/aievent/', 'admin-ai-events.html', 'Admin · AI log', 'Backend', 'Every AI call, as counts only.'),
    ('/admin/auth/user/', 'admin-users.html', 'Admin · Users', 'Backend', 'Accounts, staff flags and permissions.'),
]

# (url, file name, title, note)
API_PAGES = [
    ('/healthz/', 'api-healthz.json', 'Health check', 'Database status and book count.'),
    ('/ai/api/parse/?q=neet under 300 near madhapur', 'api-parse.json',
     'AI query parser', 'How the assistant understood a sentence.'),
    ('/ai/api/search/?q=free novels', 'api-search.json', 'AI search', 'Parsed filters and matching books.'),
    ('/ai/api/price/?category=2&condition=good', 'api-price.json', 'AI price',
     'Fair price, comparables and confidence.'),
]

RIBBON = """
<div id="bb-static-ribbon" style="position:fixed;left:0;right:0;bottom:0;z-index:99999;
     background:#0f172a;color:#fff;font:600 12.5px/1.4 'Plus Jakarta Sans',system-ui,sans-serif;
     padding:9px 14px;text-align:center;box-shadow:0 -4px 16px rgba(0,0,0,.25);">
  <i style="color:#38bdf8;">◈</i> Static preview — a saved snapshot of real BookBridge pages.
  Forms and live search need the running app.
  <a href="index.html" style="color:#7dd3fc;margin-left:8px;">All pages →</a>
</div>
"""

COVER_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BookBridge — static preview</title>
<style>
  :root {{ --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; --brand:#0284c7; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:'Plus Jakarta Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
         background:#f8fafc; color:var(--ink); }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:40px 22px 80px; }}
  header {{ background:linear-gradient(135deg,#0ea5e9,#2563eb 55%,#4338ca); color:#fff;
            border-radius:22px; padding:34px 30px; box-shadow:0 18px 40px rgba(37,99,235,.25); }}
  header h1 {{ margin:0 0 6px; font-size:2rem; letter-spacing:-.5px; }}
  header p {{ margin:0; opacity:.9; }}
  .badge {{ display:inline-block; background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.35);
            border-radius:999px; padding:5px 12px; font-size:.76rem; font-weight:800; margin-bottom:14px; }}
  h2 {{ font-size:1.05rem; text-transform:uppercase; letter-spacing:.6px; color:var(--muted);
        margin:36px 0 14px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:14px; }}
  a.card {{ display:block; background:#fff; border:1px solid var(--line); border-radius:16px;
            padding:16px 18px; text-decoration:none; color:inherit; transition:.15s; }}
  a.card:hover {{ transform:translateY(-2px); box-shadow:0 12px 26px rgba(15,23,42,.09); border-color:#bae6fd; }}
  a.card b {{ display:block; font-size:.98rem; margin-bottom:4px; }}
  a.card span {{ color:var(--muted); font-size:.82rem; line-height:1.5; }}
  .file {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.72rem;
           color:#0369a1; background:#f0f9ff; border-radius:6px; padding:2px 6px; margin-top:8px;
           display:inline-block; }}
  .note {{ background:#fffbeb; border:1px solid #fde68a; border-radius:14px; padding:16px 18px;
           color:#92400e; font-size:.86rem; line-height:1.6; margin-top:36px; }}
  .note b {{ color:#78350f; }}
  footer {{ margin-top:26px; color:var(--muted); font-size:.8rem; text-align:center; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <span class="badge">STATIC PREVIEW · no server needed</span>
    <h1>BookBridge</h1>
    <p>Buy, sell and share second-hand books nearby — with an offline AI layer.</p>
  </header>

  <h2>Frontend · {frontend_count} screens</h2>
  <div class="grid">{frontend_cards}</div>

  <h2>Backend · {backend_count} screens</h2>
  <div class="grid">{backend_cards}</div>

  <h2>API responses · {api_count} snapshots</h2>
  <div class="grid">{api_cards}</div>

  <div class="note">
    <b>ఇది ఏమిటి?</b> ఇవి నిజమైన BookBridge pages యొక్క saved HTML snapshots — అదే
    templates, అదే database data. Server అవసరం లేదు: ఏ card నైనా క్లిక్ చేయండి.<br><br>
    <b>ఏమి పనిచేయదు?</b> Forms submit అవ్వవు, live search / AI assistant API కాల్స్
    జరగవు, admin లో edit చేయలేరు — అవన్నీ running server కావాలి
    (<code>python manage.py runserver</code> లేదా deployed site).<br><br>
    <b>తాజా data కావాలంటే:</b> <code>python manage.py export_preview</code> మళ్ళీ run చేయండి.
  </div>

  <footer>Generated {generated} · {model_count} database tables · Django {django_version}</footer>
</div>
</body>
</html>
"""

CARD_TEMPLATE = ('<a class="card" href="{file}"><b>{title}</b>'
                 '<span>{note}</span><span class="file">{file}</span></a>')


class Command(BaseCommand):
    help = 'Render the app to static HTML files that open without a server.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--out', default='preview_static',
            help='Output folder (default: preview_static).',
        )
        parser.add_argument(
            '--user', default='demo',
            help='Username to preview as (default: demo). Must exist.',
        )
        parser.add_argument(
            '--zip', action='store_true',
            help='Also write a .zip next to the folder, ready to share.',
        )

    def handle(self, *args, **options):
        out_dir = Path(options['out']).expanduser().resolve()
        username = options['user']

        user = User.objects.filter(username=username).first()
        if user is None:
            raise CommandError(
                f'No user called “{username}”. Run `python manage.py seed_demo` first.'
            )

        out_dir.mkdir(parents=True, exist_ok=True)

        client = Client()
        client.force_login(user)

        first_book = Book.objects.filter(is_sold=False, is_hidden=False).order_by('-created_at').first()
        pages = list(PAGES)
        if first_book:
            pages.insert(2, (
                f'/books/{first_book.pk}/', 'book-detail.html', 'Book detail', 'Frontend',
                'Photos, seller trust, contact actions and AI recommendations.',
            ))

        # ---- render every page -------------------------------------------
        written = {}
        failures = []
        with override_settings(ALLOWED_HOSTS=['*']):
            for url, filename, *_rest in pages:
                try:
                    response = client.get(url, follow=True)
                except Exception as exc:               # pragma: no cover - defensive
                    failures.append((url, f'{exc.__class__.__name__}: {exc}'))
                    continue
                if response.status_code != 200:
                    failures.append((url, f'HTTP {response.status_code}'))
                    continue
                html = response.content.decode('utf-8', 'replace')
                (out_dir / filename).write_text(html, encoding='utf-8')
                written[url] = filename

            for url, filename, *_rest in API_PAGES:
                try:
                    response = client.get(url, follow=True)
                except Exception as exc:               # pragma: no cover
                    failures.append((url, str(exc)))
                    continue
                if response.status_code != 200:
                    failures.append((url, f'HTTP {response.status_code}'))
                    continue
                body = response.content.decode('utf-8', 'replace')
                try:                                   # pretty-print JSON for readability
                    body = json.dumps(json.loads(body), indent=2, ensure_ascii=False)
                except ValueError:
                    pass
                (out_dir / filename).write_text(body, encoding='utf-8')
                written[url] = filename

        # ---- copy static files and photos --------------------------------
        static_src = Path(settings.STATIC_ROOT) if settings.STATIC_ROOT else None
        if static_src and static_src.exists():
            shutil.copytree(str(static_src), str(out_dir / 'static'), dirs_exist_ok=True)
        media_src = Path(settings.MEDIA_ROOT)
        if media_src.exists():
            shutil.copytree(str(media_src), str(out_dir / 'media'), dirs_exist_ok=True)

        # ---- rewrite links so they work from file:// ---------------------
        mapping = {path: name for path, name in written.items()}
        ordered = sorted(mapping, key=len, reverse=True)

        def target_for(raw_path):
            path = urlparse(raw_path).path
            if not path:
                return None
            if path in mapping:
                return mapping[path]
            with_slash = path if path.endswith('/') else path + '/'
            if with_slash in mapping:
                return mapping[with_slash]
            if path.startswith('/static/'):
                return 'static/' + path[len('/static/'):]
            if path.startswith('/media/'):
                return 'media/' + path[len('/media/'):]
            # Nearest exported page sharing a prefix (e.g. /books/12/report/ → books.html)
            for candidate in ordered:
                base = urlparse(candidate).path.rstrip('/')
                if base and path.startswith(base):
                    return mapping[candidate]
            return None

        link_re = re.compile(r'\b(href|src|action)="(/[^"]*)"')

        def rewrite(match):
            attr, value = match.group(1), match.group(2)
            target = target_for(value)
            if target is None:
                return f'{attr}="#"'
            return f'{attr}="{target}"'

        for filename in list(written.values()):
            file_path = out_dir / filename
            text = file_path.read_text(encoding='utf-8')

            text = link_re.sub(rewrite, text)
            # CSS url(/static/...) and inline fetch('/ai/...') calls
            text = text.replace('url(/static/', 'url(static/')
            text = text.replace('"/static/', '"static/')
            text = text.replace('"/media/', '"media/')

            if filename.endswith('.html') and 'bb-static-ribbon' not in text:
                text = text.replace('</body>', RIBBON + '</body>', 1)

            file_path.write_text(text, encoding='utf-8')

        # ---- cover page --------------------------------------------------
        def cards(entries):
            return ''.join(
                CARD_TEMPLATE.format(file=filename, title=title, note=note)
                for filename, title, note in entries
                if filename in written.values()
            )

        frontend = [(f, t, n) for _u, f, t, _g, n in pages if _g == 'Frontend']
        backend = [(f, t, n) for _u, f, t, _g, n in pages if _g == 'Backend']
        api = [(f, t, n) for _u, f, t, n in API_PAGES]

        import django
        from django.contrib import admin as django_admin
        from django.utils import timezone

        model_count = len(django_admin.site._registry)

        cover = COVER_TEMPLATE.format(
            frontend_cards=cards(frontend),
            backend_cards=cards(backend),
            api_cards=cards(api),
            frontend_count=len([c for c in frontend if c[0] in written.values()]),
            backend_count=len([c for c in backend if c[0] in written.values()]),
            api_count=len([c for c in api if c[0] in written.values()]),
            generated=timezone.localtime().strftime('%d %b %Y, %H:%M'),
            model_count=model_count,
            django_version=django.get_version(),
        )
        # The exported index.html would shadow the home page, so the cover lives
        # at preview.html and is opened first.
        (out_dir / 'preview.html').write_text(cover, encoding='utf-8')

        if options['zip']:
            archive = out_dir.with_suffix('.zip')
            shutil.make_archive(str(archive.with_suffix('')), 'zip', root_dir=out_dir)
            self.stdout.write(self.style.SUCCESS(f'Zip written: {archive}'))

        self.stdout.write(self.style.SUCCESS(
            f'Exported {len(written)} pages to {out_dir}'
        ))
        if failures:
            self.stdout.write(self.style.WARNING(f'{len(failures)} page(s) skipped:'))
            for url, reason in failures:
                self.stdout.write(f'  {url} — {reason}')
            if any(url.startswith('/admin/') for url, _ in failures):
                self.stdout.write(self.style.WARNING(
                    'Admin pages are hidden from this account. Re-run with '
                    '`--user <superuser>` (or `python manage.py createsuperuser`) '
                    'to include them.'
                ))
        self.stdout.write('')
        self.stdout.write('Open this file in a browser (no server needed):')
        self.stdout.write(f'  {out_dir / "preview.html"}')
