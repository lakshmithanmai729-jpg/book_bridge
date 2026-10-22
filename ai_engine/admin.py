from django.contrib import admin

from .models import AIEvent


@admin.register(AIEvent)
class AIEventAdmin(admin.ModelAdmin):
    """Read-only: these rows are an audit trail, not something to edit."""

    list_display = ('kind', 'user', 'book', 'short_payload', 'created_at')
    list_filter = ('kind', 'created_at')
    search_fields = ('user__username', 'book__title')
    date_hierarchy = 'created_at'
    raw_id_fields = ('user', 'book')
    readonly_fields = ('kind', 'user', 'book', 'payload', 'created_at')

    @admin.display(description='Payload')
    def short_payload(self, obj):
        if not obj.payload:
            return '—'
        text = ', '.join(f'{key}={value}' for key, value in obj.payload.items())
        return text[:60]

    def has_add_permission(self, request):
        return False
