from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]

    CONTACT_TELEGRAM = 'telegram'
    CONTACT_IN_APP = 'in_app'
    CONTACT_WHATSAPP = 'whatsapp'
    CONTACT_CHOICES = [
        (CONTACT_TELEGRAM, 'Telegram (Recommended - No phone shared)'),
        (CONTACT_IN_APP, 'In-App Chat'),
        (CONTACT_WHATSAPP, 'WhatsApp / Call'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    name = models.CharField(max_length=150, blank=True, default='')
    phone_number = models.CharField(max_length=20, blank=True, default='')
    location = models.CharField(max_length=255, blank=True, default='')
    account_privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='private')
    telegram_username = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Telegram handle (with or without the leading @).',
    )
    contact_preference = models.CharField(
        max_length=10,
        choices=CONTACT_CHOICES,
        default=CONTACT_IN_APP,
        help_text='How buyers are allowed to reach you.',
    )
    email_verified = models.BooleanField(
        default=False,
        help_text='Set automatically when the user confirms their email address.',
    )

    def __str__(self):
        return f"{self.user.username} Profile"

    @property
    def telegram_handle(self):
        """Return the Telegram handle without a leading @ (empty string if unset)."""
        return (self.telegram_username or '').strip().lstrip('@').replace(' ', '')

    @property
    def telegram_url(self):
        handle = self.telegram_handle
        return f"https://t.me/{handle}" if handle else ''

    @property
    def prefers_telegram(self):
        return self.contact_preference == self.CONTACT_TELEGRAM

    @property
    def prefers_in_app(self):
        return self.contact_preference == self.CONTACT_IN_APP

    @property
    def prefers_whatsapp(self):
        return self.contact_preference == self.CONTACT_WHATSAPP

    @property
    def contact_label(self):
        return self.get_contact_preference_display()

    @property
    def contact_short_label(self):
        return {
            self.CONTACT_TELEGRAM: 'Telegram',
            self.CONTACT_IN_APP: 'In-App Chat',
            self.CONTACT_WHATSAPP: 'WhatsApp / Call',
        }.get(self.contact_preference, 'In-App Chat')

    # ---------- trust & safety ----------

    @property
    def is_verified(self):
        """Email confirmed → the green verified badge."""
        return bool(self.email_verified)

    @property
    def rating_summary(self):
        return SellerReview.summary_for(self.user)

    @property
    def rating_average(self):
        return self.rating_summary['average']

    @property
    def rating_count(self):
        return self.rating_summary['count']

    @property
    def is_top_seller(self):
        summary = self.rating_summary
        return summary['count'] >= 3 and summary['average'] >= 4.5

    @property
    def trust_badge(self):
        """Short label shown next to the seller's name."""
        if self.is_top_seller:
            return 'Top seller'
        if self.is_verified:
            return 'Verified'
        return ''


class ChatMessage(models.Model):
    """A single in-app chat message between a buyer and a seller."""

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    book = models.ForeignKey(
        'books.Book',
        on_delete=models.CASCADE,
        related_name='chat_messages',
        null=True,
        blank=True,
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username}: {self.text[:40]}"


class BookRequest(models.Model):
    """A student's request for a book they could not find nearby."""

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('fulfilled', 'Fulfilled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='book_requests')
    book_title = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True, default='')
    location = models.CharField(max_length=255, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.book_title} ({self.user.username})"


