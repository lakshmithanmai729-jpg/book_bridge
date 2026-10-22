from django.contrib import admin

from .models import BookRequest, ChatMessage, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'telegram_username', 'contact_preference', 'account_privacy', 'location')
    list_filter = ('contact_preference', 'account_privacy')
    search_fields = ('user__username', 'name', 'telegram_username', 'phone_number', 'location')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'book', 'short_text', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__username', 'receiver__username', 'text', 'book__title')

    @admin.display(description='Message')
    def short_text(self, obj):
        return obj.text[:60]


@admin.register(BookRequest)
class BookRequestAdmin(admin.ModelAdmin):
    list_display = ('book_title', 'user', 'category', 'location', 'status', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('book_title', 'user__username', 'category', 'location', 'notes')
