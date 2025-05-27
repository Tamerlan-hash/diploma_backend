from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription, TariffZone, TariffRule
from django.contrib.auth.models import User


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'description', 'duration_days', 'price', 'discount_percentage', 'is_active']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan_details = SubscriptionPlanSerializer(source='plan', read_only=True)

    class Meta:
        model = UserSubscription
        fields = ['id', 'user', 'plan', 'plan_details', 'start_date', 'end_date', 'status', 'auto_renew', 'created_at']
        read_only_fields = ['start_date', 'end_date', 'status', 'created_at']


class UserSubscriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSubscription
        fields = ['plan', 'auto_renew', 'payment_method']

    def create(self, validated_data):
        # Get the user from the context
        user = self.context['request'].user

        # Create the subscription
        subscription = UserSubscription.objects.create(
            user=user,
            plan=validated_data['plan'],
            auto_renew=validated_data.get('auto_renew', False),
            payment_method=validated_data.get('payment_method', '')
        )

        return subscription


class TariffZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = TariffZone
        fields = ['id', 'name', 'description', 'is_active']


class TariffRuleSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    parking_spot_name = serializers.CharField(source='parking_spot.name', read_only=True)

    class Meta:
        model = TariffRule
        fields = [
            'id', 'name', 'zone', 'zone_name', 'parking_spot', 'parking_spot_name',
            'time_period', 'custom_start_time', 'custom_end_time',
            'day_type', 'custom_days', 'price_per_hour',
            'valid_from', 'valid_to', 'is_active', 'priority'
        ]


class ParkingSpotPriceSerializer(serializers.Serializer):
    parking_spot_id = serializers.IntegerField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()

    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("End time must be after start time")
        return data


class SubscriptionPurchaseSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    payment_method_id = serializers.IntegerField()
    auto_renew = serializers.BooleanField(default=False)
