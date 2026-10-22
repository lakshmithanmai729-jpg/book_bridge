from django.db import models
from django.contrib.auth.models import User
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


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance, name=instance.username)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            UserProfile.objects.create(user=instance, name=instance.username)
