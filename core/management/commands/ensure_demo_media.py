"""Recreate demo cover images that have gone missing.

Free hosting plans give the container an ephemeral disk: every redeploy or
restart wipes `media/`, while the database rows (and their image names) stay in
PostgreSQL. The demo listings would then point at files that no longer exist.

This command re-renders just those placeholder covers, so the seeded demo keeps
looking complete. It is idempotent and skips anything already on disk, so it is
safe to run on every deploy.

Usage:
    python manage.py ensure_demo_media
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from books.models import Book
from core.management.commands.seed_demo import BOOKS, make_cover


class Command(BaseCommand):
    help = 'Recreate missing seeded cover images (survives an ephemeral disk).'

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT) / 'book_images'
        media_root.mkdir(parents=True, exist_ok=True)

        specs = {spec[0]: spec for spec in BOOKS}          # title → spec tuple
        created = 0
        missing_rows = 0

        for book in Book.objects.exclude(image='').only('id', 'title', 'image'):
            spec = specs.get(book.title)
            if spec is None:
                # A real seller's photo, not demo data — nothing we can redraw.
                continue

            filename = f"seed_{__import__('django').utils.text.slugify(book.title)[:40]}.jpg"
            target = media_root / filename
            if target.exists():
                continue

            *_, colors = spec
            if make_cover(book.title, spec[1], colors, target):
                created += 1

            expected = f'book_images/{filename}'
            if book.image.name != expected:
                missing_rows += 1

        if created:
            self.stdout.write(self.style.SUCCESS(f'Recreated {created} demo cover image(s).'))
        else:
            self.stdout.write('All demo cover images are present.')
