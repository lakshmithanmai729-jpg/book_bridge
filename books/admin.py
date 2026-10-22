from django.contrib import admin, messages
from django.utils import timezone

from .models import Book, BookImage, Category, Report, Wishlist


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


class BookImageInline(admin.TabularInline):
    model = BookImage
    extra = 0


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'author', 'price', 'condition', 'location_city', 'location_area',
        'pincode', 'seller', 'is_sold', 'is_hidden', 'views_count', 'created_at',
    )
    list_filter = ('condition', 'is_sold', 'is_hidden', 'category', 'location_city', 'pincode')
    search_fields = ('title', 'author', 'seller__username', 'location_city', 'location_area', 'pincode')
    inlines = [BookImageInline]
    actions = ['mark_sold', 'mark_available', 'hide_listings', 'unhide_listings']
    date_hierarchy = 'created_at'

    @admin.action(description='Mark selected listings as sold')
    def mark_sold(self, request, queryset):
        updated = queryset.update(is_sold=True, sold_at=timezone.now())
        self.message_user(request, f'{updated} listing(s) marked as sold.', messages.SUCCESS)

    @admin.action(description='Put selected listings back on sale')
    def mark_available(self, request, queryset):
        updated = queryset.update(is_sold=False, sold_at=None)
        self.message_user(request, f'{updated} listing(s) back on sale.', messages.SUCCESS)

    @admin.action(description='Hide selected listings from the marketplace')
    def hide_listings(self, request, queryset):
        updated = queryset.update(is_hidden=True)
        self.message_user(request, f'{updated} listing(s) hidden.', messages.WARNING)

    @admin.action(description='Unhide selected listings')
    def unhide_listings(self, request, queryset):
        updated = queryset.update(is_hidden=False)
        self.message_user(request, f'{updated} listing(s) visible again.', messages.SUCCESS)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'book', 'reason', 'reporter', 'status', 'created_at', 'reviewed_at')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('book__title', 'reporter__username', 'details')
    readonly_fields = ('book', 'reporter', 'reason', 'details', 'created_at', 'reviewed_at', 'reviewed_by')
    date_hierarchy = 'created_at'
    actions = ['action_hide_listing', 'action_dismiss', 'action_mark_reviewed']

    @admin.action(description='Hide the reported listing and close the report')
    def action_hide_listing(self, request, queryset):
        count = 0
        for report in queryset.select_related('book'):
            report.book.is_hidden = True
            report.book.save(update_fields=['is_hidden'])
            report.resolve(Report.STATUS_ACTIONED, reviewer=request.user)
            count += 1
        self.message_user(request, f'{count} listing(s) hidden and reports closed.', messages.WARNING)

    @admin.action(description='Dismiss the selected reports')
    def action_dismiss(self, request, queryset):
        count = 0
        for report in queryset:
            report.resolve(Report.STATUS_DISMISSED, reviewer=request.user)
            count += 1
        self.message_user(request, f'{count} report(s) dismissed.', messages.SUCCESS)

    @admin.action(description='Mark the selected reports as reviewed')
    def action_mark_reviewed(self, request, queryset):
        count = 0
        for report in queryset:
            report.resolve(Report.STATUS_REVIEWED, reviewer=request.user)
            count += 1
        self.message_user(request, f'{count} report(s) marked as reviewed.', messages.SUCCESS)


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'book', 'added_at')
    search_fields = ('user__username', 'book__title')
