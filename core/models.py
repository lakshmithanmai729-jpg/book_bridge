"""Small shared models for the site itself (not the marketplace)."""
from django.db import models


class StoredFile(models.Model):
    """One uploaded file kept inside the database.

    Used by ``core.storage.DatabaseStorage`` when ``MEDIA_STORAGE=db``: a free
    host wipes its disk on every restart, but the database survives, so covers
    uploaded once stay online.
    """

    name = models.CharField(max_length=255, unique=True)
    content_type = models.CharField(max_length=120, blank=True, default='')
    size = models.PositiveIntegerField(default=0)
    data = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'stored file'
        verbose_name_plural = 'stored files'
        ordering = ('name',)

    def __str__(self):
        return f'{self.name} ({self.size} bytes)'

    @property
    def is_image(self):
        return self.content_type.startswith('image/')