class SellerReview(models.Model):
    """A buyer's rating of a seller after they chatted about a book.

    Only people who actually talked to the seller can review them, which keeps
    ratings meaningful.  Reviews can be hidden by moderators without being
    deleted, and hidden reviews never count towards the average.
    """

    RATING_CHOICES = [
        (1, '1 star'),
        (2, '2 stars'),
        (3, '3 stars'),
        (4, '4 stars'),
        (5, '5 stars'),
    ]

    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_written')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    book = models.ForeignKey(
        'books.Book',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
    )
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, default=5)
    comment = models.TextField(blank=True, default='')
    is_hidden = models.BooleanField(
        default=False,
        help_text='Hidden by moderators. Hidden reviews are not shown and do not count.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('reviewer', 'seller', 'book')
        indexes = [models.Index(fields=['seller', 'is_hidden'])]

    def __str__(self):
        return f'{self.reviewer.username} → {self.seller.username}: {self.rating}★'

    def save(self, *args, **kwargs):
        # Never store a rating outside 1–5, whatever the form posts.
        try:
            value = int(self.rating)
        except (TypeError, ValueError):
            value = 5
        self.rating = max(1, min(5, value))
        return super().save(*args, **kwargs)

    @property
    def filled_stars(self):
        return range(self.rating)

    @property
    def empty_stars(self):
        return range(5 - self.rating)

    @classmethod
    def summary_for(cls, seller):
        """Return {'average': 4.6, 'count': 12} for a seller's visible reviews."""
        from django.core.cache import cache

        cache_key = f'review-summary:{seller.pk}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        reviews = cls.objects.filter(seller=seller, is_hidden=False)
        count = reviews.count()
        average = round(reviews.aggregate(avg=Avg('rating'))['avg'] or 0, 1) if count else 0
        summary = {'average': average, 'count': count}
        cache.set(cache_key, summary, 300)
        return summary

    @classmethod
    def invalidate_summary(cls, seller_id):
        from django.core.cache import cache

        cache.delete(f'review-summary:{seller_id}')

    @classmethod
    def has_chatted_with(cls, reviewer, seller):
        """A review is only allowed after a real conversation."""
        return ChatMessage.objects.filter(
            models.Q(sender=reviewer, receiver=seller)
            | models.Q(sender=seller, receiver=reviewer)
        ).exists()


class Notification(models.Model):
    """An in-app notification for one member (price drops, matches, reviews…)."""

    KIND_PRICE_DROP = 'price_drop'
    KIND_BACK_ON_SALE = 'back_on_sale'
    KIND_REQUEST_MATCH = 'request_match'
    KIND_REVIEW = 'review'
    KIND_SYSTEM = 'system'
    KIND_CHOICES = [
        (KIND_PRICE_DROP, 'Price drop'),
        (KIND_BACK_ON_SALE, 'Back on sale'),
        (KIND_REQUEST_MATCH, 'Book you wanted'),
        (KIND_REVIEW, 'New review'),
        (KIND_SYSTEM, 'BookBridge'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications_sent'
    )
    book = models.ForeignKey(
        'books.Book', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='notifications',
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_SYSTEM)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, default='')
    url = models.CharField(max_length=500, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'is_read'])]

    def __str__(self):
        return f'{self.kind} → {self.recipient.username}: {self.title[:40]}'

    @property
    def icon(self):
        return {
            self.KIND_PRICE_DROP: 'bi-tags-fill',
            self.KIND_BACK_ON_SALE: 'bi-arrow-repeat',
            self.KIND_REQUEST_MATCH: 'bi-search-heart-fill',
            self.KIND_REVIEW: 'bi-star-fill',
        }.get(self.kind, 'bi-bell-fill')

    @property
    def color(self):
        return {
            self.KIND_PRICE_DROP: '#047857',
            self.KIND_BACK_ON_SALE: '#0284c7',
            self.KIND_REQUEST_MATCH: '#7c3aed',
            self.KIND_REVIEW: '#f59e0b',
        }.get(self.kind, '#0284c7')

    @classmethod
    def unread_count(cls, user):
        if not user or not getattr(user, 'is_authenticated', False):
            return 0
        return cls.objects.filter(recipient=user, is_read=False).count()


class UserBlock(models.Model):
    """One user hiding another user's listings and chats."""

    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_made')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.blocker.username} blocked {self.blocked.username}'

    @classmethod
    def blocked_ids_for(cls, user):
        """Every user id hidden from ``user`` (blocked by them or blocking them)."""
        if not user or not getattr(user, 'is_authenticated', False):
            return set()
        made = cls.objects.filter(blocker=user).values_list('blocked_id', flat=True)
        received = cls.objects.filter(blocked=user).values_list('blocker_id', flat=True)
        return set(made) | set(received)

    @classmethod
    def exists_between(cls, first, second):
        if not first or not second or first == second:
            return False
        return cls.objects.filter(
            models.Q(blocker=first, blocked=second) | models.Q(blocker=second, blocked=first)
        ).exists()

    @classmethod
    def is_blocked_by_me(cls, me, other):
        if not me or not getattr(me, 'is_authenticated', False):
            return False
        return cls.objects.filter(blocker=me, blocked=other).exists()


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance, name=instance.username)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            UserProfile.objects.create(user=instance, name=instance.username)
