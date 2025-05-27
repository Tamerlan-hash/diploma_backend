from rest_framework import serializers
from .models import Reservation, Payment
from sensor.serializers import ParkingSpotSerializer
from sensor.models import ParkingSpot
from django.utils import timezone
from django.db.models import Q

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'amount', 'status', 'payment_date', 'payment_method', 'transaction_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ReservationSerializer(serializers.ModelSerializer):
    payment_status = serializers.SerializerMethodField()
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'user', 'parking_spot', 'start_time', 'end_time', 'status', 
                 'total_price', 'payment_status', 'created_at', 'updated_at']
        read_only_fields = ['user', 'status', 'total_price', 'payment_status', 'created_at', 'updated_at']

    def get_payment_status(self, obj):
        if not obj.payment:
            return 'not_created'
        return obj.payment.status

    def validate(self, data):
        # Ensure end_time is after start_time
        if data['end_time'] <= data['start_time']:
            raise serializers.ValidationError("End time must be after start time")

        # Ensure start_time is not in the past
        if data['start_time'] < timezone.now():
            raise serializers.ValidationError("Start time cannot be in the past")

        # Ensure start_time is on an hourly boundary (minutes, seconds, microseconds are all 0)
        start_time = data['start_time']
        if start_time.minute != 0 or start_time.second != 0 or start_time.microsecond != 0:
            raise serializers.ValidationError("Start time must be at the beginning of an hour (e.g., 10:00, 11:00)")

        # Ensure end_time is on an hourly boundary (minutes, seconds, microseconds are all 0)
        end_time = data['end_time']
        if end_time.minute != 0 or end_time.second != 0 or end_time.microsecond != 0:
            raise serializers.ValidationError("End time must be at the beginning of an hour (e.g., 10:00, 11:00)")

        # Ensure the duration is a whole number of hours
        duration_seconds = (end_time - start_time).total_seconds()
        duration_hours = duration_seconds / 3600
        if duration_hours <= 0 or duration_seconds % 3600 != 0:
            raise serializers.ValidationError("Reservation duration must be a whole number of hours")

        # Check for overlapping reservations
        parking_spot = data['parking_spot']

        # Exclude current reservation when updating
        exclude_id = self.instance.id if self.instance else None

        overlapping_reservations = Reservation.objects.filter(
            parking_spot=parking_spot,
            status__in=['pending', 'active'],
            start_time__lt=end_time,
            end_time__gt=start_time
        )

        if exclude_id:
            overlapping_reservations = overlapping_reservations.exclude(id=exclude_id)

        if overlapping_reservations.exists():
            raise serializers.ValidationError("This parking spot is already reserved for the selected time period")

        return data

    def create(self, validated_data):
        # Set the user to the current user
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class ReservationDetailSerializer(ReservationSerializer):
    parking_spot = ParkingSpotSerializer(read_only=True)
    payment = PaymentSerializer(read_only=True)

    class Meta(ReservationSerializer.Meta):
        fields = ReservationSerializer.Meta.fields + ['payment']
        read_only_fields = ReservationSerializer.Meta.read_only_fields + ['parking_spot', 'payment']

class ReservationListSerializer(serializers.ModelSerializer):
    parking_spot_name = serializers.CharField(source='parking_spot.name', read_only=True)
    payment_status = serializers.SerializerMethodField()
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'parking_spot_name', 'start_time', 'end_time', 'status', 'total_price', 'payment_status']
        read_only_fields = fields

    def get_payment_status(self, obj):
        if not obj.payment:
            return 'not_created'
        return obj.payment.status

class TimeSlotReservationsSerializer(serializers.Serializer):
    """
    Serializer for displaying reservations grouped by time slots.
    This serializer provides information about which parking spots are reserved for each time slot.
    """
    time_slot = serializers.DateTimeField()
    reservations = serializers.SerializerMethodField()

    def get_reservations(self, obj):
        # Get the time slot from the object
        time_slot = obj['time_slot']

        # Get all parking spots
        parking_spots = ParkingSpot.objects.all()
        result = []

        for spot in parking_spots:
            # Check if this spot is reserved at this time slot
            is_reserved = Reservation.objects.filter(
                parking_spot=spot,
                status__in=['pending', 'active'],
                start_time__lte=time_slot,
                end_time__gt=time_slot
            ).exists()

            # Get reservation details if it exists
            reservation = None
            if is_reserved:
                reservation = Reservation.objects.filter(
                    parking_spot=spot,
                    status__in=['pending', 'active'],
                    start_time__lte=time_slot,
                    end_time__gt=time_slot
                ).first()

                reservation = {
                    'id': reservation.id,
                    'user': reservation.user.username,
                    'start_time': reservation.start_time,
                    'end_time': reservation.end_time,
                    'status': reservation.status
                }

            # Check if the spot has a sensor and if it's occupied
            sensor_status = None
            if hasattr(spot, 'sensor'):
                sensor_status = {
                    'is_occupied': spot.sensor.is_occupied
                }

            # Check if the spot has a blocker and its status
            blocker_status = None
            if hasattr(spot, 'blocker'):
                blocker_status = {
                    'is_raised': spot.blocker.is_raised
                }

            result.append({
                'parking_spot_id': spot.reference,
                'parking_spot_name': spot.name,
                'price_per_hour': str(spot.price_per_hour),
                'is_reserved': is_reserved,
                'reservation': reservation,
                'sensor': sensor_status,
                'blocker': blocker_status
            })

        return result
