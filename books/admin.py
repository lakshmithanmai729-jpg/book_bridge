from django.contrib import admin
from .models import Category, Book, Wishlist


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'price', 'condition', 'location_city', 'location_area', 'pincode', 'contact_phone', 'seller', 'is_sold', 'created_at')
    list_filter = ('condition', 'is_sold', 'category', 'location_city', 'pincode')
    search_fields = ('title', 'author', 'seller__username', 'location_city', 'location_area', 'pincode')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'book', 'added_at')
    search_fields = ('user__username', 'book__title')
