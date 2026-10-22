import os
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

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
