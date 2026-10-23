import os
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from books.models import Book, Category


class ProductionSeedSafetyTests(TestCase):
    """A public deploy must never contain accounts with a published password."""

    def test_demo_users_are_not_seeded_when_debug_is_off(self):
        from django.core.management import call_command
        from io import StringIO

        with override_settings(DEBUG=False):
            out = StringIO()
            call_command('seed_demo', '--if-empty', stdout=out)

        self.assertFalse(User.objects.filter(username='demo').exists())
        self.assertFalse(User.objects.filter(username='arjun').exists())
        # Categories are still created — the sell form needs them.
        self.assertTrue(Category.objects.exists())
        self.assertIn('demo accounts were NOT created', out.getvalue())

    def test_force_demo_still_works_for_a_staging_site(self):
        from django.core.management import call_command
        from io import StringIO

        with override_settings(DEBUG=False):
            call_command('seed_demo', '--if-empty', '--force-demo', stdout=StringIO())

        self.assertTrue(User.objects.filter(username='demo').exists())

    def test_local_debug_seeding_is_unchanged(self):
        from django.core.management import call_command
        from io import StringIO

        # Django forces DEBUG=False while running tests, so opt back in here.
        with override_settings(DEBUG=True):
            call_command('seed_demo', '--if-empty', stdout=StringIO())

        self.assertTrue(User.objects.filter(username='demo').exists())


class EnsureAdminTests(TestCase):
    """The owner can create their admin from Render env vars, no shell needed."""

    def test_creates_a_superuser_from_the_environment(self):
        from django.core.management import call_command
        from io import StringIO

        with mock.patch.dict('os.environ', {
            'DJANGO_SUPERUSER_USERNAME': 'owner',
            'DJANGO_SUPERUSER_EMAIL': 'owner@example.com',
            'DJANGO_SUPERUSER_PASSWORD': 'a-very-long-password-123',
        }):
            call_command('ensure_admin', stdout=StringIO())

        user = User.objects.get(username='owner')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password('a-very-long-password-123'))

    def test_is_a_no_op_when_the_variables_are_missing(self):
        from django.core.management import call_command
        from io import StringIO

        with mock.patch.dict('os.environ', {}, clear=False):
            os.environ.pop('DJANGO_SUPERUSER_USERNAME', None)
            out = StringIO()
            call_command('ensure_admin', stdout=out)

        self.assertIn('skipping admin creation', out.getvalue())

    def test_existing_admin_is_promoted_not_duplicated(self):
        from django.core.management import call_command
        from io import StringIO

        User.objects.create_user('owner', password='old-password')

        with mock.patch.dict('os.environ', {
            'DJANGO_SUPERUSER_USERNAME': 'owner',
            'DJANGO_SUPERUSER_PASSWORD': 'new-password-1234',
        }):
            call_command('ensure_admin', stdout=StringIO())

        self.assertEqual(User.objects.filter(username='owner').count(), 1)
        user = User.objects.get(username='owner')
        self.assertTrue(user.is_superuser)
        # The old password is kept unless --rotate-password is passed.
        self.assertTrue(user.check_password('old-password'))


