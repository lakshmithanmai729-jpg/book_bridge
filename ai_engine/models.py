from django.conf import settings
from django.db import models


class AIEvent(models.Model):
    """One use of an AI feature.

    We log feature usage (never raw personal data) so the team can see what is
    actually being used, how often suggestions are accepted, and whether the
    assistant is answering real queries.
    """

    KIND_PRICE = 'price'
    KIND_DESCRIBE = 'describe'
    KIND_CLASSIFY = 'classify'
    KIND_SEARCH = 'search'
    KIND_RISK = 'risk'
    KIND_CHOICES = [
        (KIND_PRICE, 'Price suggestion'),
        (KIND_DESCRIBE, 'Description draft'),
        (KIND_CLASSIFY, 'Category guess'),
        (KIND_SEARCH, 'AI search'),
        (KIND_RISK, 'Risk check'),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ai_events',
    )
    book = models.ForeignKey(
        'books.Book',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ai_events',
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['kind', '-created_at'])]

    def __str__(self):
        return f'{self.get_kind_display()} @ {self.created_at:%d %b %H:%M}'
