from django.contrib import admin
from .models import Reservation, Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount', 'status', 'payment_date', 'payment_method', 'created_at')
    list_filter = ('status', 'payment_date', 'created_at')
    search_fields = ('transaction_id', 'payment_method')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Payment Details', {
            'fields': ('amount', 'status', 'payment_date', 'payment_method', 'transaction_id')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_completed', 'mark_as_failed', 'refund_payments']

    def mark_as_completed(self, request, queryset):
        for payment in queryset.filter(status='pending'):
            payment.mark_as_completed()
        self.message_user(request, f"{queryset.filter(status='completed').count()} payments were marked as completed.")
    mark_as_completed.short_description = "Mark selected payments as completed"

    def mark_as_failed(self, request, queryset):
        for payment in queryset.filter(status='pending'):
            payment.mark_as_failed()
        self.message_user(request, f"{queryset.filter(status='failed').count()} payments were marked as failed.")
    mark_as_failed.short_description = "Mark selected payments as failed"

    def refund_payments(self, request, queryset):
        refunded_count = 0
        for payment in queryset.filter(status='completed'):
            if payment.refund():
                refunded_count += 1
        self.message_user(request, f"{refunded_count} payments were refunded.")
    refund_payments.short_description = "Refund selected payments"

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('user', 'parking_spot', 'start_time', 'end_time', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'parking_spot__name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Parking Information', {
            'fields': ('parking_spot',)
        }),
        ('Reservation Details', {
            'fields': ('start_time', 'end_time', 'status')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_reservations', 'complete_reservations', 'cancel_reservations']

    def activate_reservations(self, request, queryset):
        for reservation in queryset.filter(status='pending'):
            reservation.activate()
        self.message_user(request, f"{queryset.filter(status='active').count()} reservations were activated.")
    activate_reservations.short_description = "Activate selected reservations"

    def complete_reservations(self, request, queryset):
        for reservation in queryset.filter(status='active'):
            reservation.complete()
        self.message_user(request, f"{queryset.filter(status='completed').count()} reservations were completed.")
    complete_reservations.short_description = "Complete selected reservations"

    def cancel_reservations(self, request, queryset):
        for reservation in queryset.filter(status__in=['pending', 'active']):
            reservation.cancel()
        self.message_user(request, f"{queryset.filter(status='cancelled').count()} reservations were cancelled.")
    cancel_reservations.short_description = "Cancel selected reservations"
