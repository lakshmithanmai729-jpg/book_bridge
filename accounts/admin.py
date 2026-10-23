from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string

from .models import (
    BookRequest, ChatMessage, Notification, SellerReview, UserBlock, UserProfile,
)


# The built-in User screen, plus one action that exists because a free deploy
# has no working email: when somebody forgets their password the owner can set
# a readable one and pass it on.
admin.site.unregister(User)


@admin.register(User)
class BookBridgeUserAdmin(BaseUserAdmin):
    actions = ('set_temporary_password',)

    @admin.action(description='Set a temporary password (shown to you — share it with the member)')
    def set_temporary_password(self, request, queryset):
        lines = []
        for user in queryset:
            temporary = f'BookBridge-{get_random_string(6, "0123456789")}'
            user.set_password(temporary)
            user.save(update_fields=['password'])
            lines.append(f'{user.username} → {temporary}')

        self.message_user(
            request,
            'Temporary passwords set. Share each one privately — the member can '
            'change it after signing in: ' + '; '.join(lines),
        )


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


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'kind', 'title', 'is_read', 'created_at')
    list_filter = ('kind', 'is_read', 'created_at')
    search_fields = ('recipient__username', 'title', 'body')
    date_hierarchy = 'created_at'
    raw_id_fields = ('recipient', 'actor', 'book')
    readonly_fields = ('created_at',)
