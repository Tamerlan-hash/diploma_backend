from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription, TariffZone, TariffRule


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration_days', 'price', 'discount_percentage', 'is_active')
    list_filter = ('is_active', 'duration_days')
    search_fields = ('name', 'description')


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'status', 'auto_renew')
    list_filter = ('status', 'auto_renew', 'plan')
    search_fields = ('user__username', 'user__email', 'payment_id')
    date_hierarchy = 'start_date'


@admin.register(TariffZone)
class TariffZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')


@admin.register(TariffRule)
class TariffRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'zone', 'parking_spot', 'time_period', 'day_type', 'price_per_hour', 'is_active', 'priority')
    list_filter = ('is_active', 'zone', 'time_period', 'day_type')
    search_fields = ('name', 'zone__name', 'parking_spot__name')
    date_hierarchy = 'valid_from'
    fieldsets = (
        (None, {
            'fields': ('name', 'zone', 'parking_spot', 'price_per_hour', 'is_active', 'priority')
        }),
        ('Time Period', {
            'fields': ('time_period', 'custom_start_time', 'custom_end_time')
        }),
        ('Day Type', {
            'fields': ('day_type', 'custom_days')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to')
        }),
    )