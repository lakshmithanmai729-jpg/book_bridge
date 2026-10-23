"""Print what the deployed site is really connected to.

Debugging a deploy is much faster when the logs answer three questions in one
place: which database am I talking to, am I allowed to write to it, and where
are uploaded photos going?

Run it from the Render start command (it is cheap), or any time with:

    python manage.py db_status

It never prints a password.
"""
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Show the database, media storage and demo-mode status of this deployment.'

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        engine = db.get('ENGINE', '').rsplit('.', 1)[-1]
        host = db.get('HOST') or 'local file'
        options = db.get('OPTIONS') or {}
        sslmode = options.get('sslmode', 'default')

        self.stdout.write('Database')
        self.stdout.write(f'  engine   : {engine}')
        self.stdout.write(f'  host     : {host}')
        self.stdout.write(f'  name     : {db.get("NAME")}')
        self.stdout.write(f'  sslmode  : {sslmode}')

        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
            if hasattr(connection, 'get_server_info'):
                detail = f' (server {connection.get_server_info()})'
            else:
                detail = f' (SQLite {connection.Database.sqlite_version})' if engine == 'sqlite3' else ''
            self.stdout.write(self.style.SUCCESS(f'  status   : connected{detail}'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'  status   : FAILED — {exc.__class__.__name__}: {exc}'))
            return

        from accounts.models import ChatMessage
        from books.models import Book
        from core.models import StoredFile

        self.stdout.write('Content')
        self.stdout.write(f'  books    : {Book.objects.count()}')
        self.stdout.write(f'  chats    : {ChatMessage.objects.count()}')
        self.stdout.write(f'  files    : {StoredFile.objects.count()} stored in the database')

        backend = default_storage.__class__.__name__
        self.stdout.write('Uploaded photos')
        self.stdout.write(f'  storage  : {backend}')
        if backend == 'DatabaseStorage':
            self.stdout.write(
                self.style.SUCCESS(
                    '  survives : yes — photos are rows in the database, so a '
                    'restart or redeploy keeps them.'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    '  survives : only until the next restart. Set MEDIA_STORAGE=db '
                    'on a free plan, or point this at S3.'
                )
            )

        self.stdout.write('Modes')
        self.stdout.write(f'  DEBUG    : {settings.DEBUG}')
        self.stdout.write(f'  DEMO_MODE: {getattr(settings, "DEMO_MODE", False)}')

        if not settings.DEBUG:
            backend_name = settings.EMAIL_BACKEND
            if any(mark in backend_name.lower() for mark in ('console', 'dummy', 'locmem')):
                self.stdout.write(self.style.WARNING(
                    '  email    : messages go to these logs only — password reset '
                    'will not deliver. See DEPLOY.md for Gmail SMTP.'
                ))
            else:
                self.stdout.write('  email    : SMTP configured')
