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
    selected_hours = serializers.JSONField(required=False)
    payment_method_type = serializers.CharField(required=False, write_only=True)
    payment_method_id = serializers.IntegerField(required=False, write_only=True, allow_null=True)
    parking_spot = serializers.PrimaryKeyRelatedField(queryset=ParkingSpot.objects.all(), required=True)

    class Meta:
        model = Reservation
        fields = ['id', 'user', 'parking_spot', 'start_time', 'end_time', 'status', 
                 'total_price', 'payment_status', 'created_at', 'updated_at', 'selected_hours',
                 'payment_method_type', 'payment_method_id']
        read_only_fields = ['user', 'status', 'total_price', 'payment_status', 'created_at', 'updated_at']

    def get_payment_status(self, obj):
        if not obj.payment:
            return 'not_created'
        return obj.payment.status

    def validate(self, data):
        # Check if we're using hourly booking
        selected_hours = data.get('selected_hours', [])

        if selected_hours:
            # Validate selected_hours format
            if not isinstance(selected_hours, list):
                raise serializers.ValidationError({"selected_hours": "Must be a list of hour slots"})

            if not selected_hours:
                raise serializers.ValidationError({"selected_hours": "At least one hour slot must be selected"})

            # Validate each hour slot
            now = timezone.now()
            parking_spot = data['parking_spot']

            # Set start_time and end_time based on selected hours
            start_times = []
            end_times = []

            for i, slot in enumerate(selected_hours):
                if not isinstance(slot, dict) or 'start' not in slot or 'end' not in slot:
                    raise serializers.ValidationError({"selected_hours": f"Invalid format for slot {i}"})

                try:
                    start = timezone.datetime.fromisoformat(slot['start'])
                    end = timezone.datetime.fromisoformat(slot['end'])

                    # Ensure each slot is exactly 1 hour
                    duration_seconds = (end - start).total_seconds()
                    if duration_seconds != 3600:  # 3600 seconds = 1 hour
                        raise serializers.ValidationError({"selected_hours": f"Slot {i} must be exactly 1 hour"})

                    # Check if the slot is in the past
                    if start < now:
                        raise serializers.ValidationError({"selected_hours": f"Slot {i} is in the past"})

                    # Check for overlapping reservations
                    exclude_id = self.instance.id if self.instance else None

                    overlapping_reservations = Reservation.objects.filter(
                        parking_spot=parking_spot,
                        status__in=['pending', 'active'],
                        start_time__lt=end,
                        end_time__gt=start
                    )

                    if exclude_id:
                        overlapping_reservations = overlapping_reservations.exclude(id=exclude_id)

                    if overlapping_reservations.exists():
                        raise serializers.ValidationError({"selected_hours": f"Slot {i} overlaps with an existing reservation"})

                    start_times.append(start)
                    end_times.append(end)

                except (ValueError, TypeError):
                    raise serializers.ValidationError({"selected_hours": f"Invalid datetime format for slot {i}"})

            # Validate that selected hours are consecutive
            if len(selected_hours) > 1:
                # Sort slots by start time
                sorted_slots = sorted(selected_hours, key=lambda x: timezone.datetime.fromisoformat(x['start']))

                # Check if slots are consecutive
                for i in range(len(sorted_slots) - 1):
                    current_end = timezone.datetime.fromisoformat(sorted_slots[i]['end'])
                    next_start = timezone.datetime.fromisoformat(sorted_slots[i+1]['start'])

                    if current_end != next_start:
                        raise serializers.ValidationError({"selected_hours": "Selected hours must be consecutive"})

            # Set overall start_time and end_time
            if start_times and end_times:
                data['start_time'] = min(start_times)
                data['end_time'] = max(end_times)
        else:
            # Traditional validation for non-hourly bookings
            # Ensure end_time is after start_time
            if data['end_time'] <= data['start_time']:
                raise serializers.ValidationError({"non_field_errors": ["End time must be after start time"]})


            # Get start and end times
            start_time = data['start_time']
            end_time = data['end_time']

            # Ensure minimum duration of 1 hour
            duration_seconds = (end_time - start_time).total_seconds()
            if duration_seconds < 3600:  # 3600 seconds = 1 hour
                raise serializers.ValidationError({"non_field_errors": ["Reservation must be at least 1 hour long"]})

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
                raise serializers.ValidationError({"non_field_errors": ["This parking spot is already reserved for the selected time period"]})

        return data

    def create(self, validated_data):
        # Extract payment method data
        payment_method_type = validated_data.pop('payment_method_type', None)
        payment_method_id = validated_data.pop('payment_method_id', None)

        # Set the user to the current user
        validated_data['user'] = self.context['request'].user

        # Create the reservation
        reservation = super().create(validated_data)

        # Calculate total price
        reservation.total_price = reservation.calculate_total_price()
        reservation.save(update_fields=['total_price'])

        # Process payment if payment method is provided
        if payment_method_type:
            try:
                if payment_method_type == 'wallet':
                    # Process wallet payment
                    reservation.process_wallet_payment()
                elif payment_method_type == 'card' and payment_method_id:
                    # Process card payment
                    reservation.process_card_payment(payment_method_id)
                else:
                    # Create payment without processing
                    reservation.create_payment()
            except Exception as e:
                # If payment processing fails, still return the reservation
                # but with an error message
                reservation.status = 'pending'
                reservation.save()
                # You might want to log the error here
                print(f"Payment processing error: {str(e)}")

        return reservation

