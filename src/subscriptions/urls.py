from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SubscriptionPlanViewSet, UserSubscriptionViewSet, TariffZoneViewSet, TariffRuleViewSet,
    ParkingSpotPriceView, SubscriptionPurchaseView, AdminTariffRuleViewSet, AdminTariffZoneViewSet,
    AdminSubscriptionPlanViewSet, SubscriptionStatsView
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'plans', SubscriptionPlanViewSet)
router.register(r'subscriptions', UserSubscriptionViewSet, basename='subscription')
router.register(r'zones', TariffZoneViewSet)
router.register(r'rules', TariffRuleViewSet, basename='tariff-rule')

# Create a router for admin ViewSets
admin_router = DefaultRouter()
admin_router.register(r'rules', AdminTariffRuleViewSet)
admin_router.register(r'zones', AdminTariffZoneViewSet)
admin_router.register(r'plans', AdminSubscriptionPlanViewSet)

urlpatterns = [
    # User-facing API endpoints
    path('', include(router.urls)),
    path('calculate-price/', ParkingSpotPriceView.as_view(), name='calculate-price'),
    path('purchase-subscription/', SubscriptionPurchaseView.as_view(), name='purchase-subscription'),

    # Admin API endpoints
    path('admin/', include(admin_router.urls)),
    path('admin/stats/', SubscriptionStatsView.as_view(), name='subscription-stats'),
]
