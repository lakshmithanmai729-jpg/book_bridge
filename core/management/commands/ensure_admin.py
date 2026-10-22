"""Create (or update) the site owner's admin account from environment variables.

Render's free plan does not always give you a shell, so instead of asking the
owner to run ``createsuperuser`` interactively, this command reads:

    DJANGO_SUPERUSER_USERNAME   (required to do anything)
    DJANGO_SUPERUSER_EMAIL      (optional)
    DJANGO_SUPERUSER_PASSWORD   (required to create a new account)

and makes sure that account exists, is active, is staff and is a superuser.
When the variables are missing it silently does nothing, which makes it safe to
run on every deploy.

Usage:
    python manage.py ensure_admin
"""
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create or update a superuser from DJANGO_SUPERUSER_* environment variables.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username', default=os.environ.get('DJANGO_SUPERUSER_USERNAME', ''),
            help='Admin username (defaults to DJANGO_SUPERUSER_USERNAME).',
        )
        parser.add_argument(
            '--email', default=os.environ.get('DJANGO_SUPERUSER_EMAIL', ''),
            help='Admin email (defaults to DJANGO_SUPERUSER_EMAIL).',
        )
        parser.add_argument(
            '--password', default=os.environ.get('DJANGO_SUPERUSER_PASSWORD', ''),
            help='Admin password (defaults to DJANGO_SUPERUSER_PASSWORD).',
        )
        parser.add_argument(
            '--rotate-password',
            action='store_true',
            help='Reset the password of an existing admin to the one supplied.',
        )

    def handle(self, *args, **options):
        username = (options['username'] or '').strip()
        email = (options['email'] or '').strip()
        password = options['password'] or ''

        if not username:
            self.stdout.write(
                'DJANGO_SUPERUSER_USERNAME is not set — skipping admin creation.'
            )
            return

        user = User.objects.filter(username=username).first()

        if user is None:
            if not password:
                self.stderr.write(
                    'DJANGO_SUPERUSER_PASSWORD is required to create the admin account.'
                )
                return
            user = User.objects.create_superuser(
                username=username,
                email=email or f'{username}@bookbridge.local',
                password=password,
            )
            self.stdout.write(self.style.SUCCESS(f'Created superuser “{username}”.'))
            return

        changed = []
        if not user.is_staff:
            user.is_staff = True
            changed.append('is_staff')
        if not user.is_superuser:
            user.is_superuser = True
            changed.append('is_superuser')
        if not user.is_active:
            user.is_active = True
            changed.append('is_active')
        if email and user.email != email:
            user.email = email
            changed.append('email')
        if options['rotate_password'] and password:
            user.set_password(password)
            changed.append('password')

        if changed:
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f'Updated superuser “{username}” ({", ".join(changed)}).'
            ))
        else:
            self.stdout.write(f'Superuser “{username}” is already set up.')
