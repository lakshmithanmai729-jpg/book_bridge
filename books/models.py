from django.db import models
from django.contrib.auth.models import User


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
    price = models.DecimalField(max_digits=8, decimal_places=2)
    original_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, default=0)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'book')

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"
