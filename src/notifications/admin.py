from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'status', 'created_at', 'read_at')
    list_filter = ('type', 'status', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('created_at', 'read_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'type', 'title', 'message', 'status', 'reservation_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'read_at'),
            'classes': ('collapse',),
        }),
    )