from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

# The price is a DecimalField(max_digits=8, decimal_places=2), so this is the
# largest value the column can hold. Anything above it breaks every page that
# renders the book, so it must never reach the database.
PRICE_MAX = 999999.99


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class Book(models.Model):
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('like_new', 'Like New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ]

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='books')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(PRICE_MAX)],
    )
    original_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(PRICE_MAX)],
    )
    is_negotiable = models.BooleanField(default=True)
    listing_type = models.CharField(max_length=10, choices=[('single', 'Single Book'), ('set', 'Full Set')], default='single')
    is_donation = models.BooleanField(default=False)
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES, default='good')
    image = models.ImageField(upload_to='book_images/', blank=True, null=True)
    location_city = models.CharField(max_length=100, blank=True, default='', help_text="City or Town (e.g. Hyderabad)")
    location_area = models.CharField(max_length=100, blank=True, default='', help_text="Area, Locality or College (e.g. Madhapur, JNTU)")
    pincode = models.CharField(max_length=10, blank=True, default='', help_text="6-digit Pincode")
    contact_phone = models.CharField(max_length=15, blank=True, default='', help_text="Phone / WhatsApp number for local buyer contact")
    is_sold = models.BooleanField(default=False)
    sold_at = models.DateTimeField(null=True, blank=True)
    is_hidden = models.BooleanField(
        default=False,
        help_text='Hidden by moderators after a report. Only the seller can still see it.',
    )
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # Belt and braces: SQLite does not enforce max_digits, so a single
            # oversized price used to poison the whole marketplace with 500s.
            models.CheckConstraint(
                condition=Q(price__gte=0, price__lte=PRICE_MAX),
                name='book_price_within_range',
            ),
        ]
        indexes = [
            models.Index(fields=['is_sold', 'is_hidden', '-created_at']),
            models.Index(fields=['location_city']),
            models.Index(fields=['seller', '-created_at']),
        ]

    @property
    def is_available(self):
        return not self.is_sold and not self.is_hidden

    @property
    def status_label(self):
        if self.is_sold:
            return 'Sold'
        if self.is_hidden:
            return 'Hidden'
        return 'Available'

    @property
    def status_class(self):
        if self.is_sold:
            return 'red'
        if self.is_hidden:
            return 'amber'
        return 'green'

    def mark_sold(self, sold=True):
        self.is_sold = sold
        self.sold_at = timezone.now() if sold else None
        self.save(update_fields=['is_sold', 'sold_at', 'updated_at'])

    def get_absolute_url(self):
        return reverse('books:book_detail', args=[self.pk])


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'book')

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"


class BookImage(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='book_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.book.title} image"


Book.gallery_images = property(lambda self: self.images.all().order_by('uploaded_at'))


class Report(models.Model):
    """A buyer/seller report about a listing, reviewed by moderators."""

    REASON_CHOICES = [
        ('fake', 'Fake or misleading listing'),
        ('wrong_price', 'Wrong price or already sold'),
        ('prohibited', 'Prohibited or inappropriate item'),
        ('spam', 'Spam / duplicate listing'),
        ('offensive', 'Offensive content or photos'),
        ('scam', 'Trying to scam buyers'),
        ('other', 'Something else'),
    ]

    STATUS_OPEN = 'open'
    STATUS_REVIEWED = 'reviewed'
    STATUS_ACTIONED = 'actioned'
    STATUS_DISMISSED = 'dismissed'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_REVIEWED, 'Reviewed'),
        (STATUS_ACTIONED, 'Actioned'),
        (STATUS_DISMISSED, 'Dismissed'),
    ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports_made'
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default='other')
    details = models.TextField(blank=True, default='')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_OPEN)
    admin_note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports_reviewed'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', '-created_at'])]

    def __str__(self):
        return f"Report #{self.pk} · {self.book.title} · {self.get_reason_display()}"

    @property
    def is_open(self):
        return self.status == self.STATUS_OPEN

    def resolve(self, status, reviewer=None, note=''):
        self.status = status
        self.admin_note = note or self.admin_note
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=['status', 'admin_note', 'reviewed_by', 'reviewed_at'])
