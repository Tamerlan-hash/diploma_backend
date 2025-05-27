from django.contrib import admin
from .models import PaymentMethod, Transaction, Wallet

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'masked_card_number', 'cardholder_name', 'is_default', 'created_at')
    list_filter = ('type', 'is_default', 'created_at')
    search_fields = ('user__username', 'cardholder_name')
    readonly_fields = ('created_at', 'updated_at')
    
    def masked_card_number(self, obj):
        return f"**** **** **** {obj.card_number[-4:]}"
    masked_card_number.short_description = 'Card Number'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('user__username', 'transaction_id', 'reservation_id')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'wallet', 'payment_method')
        }),
        ('Transaction Details', {
            'fields': ('transaction_type', 'amount', 'status', 'reservation_id', 'description')
        }),
        ('Payment Information', {
            'fields': ('transaction_id',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_completed', 'mark_as_failed']
    
    def mark_as_completed(self, request, queryset):
        for transaction in queryset.filter(status='pending'):
            transaction.mark_as_completed()
        self.message_user(request, f"{queryset.filter(status='completed').count()} transactions were marked as completed.")
    mark_as_completed.short_description = "Mark selected transactions as completed"
    
    def mark_as_failed(self, request, queryset):
        for transaction in queryset.filter(status='pending'):
            transaction.mark_as_failed()
        self.message_user(request, f"{queryset.filter(status='failed').count()} transactions were marked as failed.")
    mark_as_failed.short_description = "Mark selected transactions as failed"

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'created_at')
    search_fields = ('user__username',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Wallet Details', {
            'fields': ('balance',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )