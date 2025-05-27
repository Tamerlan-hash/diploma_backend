from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentMethodViewSet, TransactionViewSet, PaymentProcessView, WalletViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'wallet', WalletViewSet, basename='wallet')

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
    path('process/', PaymentProcessView.as_view(), name='payment-process'),
]