class BackendTourTests(TestCase):
    """The tour page is the demo screen — it must be staff-only and accurate."""

    def setUp(self):
        self.staff = User.objects.create_user('staffer', password='Bridge!2345', is_staff=True)
        self.member = User.objects.create_user('member', password='Bridge!2345')
        self.category = Category.objects.create(name='NEET')
        self.book = Book.objects.create(
            seller=self.staff, title='Tour Book', author='A', price=100, category=self.category,
        )

    def test_anonymous_visitors_are_sent_to_the_admin_login(self):
        response = self.client.get(reverse('core:backend_tour'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_regular_members_cannot_open_the_tour(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse('core:backend_tour'))
        self.assertEqual(response.status_code, 302)

    def test_staff_see_every_table_with_live_counts(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('core:backend_tour'))
        self.assertEqual(response.status_code, 200)
        page = response.content.decode()

        for label in ('Book listings', 'Categories', 'User profiles', 'Chat messages',
                      'AI usage log', 'Accounts &amp; permissions'):
            self.assertIn(label, page)

        # The book we created must be counted, not hardcoded.
        self.assertEqual(response.context['model_total'], 13)
        books_group = next(g for g in response.context['tour_groups'] if g['app'] == 'books')
        self.assertEqual(books_group['total'], 2)          # 1 category + 1 book

    def test_zero_row_tables_show_zero_not_a_dash(self):
        self.client.force_login(self.staff)
        page = self.client.get(reverse('core:backend_tour')).content.decode()
        self.assertIn('<span class="bb-tour-count">0</span>', page)

    def test_tour_links_to_the_admin_changelists(self):
        self.client.force_login(self.staff)
        page = self.client.get(reverse('core:backend_tour')).content.decode()
        self.assertIn('/admin/books/book/', page)
        self.assertIn('/admin/ai_engine/aievent/', page)

    def test_staff_dashboard_links_to_the_tour(self):
        self.client.force_login(self.staff)
        page = self.client.get(reverse('core:staff_dashboard')).content.decode()
        self.assertIn(reverse('core:backend_tour'), page)


class ExportPreviewTests(TestCase):
    """`manage.py export_preview` must produce a folder that works offline."""

    def setUp(self):
        # The demo account created by `seed_demo --with-admin` is a superuser,
        # so the export can reach the admin screens.
        self.staff = User.objects.create_superuser(
            'demo', email='demo@bookbridge.local', password='Bridge!2345',
        )
        self.category = Category.objects.create(name='NEET')
        self.book = Book.objects.create(
            seller=self.staff, title='Export Book', author='A', price=150, category=self.category,
        )

    def test_export_writes_pages_and_a_cover(self):
        import tempfile
        from pathlib import Path
        from django.core.management import call_command
        from io import StringIO

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'preview'
            call_command('export_preview', '--out', str(out), stdout=StringIO())

            self.assertTrue((out / 'preview.html').exists())
            self.assertTrue((out / 'index.html').exists())
            self.assertTrue((out / 'backend-tour.html').exists())
            self.assertTrue((out / 'admin-books.html').exists())

    def test_export_rewrites_every_absolute_link(self):
        import re
        import tempfile
        from pathlib import Path
        from django.core.management import call_command
        from io import StringIO

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'preview'
            call_command('export_preview', '--out', str(out), stdout=StringIO())

            for page in out.glob('*.html'):
                html = page.read_text(encoding='utf-8')
                absolute = re.findall(r'\b(?:href|src|action)="(/[^"]*)"', html)
                self.assertEqual(absolute, [], f'{page.name} still has absolute links')

    def test_export_marks_the_pages_as_a_static_snapshot(self):
        import tempfile
        from pathlib import Path
        from django.core.management import call_command
        from io import StringIO

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'preview'
            call_command('export_preview', '--out', str(out), stdout=StringIO())
            self.assertIn('bb-static-ribbon', (out / 'index.html').read_text(encoding='utf-8'))

    def test_export_refuses_an_unknown_user(self):
        import tempfile
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CommandError):
                call_command('export_preview', '--out', tmp, '--user', 'nobody', stdout=None)


class DemoModeSeedingTests(TestCase):
    """DEMO_MODE fills a live demo without handing out working passwords."""

    def run_seed(self, *args, **kwargs):
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command('seed_demo', '--if-empty', *args, stdout=out, **kwargs)
        return out.getvalue()

    def test_demo_mode_seeds_books_without_usable_passwords(self):
        with override_settings(DEBUG=False, DEMO_MODE=True):
            output = self.run_seed()

        self.assertEqual(User.objects.filter(username__in=['demo', 'arjun', 'priya', 'rahul']).count(), 4)
        self.assertGreaterEqual(Book.objects.count(), 16)
        for user in User.objects.filter(username__in=['demo', 'arjun', 'priya', 'rahul']):
            self.assertFalse(
                user.has_usable_password(),
                f'{user.username} must not be signable-into on a public demo',
            )
            self.assertFalse(user.is_superuser)
        self.assertIn('unusable passwords', output)

    def test_demo_accounts_cannot_log_in_with_the_readme_password(self):
        with override_settings(DEBUG=False, DEMO_MODE=True):
            self.run_seed()

        response = self.client.post(reverse('accounts:login'), {
            'username': 'demo',
            'password': 'bookbridge123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_second_run_is_idempotent(self):
        with override_settings(DEBUG=False, DEMO_MODE=True):
            self.run_seed()
            books = Book.objects.count()
            output = self.run_seed()

        self.assertEqual(Book.objects.count(), books)
        self.assertIn('already present', output)

    def test_demo_mode_seeds_even_when_the_owner_already_added_a_book(self):
        owner = User.objects.create_user('owner', password='Bridge!2345')
        Book.objects.create(
            seller=owner, title='My Own Listing', author='Me', price=100,
        )

        with override_settings(DEBUG=False, DEMO_MODE=True):
            self.run_seed()

        self.assertTrue(Book.objects.filter(title='My Own Listing').exists())
        self.assertGreaterEqual(Book.objects.count(), 17)

    def test_without_demo_mode_a_live_site_still_gets_no_accounts(self):
        with override_settings(DEBUG=False, DEMO_MODE=False):
            output = self.run_seed()

        self.assertFalse(User.objects.filter(username='demo').exists())
        self.assertIn('DEMO_MODE is not set', output)

    def test_demo_passwords_flag_is_the_opt_in_for_a_staging_site(self):
        with override_settings(DEBUG=False, DEMO_MODE=False):
            self.run_seed('--demo-passwords')

        demo = User.objects.get(username='demo')
        self.assertTrue(demo.has_usable_password())
        self.assertTrue(demo.check_password('bookbridge123'))


class DatabaseStorageTests(TestCase):
    """MEDIA_STORAGE=db keeps covers in the database, across restarts."""

    DB_STORAGE = {
        'default': {'BACKEND': 'core.storage.DatabaseStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }

    def test_save_open_exists_delete_round_trip(self):
        from django.core.files.base import ContentFile
        from django.core.files.storage import storages

        with override_settings(STORAGES=self.DB_STORAGE):
            storage = storages['default']
            name = storage.save('book_images/round-trip.webp', ContentFile(b'hello-cover'))

            self.assertEqual(name, 'book_images/round-trip.webp')
            self.assertTrue(storage.exists(name))
            self.assertEqual(storage.size(name), len(b'hello-cover'))
            self.assertEqual(storage.url(name), '/media/book_images/round-trip.webp')
            with storage.open(name) as handle:
                self.assertEqual(handle.read(), b'hello-cover')

            storage.delete(name)
            self.assertFalse(storage.exists(name))

    def test_a_saved_photo_is_served_at_its_media_url(self):
        from django.core.files.base import ContentFile
        from django.core.files.storage import storages

        with override_settings(STORAGES=self.DB_STORAGE, DEBUG=False):
            storages['default'].save('book_images/served.jpg', ContentFile(b'jpeg-bytes'))
            response = self.client.get('/media/book_images/served.jpg')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'jpeg-bytes')
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertIn('max-age', response['Cache-Control'])

    def test_missing_photo_returns_404_not_a_server_error(self):
        with override_settings(STORAGES=self.DB_STORAGE):
            response = self.client.get('/media/book_images/never-saved.jpg')
        self.assertEqual(response.status_code, 404)

    def test_book_upload_lands_in_the_database(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.models import StoredFile

        seller = User.objects.create_user('seller', password='Bridge!2345')
        book = Book.objects.create(seller=seller, title='In DB', author='A', price=50)

        with override_settings(STORAGES=self.DB_STORAGE):
            book.image.save('cover.jpg', SimpleUploadedFile('cover.jpg', b'fake-jpeg'), save=True)
            self.assertTrue(
                StoredFile.objects.filter(name=book.image.name).exists(),
                'the cover should be a row, not a file on disk',
            )
            response = self.client.get(book.image.url)
            self.assertEqual(response.status_code, 200)

    def test_ensure_demo_media_recreates_missing_covers_in_the_database(self):
        from django.core.management import call_command
        from io import StringIO
        from core.models import StoredFile

        with override_settings(DEBUG=True, STORAGES=self.DB_STORAGE):
            call_command('seed_demo', '--if-empty', stdout=StringIO())
            # Simulate the free host wiping its disk: rows survive, files do not.
            StoredFile.objects.all().delete()

            out = StringIO()
            call_command('ensure_demo_media', stdout=out)

            self.assertIn('Recreated', out.getvalue())
            self.assertGreaterEqual(StoredFile.objects.count(), 16)

    def test_media_storage_setting_defaults_to_the_disk(self):
        from django.conf import settings

        self.assertIn(getattr(settings, 'MEDIA_STORAGE', 'filesystem'), ('filesystem', 'db'))


class DatabaseUrlParsingTests(TestCase):
    """A Neon connection string must keep its sslmode."""

    def test_neon_url_keeps_ssl_options_and_health_checks(self):
        from config.settings import _database_from_url

        config = _database_from_url(
            'postgresql://bookbridge:p%40ss@ep-cool-123-pooler.ap-southeast-1.aws.neon.tech'
            '/neondb?sslmode=require&channel_binding=require'
        )

        self.assertEqual(config['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(config['PASSWORD'], 'p@ss')
        self.assertEqual(config['NAME'], 'neondb')
        self.assertEqual(config['HOST'], 'ep-cool-123-pooler.ap-southeast-1.aws.neon.tech')
        self.assertEqual(config['OPTIONS']['sslmode'], 'require')
        self.assertEqual(config['OPTIONS']['channel_binding'], 'require')
        self.assertTrue(config['CONN_HEALTH_CHECKS'])

    def test_url_without_options_still_works(self):
        from config.settings import _database_from_url

        config = _database_from_url('postgres://user:pass@db.example.com:5432/books')

        self.assertEqual(config['PORT'], '5432')
        self.assertNotIn('OPTIONS', config)

    def test_db_status_reports_the_connection_without_leaking_secrets(self):
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command('db_status', stdout=out)
        text = out.getvalue()

        self.assertIn('Database', text)
        self.assertIn('connected', text)
        self.assertIn('Uploaded photos', text)
        self.assertNotIn('PASSWORD', text)
