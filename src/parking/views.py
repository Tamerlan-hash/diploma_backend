from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime, timedelta
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from .models import Reservation, Payment
from .serializers import (
    ReservationSerializer, ReservationDetailSerializer, ReservationListSerializer,
    PaymentSerializer, TimeSlotReservationsSerializer
)
from sensor.models import Sensor

class ReservationListCreateView(generics.ListCreateAPIView):
    """
    List all reservations for the current user or create a new reservation.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ReservationSerializer

    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ReservationListSerializer
        return ReservationSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        return context

class ReservationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a reservation instance.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ReservationDetailSerializer

    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        instance.cancel()

class AvailableParkingSpotsView(APIView):
    """
    List all available parking spots for a given time period.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get available parking spots for a time period",
        manual_parameters=[
            openapi.Parameter('start_time', openapi.IN_QUERY, description="Start time (ISO format)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, required=True),
            openapi.Parameter('end_time', openapi.IN_QUERY, description="End time (ISO format)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, required=True),
        ],
        responses={200: 'List of available parking spots'}
    )
    def get(self, request):
        from django.utils.dateparse import parse_datetime
        from sensor.serializers import SensorSerializer

        start_time = parse_datetime(request.query_params.get('start_time'))
        end_time = parse_datetime(request.query_params.get('end_time'))

        if not start_time or not end_time:
            return Response({"error": "Valid start_time and end_time are required"}, status=status.HTTP_400_BAD_REQUEST)

        if end_time <= start_time:
            return Response({"error": "End time must be after start time"}, status=status.HTTP_400_BAD_REQUEST)

        # Get all parking spots
        all_spots = Sensor.objects.all()

        # Get reserved parking spots for the given time period
        reserved_spot_ids = Reservation.objects.filter(
            status__in=['pending', 'active'],
            start_time__lt=end_time,
            end_time__gt=start_time
        ).values_list('parking_spot_id', flat=True)

        # Filter out reserved spots
        available_spots = all_spots.exclude(reference__in=reserved_spot_ids)

        serializer = SensorSerializer(available_spots, many=True)
        return Response(serializer.data)

class ReservationActionView(APIView):
    """
    Perform actions on a reservation (activate, complete, cancel).
    """
    permission_classes = [IsAuthenticated]

    def get_reservation(self, pk):
        return get_object_or_404(Reservation, pk=pk, user=self.request.user)

    @swagger_auto_schema(
        operation_description="Activate a reservation",
        responses={200: ReservationDetailSerializer()}
    )
    def post(self, request, pk, action):
        reservation = self.get_reservation(pk)

        if action == 'activate':
            reservation.activate()
        elif action == 'complete':
            reservation.complete()
        elif action == 'cancel':
            reservation.cancel()
        else:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReservationDetailSerializer(reservation)
        return Response(serializer.data)

class UserReservationsView(generics.ListAPIView):
    """
    List all reservations for the current user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ReservationListSerializer

    def get_queryset(self):
        status_filter = self.request.query_params.get('status')
        queryset = Reservation.objects.filter(user=self.request.user)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

class ReservationPaymentView(APIView):
    """
    Create and process payments for reservations.
    """
    permission_classes = [IsAuthenticated]

    def get_reservation(self, pk):
        return get_object_or_404(Reservation, pk=pk, user=self.request.user)

    @swagger_auto_schema(
        operation_description="Create a payment for a reservation",
        responses={
            200: PaymentSerializer(),
            400: "Bad Request",
            404: "Reservation not found"
        }
    )
    def post(self, request, pk, action):
        reservation = self.get_reservation(pk)

        if action == 'create':
            # Calculate total price and create payment
            payment = reservation.create_payment()
            serializer = PaymentSerializer(payment)
            return Response(serializer.data)

        elif action == 'process':
            # Process the payment
            payment_method = request.data.get('payment_method', '')
            transaction_id = request.data.get('transaction_id', '')

            if not reservation.payment:
                return Response(
                    {"error": "Payment not created yet. Create payment first."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if reservation.payment.status == 'completed':
                return Response(
                    {"error": "Payment already completed"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            reservation.process_payment(payment_method, transaction_id)
            serializer = PaymentSerializer(reservation.payment)
            return Response(serializer.data)

        elif action == 'wallet':
            # Process payment using wallet
            from payments.models import Wallet, Transaction

            # Ensure payment is created
            if not reservation.payment:
                reservation.create_payment()

            if reservation.payment.status == 'completed':
                return Response(
                    {"error": "Payment already completed"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                # Get user's wallet
                wallet = Wallet.objects.get(user=request.user)

                # Create wallet payment transaction
                transaction = Transaction.create_wallet_payment(
                    wallet=wallet,
                    amount=reservation.total_price,
                    reservation_id=str(reservation.id),
                    description=f"Payment for reservation #{reservation.id}"
                )

                # Update reservation payment
                reservation.process_payment(
                    payment_method='wallet',
                    transaction_id=transaction.transaction_id
                )

                # Return payment details
                serializer = PaymentSerializer(reservation.payment)
                return Response(serializer.data)

            except Wallet.DoesNotExist:
                return Response(
                    {"error": "Wallet not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            except ValueError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        else:
            return Response(
                {"error": "Invalid action. Use 'create', 'process', or 'wallet'."},
                status=status.HTTP_400_BAD_REQUEST
            )

class TimeSlotReservationsView(APIView):
    """
    List reservations grouped by time slots.
    This view generates time slots based on the provided parameters and returns
    the reservation status for each parking spot at each time slot.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get reservations grouped by time slots",
        manual_parameters=[
            openapi.Parameter('start_time', openapi.IN_QUERY, description="Start time (ISO format)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, required=True),
            openapi.Parameter('end_time', openapi.IN_QUERY, description="End time (ISO format)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, required=True),
            openapi.Parameter('interval', openapi.IN_QUERY, description="Interval in minutes", type=openapi.TYPE_INTEGER, default=60),
        ],
        responses={200: 'List of time slots with reservations'}
    )
    def get(self, request):
        # Parse parameters
        start_time = parse_datetime(request.query_params.get('start_time'))
        end_time = parse_datetime(request.query_params.get('end_time'))
        interval_minutes = int(request.query_params.get('interval', 60))

        if not start_time or not end_time:
            return Response({"error": "Valid start_time and end_time are required"}, status=status.HTTP_400_BAD_REQUEST)

        if end_time <= start_time:
            return Response({"error": "End time must be after start time"}, status=status.HTTP_400_BAD_REQUEST)

        # Generate time slots
        time_slots = []
        current_time = start_time
        while current_time < end_time:
            time_slots.append(current_time)
            current_time += timedelta(minutes=interval_minutes)

        # Prepare response data
        result = []
        for time_slot in time_slots:
            serializer = TimeSlotReservationsSerializer({
                'time_slot': time_slot,
            })
            result.append(serializer.data)

        return Response(result)


class ParkingSpotAvailableWindowsView(APIView):
    """
    Get booking windows for a specific parking spot.
    This view returns a list of hourly time slots for a specific parking spot
    within a given date range, including both available and blocked slots.
    All windows are exactly one hour in duration.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get booking windows for a specific parking spot",
        manual_parameters=[
            openapi.Parameter('date', openapi.IN_QUERY, description="Date (YYYY-MM-DD)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, required=True),
        ],
        responses={200: 'List of hourly booking windows with status'}
    )
    def get(self, request, spot_id):
        # Get the parking spot
        try:
            # First try to get by reference (UUID)
            import uuid
            try:
                # Try to convert to UUID if it's in UUID format
                uuid_obj = uuid.UUID(spot_id)
                parking_spot = Sensor.objects.get(reference=uuid_obj)
            except (ValueError, TypeError):
                # If not a valid UUID, try to get by name
                parking_spot = Sensor.objects.get(name=spot_id)
        except Sensor.DoesNotExist:
            return Response({"error": "Parking spot not found"}, status=status.HTTP_404_NOT_FOUND)

        # Parse parameters
        date_str = request.query_params.get('date')

        try:
            if date_str:
                # Parse the provided date
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                # Use today's date as default
                selected_date = timezone.now().date()

            # Create datetime objects for start and end of the day
            start_time = timezone.make_aware(datetime.combine(selected_date, datetime.min.time()))
            end_time = timezone.make_aware(datetime.combine(selected_date + timedelta(days=1), datetime.min.time()))
        except (ValueError, TypeError):
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        # Get reservations for this parking spot on the selected date
        reservations = Reservation.objects.filter(
            parking_spot=parking_spot,
            status__in=['pending', 'active'],
            start_time__lt=end_time,
            end_time__gt=start_time
        ).order_by('start_time')

        # Create a list of all hours in the day
        hourly_slots = []
        current_hour = start_time.replace(minute=0, second=0, microsecond=0)

        while current_hour < end_time:
            next_hour = current_hour + timedelta(hours=1)
            hourly_slots.append((current_hour, next_hour))
            current_hour = next_hour

        # Get current time for checking past slots
        now = timezone.now()

        # Process all slots and mark their status
        hourly_windows = []

        for slot_start, slot_end in hourly_slots:
            # Default status is available
            status = "available"
            reason = None

            # Check if this slot has already ended
            if slot_end < now:
                status = "blocked"
                reason = "past_time"
            else:
                # Check if this hourly slot overlaps with any reservation
                for reservation in reservations:
                    # If reservation overlaps with this slot, mark as blocked
                    if (reservation.start_time < slot_end and 
                        reservation.end_time > slot_start):
                        status = "blocked"
                        reason = "already_booked"
                        break

            hourly_windows.append({
                'start_time': slot_start.isoformat(),
                'end_time': slot_end.isoformat(),
                'status': status,
                'reason': reason
            })

        return Response(hourly_windows)
