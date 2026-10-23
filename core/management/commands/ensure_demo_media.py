"""Recreate demo cover images that have gone missing.

Free hosting plans give the container an ephemeral disk: every redeploy or
restart wipes ``media/``, while the database rows (and their image names) stay
in PostgreSQL. The demo listings would then point at files that no longer exist.

This command re-renders just those placeholder covers, so the seeded demo keeps
looking complete. It asks the configured storage whether the file is there, so
it works for local disk and for ``MEDIA_STORAGE=db`` (where the covers live in
the database and therefore never disappear).

Usage:
    python manage.py ensure_demo_media
"""
import tempfile
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from books.models import Book
from core.management.commands.seed_demo import BOOKS, make_cover


class Command(BaseCommand):
    help = 'Recreate missing seeded cover images (survives an ephemeral disk).'

    def handle(self, *args, **options):
        specs = {spec[0]: spec for spec in BOOKS}          # title → spec tuple
        created = 0
        missing_rows = 0

        for book in Book.objects.exclude(image='').only('id', 'title', 'image'):
            spec = specs.get(book.title)
            if spec is None:
                # A real seller's photo, not demo data — nothing we can redraw.
                continue

            filename = f"seed_{slugify(book.title)[:40]}.jpg"
            stored_name = f'book_images/{filename}'

            if not default_storage.exists(stored_name):
                with tempfile.TemporaryDirectory() as tmp:
                    target = Path(tmp) / filename
                    if make_cover(book.title, spec[1], spec[-1], target):
                        with open(target, 'rb') as handle:
                            default_storage.save(stored_name, File(handle))
                        created += 1

            expected = stored_name
            if book.image.name != expected:
                missing_rows += 1

        if created:
            self.stdout.write(self.style.SUCCESS(f'Recreated {created} demo cover image(s).'))
        else:
            self.stdout.write('All demo cover images are present.')

        if missing_rows:
            self.stdout.write(
                f'{missing_rows} listing(s) point at a different file name; '
                'their photos are left as they are.'
            )
