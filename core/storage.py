"""File storage that keeps uploaded photos inside the database.

Free hosting plans hand you an ephemeral disk: every restart, redeploy or
wake-up from sleep wipes ``media/``. The database rows survive, so a book keeps
pointing at a cover that no longer exists and the site shows placeholders.

On a paid plan you would point this at S3 or Cloudinary. On the free plan the
database is the only thing that actually persists — and at this size (16 seeded
covers plus whatever a demo visitor uploads, each a few dozen KB of WebP) it is
a perfectly good place to keep them.

Switch it on with::

    MEDIA_STORAGE=db

Nothing else changes: ``default_storage`` is used throughout the project, so
templates, the thumbnail filter and the admin all keep working, and files keep
their ``/media/...`` URLs.
"""
import mimetypes
import posixpath
from datetime import timezone as dj_timezone

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseStorage(Storage):
    """Store files as rows in ``core.StoredFile``."""

    def __init__(self, location='', base_url=None):
        self.location = location
        self.base_url = base_url

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _model():
        # Imported lazily: settings is imported long before the app registry
        # is ready, and this class is named there.
        from core.models import StoredFile

        return StoredFile

    def _normalise(self, name):
        name = str(name).replace('\\', '/').strip('/')
        # Never let ".." climb out of the media namespace, even though the
        # lookup below is an exact match and cannot leak another file.
        return posixpath.normpath(name) if '..' in name else name

    # -- Storage API -----------------------------------------------------
    def _open(self, name, mode='rb'):
        row = self._model().objects.get(name=self._normalise(name))
        return ContentFile(bytes(row.data), name=row.name)

    def _save(self, name, content):
        name = self._normalise(name)
        content.open(mode='rb') if hasattr(content, 'open') else None
        try:
            content.seek(0)
        except Exception:
            pass
        data = content.read()
        if isinstance(data, str):
            data = data.encode()

        content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        self._model().objects.update_or_create(
            name=name,
            defaults={'data': data, 'size': len(data), 'content_type': content_type},
        )
        return name

    def exists(self, name):
        return self._model().objects.filter(name=self._normalise(name)).exists()

    def delete(self, name):
        self._model().objects.filter(name=self._normalise(name)).delete()

    def size(self, name):
        row = self._model().objects.filter(name=self._normalise(name)).values_list(
            'size', flat=True
        ).first()
        if row is None:
            raise FileNotFoundError(name)
        return row

    def url(self, name):
        if self.base_url:
            return self.base_url + name
        from django.conf import settings

        return f'{settings.MEDIA_URL}{self._normalise(name)}'

    def listdir(self, path):
        path = self._normalise(path)
        prefix = f'{path}/' if path else ''
        names = self._model().objects.filter(name__startswith=prefix).values_list(
            'name', flat=True
        )

        directories, files = set(), []
        for name in names:
            remainder = name[len(prefix):]
            if '/' in remainder:
                directories.add(remainder.split('/', 1)[0])
            else:
                files.append(remainder)
        return sorted(directories), sorted(files)

    def get_created_time(self, name):
        row = self._model().objects.filter(name=self._normalise(name)).first()
        if row is None:
            raise FileNotFoundError(name)
        return row.created_at

    def get_modified_time(self, name):
        return self.get_created_time(name).astimezone(dj_timezone.utc)

    def get_accessed_time(self, name):
        return self.get_modified_time(name)

    def path(self, name):  # pragma: no cover - only used by code that needs a real file
        raise NotImplementedError(
            'Photos are stored in the database, so there is no filesystem path. '
            'Use storage.open(name) instead.'
        )
