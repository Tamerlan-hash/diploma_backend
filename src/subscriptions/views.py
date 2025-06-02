from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.models import User
from sensor.models import Sensor
from payments.models import Transaction, Wallet, PaymentMethod
from .models import SubscriptionPlan, UserSubscription, TariffZone, TariffRule, calculate_price_with_subscription
from .serializers import (
    SubscriptionPlanSerializer, UserSubscriptionSerializer, TariffZoneSerializer, 
    TariffRuleSerializer, ParkingSpotPriceSerializer, SubscriptionPurchaseSerializer,
    UserSubscriptionCreateSerializer
)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from decimal import Decimal


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing subscription plans.
    """
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserSubscriptionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing user subscriptions.
    """
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']  # Restrict to GET, POST, DELETE only

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return UserSubscription.objects.filter(user=self.request.user)
        return UserSubscription.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserSubscriptionCreateSerializer
        return UserSubscriptionSerializer

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied("Authentication required")
        serializer.save(user=self.request.user)

    @swagger_auto_schema(
        operation_description="Cancel a subscription",
        responses={
            200: "Subscription cancelled",
            400: "Bad Request",
            404: "Subscription not found"
        }
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_subscription(self, request, pk=None):
        subscription = self.get_object()
        subscription.cancel()
        return Response({"status": "Subscription cancelled"})

    @swagger_auto_schema(
        operation_description="Renew a subscription",
        responses={
            200: "Subscription renewed",
            400: "Bad Request",
            404: "Subscription not found"
        }
    )
    @action(detail=True, methods=['post'], url_path='renew')
    def renew_subscription(self, request, pk=None):
        subscription = self.get_object()
        if subscription.renew():
            return Response({"status": "Subscription renewed"})
        return Response({"error": "Cannot renew inactive subscription"}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Get active subscription",
        responses={
            200: UserSubscriptionSerializer(),
            404: "No active subscription found"
        }
    )
    @action(detail=False, methods=['get'], url_path='active')
    def active_subscription(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        now = timezone.now()
        subscription = UserSubscription.objects.filter(
            user=request.user,
            status='active',
            start_date__lte=now,
            end_date__gte=now
        ).first()

        if subscription:
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        return Response({"error": "No active subscription found"}, status=status.HTTP_404_NOT_FOUND)


class TariffZoneViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing tariff zones.
    """
    queryset = TariffZone.objects.filter(is_active=True)
    serializer_class = TariffZoneSerializer
    permission_classes = [permissions.IsAuthenticated]


class TariffRuleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing tariff rules.
    """
    queryset = TariffRule.objects.filter(is_active=True)
    serializer_class = TariffRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = TariffRule.objects.filter(is_active=True)

        # Filter by zone if provided
        zone_id = self.request.query_params.get('zone_id', None)
        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)

        # Filter by parking spot if provided
        parking_spot_id = self.request.query_params.get('parking_spot_id', None)
        if parking_spot_id:
            queryset = queryset.filter(
                Q(parking_spot_id=parking_spot_id) | Q(parking_spot__isnull=True)
            )

        return queryset


class ParkingSpotPriceView(APIView):
    """
    API endpoint for calculating parking spot prices.
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Calculate price for parking spot",
        request_body=ParkingSpotPriceSerializer,
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'price': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'has_subscription_discount': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'original_price': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'discount_percentage': openapi.Schema(type=openapi.TYPE_NUMBER),
                }
            ),
            400: "Bad Request",
            404: "Parking spot not found"
        }
    )
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = ParkingSpotPriceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get validated data
        parking_spot_id = serializer.validated_data['parking_spot_id']
        start_time = serializer.validated_data['start_time']
        end_time = serializer.validated_data['end_time']

        # Get parking spot
        try:
            parking_spot = Sensor.objects.get(id=parking_spot_id)
        except Sensor.DoesNotExist:
            return Response({"error": "Parking spot not found"}, status=status.HTTP_404_NOT_FOUND)

        # Calculate price with subscription discount
        price = calculate_price_with_subscription(request.user, parking_spot, start_time, end_time)

        # Check if user has active subscription
        active_subscription = UserSubscription.objects.filter(
            user=request.user,
            status='active',
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).first()

        # Calculate original price without discount
        original_price = price
        discount_percentage = 0
        has_subscription_discount = False

        if active_subscription and active_subscription.plan.discount_percentage > 0:
            # If user has active subscription with discount, calculate original price
            discount_percentage = active_subscription.plan.discount_percentage
            original_price = price / (1 - (discount_percentage / Decimal('100.00')))
            has_subscription_discount = True

        return Response({
            'price': price,
            'has_subscription_discount': has_subscription_discount,
            'original_price': original_price,
            'discount_percentage': discount_percentage,
        })


class SubscriptionPurchaseView(APIView):
    """
    API endpoint for purchasing subscriptions.
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Purchase a subscription",
        request_body=SubscriptionPurchaseSerializer,
        responses={
            200: UserSubscriptionSerializer(),
            400: "Bad Request",
            404: "Subscription plan or payment method not found"
        }
    )
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = SubscriptionPurchaseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get validated data
        plan_id = serializer.validated_data['plan_id']
        payment_method_id = serializer.validated_data['payment_method_id']
        auto_renew = serializer.validated_data.get('auto_renew', False)

        # Get subscription plan
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Subscription plan not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get payment method
        try:
            payment_method = PaymentMethod.objects.get(id=payment_method_id, user=request.user)
        except PaymentMethod.DoesNotExist:
            return Response({"error": "Payment method not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if user already has an active subscription
        active_subscription = UserSubscription.objects.filter(
            user=request.user,
            status='active',
            end_date__gte=timezone.now()
        ).first()

        if active_subscription:
            return Response({"error": "User already has an active subscription"}, status=status.HTTP_400_BAD_REQUEST)

        # Create transaction for subscription payment
        transaction = Transaction.objects.create(
            user=request.user,
            payment_method=payment_method,
            amount=plan.price,
            transaction_type='card_payment',
            description=f"Subscription purchase: {plan.name} ({plan.get_duration_days_display()})"
        )

        # Process payment (in a real system, this would integrate with a payment gateway)
        transaction.mark_as_completed(transaction_id=f"SUB-{transaction.id}")

        # Create subscription
        subscription = UserSubscription.objects.create(
            user=request.user,
            plan=plan,
            auto_renew=auto_renew,
            payment_id=transaction.id,
            payment_method=f"{payment_method.get_type_display()} ending in {payment_method.card_number[-4:]}"
        )

        # Return subscription data
        subscription_serializer = UserSubscriptionSerializer(subscription)
        return Response(subscription_serializer.data)


class AdminTariffRuleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for admin management of tariff rules.
    """
    queryset = TariffRule.objects.all()
    serializer_class = TariffRuleSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminTariffZoneViewSet(viewsets.ModelViewSet):
    """
    API endpoint for admin management of tariff zones.
    """
    queryset = TariffZone.objects.all()
    serializer_class = TariffZoneSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminSubscriptionPlanViewSet(viewsets.ModelViewSet):
    """
    API endpoint for admin management of subscription plans.
    """
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.IsAdminUser]


class SubscriptionStatsView(APIView):
    """
    API endpoint for viewing subscription statistics.
    """
    permission_classes = [permissions.IsAdminUser]

    @swagger_auto_schema(
        operation_description="Get subscription statistics",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'total_subscriptions': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'active_subscriptions': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'expired_subscriptions': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'cancelled_subscriptions': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'total_revenue': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'subscriptions_by_plan': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'plan_name': openapi.Schema(type=openapi.TYPE_STRING),
                                'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'revenue': openapi.Schema(type=openapi.TYPE_NUMBER),
                            }
                        )
                    ),
                }
            )
        }
    )
    def get(self, request):
        # Get all subscriptions
        subscriptions = UserSubscription.objects.all()

        # Calculate statistics
        total_subscriptions = subscriptions.count()
        active_subscriptions = subscriptions.filter(status='active', end_date__gte=timezone.now()).count()
        expired_subscriptions = subscriptions.filter(status='expired').count()
        cancelled_subscriptions = subscriptions.filter(status='cancelled').count()

        # Calculate total revenue
        total_revenue = sum(sub.plan.price for sub in subscriptions)

        # Calculate subscriptions by plan
        plans = SubscriptionPlan.objects.all()
        subscriptions_by_plan = []

        for plan in plans:
            plan_subscriptions = subscriptions.filter(plan=plan)
            plan_count = plan_subscriptions.count()
            plan_revenue = sum(sub.plan.price for sub in plan_subscriptions)

            subscriptions_by_plan.append({
                'plan_name': plan.name,
                'count': plan_count,
                'revenue': plan_revenue,
            })

        return Response({
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'expired_subscriptions': expired_subscriptions,
            'cancelled_subscriptions': cancelled_subscriptions,
            'total_revenue': total_revenue,
            'subscriptions_by_plan': subscriptions_by_plan,
        })
