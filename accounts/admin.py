from django.contrib import admin

from .models import BookRequest, ChatMessage, SellerReview, UserBlock, UserProfile


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


@admin.register(SellerReview)
class SellerReviewAdmin(admin.ModelAdmin):
    list_display = ('seller', 'reviewer', 'rating', 'short_comment', 'book', 'is_hidden', 'created_at')
    list_filter = ('rating', 'is_hidden', 'created_at')
    search_fields = ('seller__username', 'reviewer__username', 'comment', 'book__title')
    raw_id_fields = ('seller', 'reviewer', 'book')
    actions = ('hide_reviews', 'unhide_reviews')

    @admin.display(description='Comment')
    def short_comment(self, obj):
        return (obj.comment or '—')[:60]

    @admin.action(description='Hide selected reviews (they stop counting)')
    def hide_reviews(self, request, queryset):
        updated = queryset.update(is_hidden=True)
        for seller_id in set(queryset.values_list('seller_id', flat=True)):
            SellerReview.invalidate_summary(seller_id)
        self.message_user(request, f'{updated} review(s) hidden.')

    @admin.action(description='Unhide selected reviews')
    def unhide_reviews(self, request, queryset):
        updated = queryset.update(is_hidden=False)
        for seller_id in set(queryset.values_list('seller_id', flat=True)):
            SellerReview.invalidate_summary(seller_id)
        self.message_user(request, f'{updated} review(s) visible again.')


@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    search_fields = ('blocker__username', 'blocked__username')
    raw_id_fields = ('blocker', 'blocked')