class ReservationDetailSerializer(ReservationSerializer):
    parking_spot = ParkingSpotSerializer(read_only=True)
    payment = PaymentSerializer(read_only=True)
    is_occupied = serializers.SerializerMethodField()
    is_blocker_raised = serializers.SerializerMethodField()
    can_control_blocker = serializers.SerializerMethodField()

    class Meta(ReservationSerializer.Meta):
        fields = ReservationSerializer.Meta.fields + ['payment', 'is_occupied', 'is_blocker_raised', 'can_control_blocker']
        read_only_fields = ReservationSerializer.Meta.read_only_fields + ['parking_spot', 'payment', 'is_occupied', 'is_blocker_raised', 'can_control_blocker']

    def get_can_control_blocker(self, obj):
        """Check if user can control the blocker for this reservation"""
        # User can control blocker if reservation is active and paid
        return obj.status == 'active' and obj.payment and obj.payment.status == 'completed'

    def get_is_occupied(self, obj):
        if hasattr(obj.parking_spot, 'sensor'):
            return obj.parking_spot.sensor.is_occupied
        return False

    def get_is_blocker_raised(self, obj):
        if hasattr(obj.parking_spot, 'blocker'):
            return obj.parking_spot.blocker.is_raised
        return False

class ReservationListSerializer(serializers.ModelSerializer):
    parking_spot_name = serializers.CharField(source='parking_spot.name', read_only=True)
    payment_status = serializers.SerializerMethodField()
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_occupied = serializers.SerializerMethodField()
    is_blocker_raised = serializers.SerializerMethodField()
    can_control_blocker = serializers.SerializerMethodField()
    selected_hours = serializers.JSONField(read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'parking_spot_name', 'start_time', 'end_time', 'status', 'total_price', 
                 'payment_status', 'is_occupied', 'is_blocker_raised', 'can_control_blocker', 'selected_hours']
        read_only_fields = fields

    def get_payment_status(self, obj):
        if not obj.payment:
            return 'not_created'
        return obj.payment.status

    def get_is_occupied(self, obj):
        if hasattr(obj.parking_spot, 'sensor'):
            return obj.parking_spot.sensor.is_occupied
        return False

    def get_is_blocker_raised(self, obj):
        if hasattr(obj.parking_spot, 'blocker'):
            return obj.parking_spot.blocker.is_raised
        return False

    def get_can_control_blocker(self, obj):
        """Check if user can control the blocker for this reservation"""
        # User can control blocker if reservation is active and paid
        return obj.status == 'active' and obj.payment and obj.payment.status == 'completed'

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


class UserBookingHoursSerializer(serializers.Serializer):
    """
    Serializer for displaying users and their booking hours for a specific parking spot.
    This serializer provides information about how many hours each user has booked a particular parking spot.
    """
    parking_spot = serializers.SerializerMethodField()
    user_bookings = serializers.SerializerMethodField()

    def get_parking_spot(self, obj):
        spot = obj['parking_spot']
        return {
            'id': spot.reference,
            'name': spot.name,
            'price_per_hour': str(spot.price_per_hour)
        }

    def get_user_bookings(self, obj):
        # Get the parking spot from the object
        spot = obj['parking_spot']

        # Get all reservations for this parking spot
        reservations = Reservation.objects.filter(
            parking_spot=spot,
            status__in=['pending', 'active', 'completed']
        ).select_related('user')

        # Group reservations by user
        user_bookings = {}

        for reservation in reservations:
            username = reservation.user.username
            user_id = reservation.user.id

            # Calculate hours for this reservation
            if reservation.selected_hours:
                # If we have selected hours, calculate based on those
                hours = len(reservation.selected_hours)
            else:
                # Otherwise calculate based on start and end time
                duration = reservation.end_time - reservation.start_time
                hours = duration.total_seconds() / 3600  # Convert seconds to hours

            # Add or update user in the dictionary
            if username not in user_bookings:
                user_bookings[username] = {
                    'user_id': user_id,
                    'username': username,
                    'total_hours': hours,
                    'reservations': [{
                        'id': reservation.id,
                        'start_time': reservation.start_time,
                        'end_time': reservation.end_time,
                        'status': reservation.status,
                        'hours': hours
                    }]
                }
            else:
                user_bookings[username]['total_hours'] += hours
                user_bookings[username]['reservations'].append({
                    'id': reservation.id,
                    'start_time': reservation.start_time,
                    'end_time': reservation.end_time,
                    'status': reservation.status,
                    'hours': hours
                })

        # Convert dictionary to list and sort by total hours (descending)
        result = list(user_bookings.values())
        result.sort(key=lambda x: x['total_hours'], reverse=True)

        return result
