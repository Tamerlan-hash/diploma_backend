import pytest
from django.utils import timezone
from datetime import timedelta
import uuid
from decimal import Decimal
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from sensor.models import Sensor, ParkingSpot, Blocker
from parking.models import Reservation, Payment
from subscriptions.models import TariffZone, TariffRule
from rest_framework.test import APIRequestFactory
from parking.serializers import ReservationSerializer

@pytest.mark.django_db
class TestParkingSpotWithTariff:
    """Test that ParkingSpot requires a tariff_zone."""

    @pytest.fixture
    def setup_data(self):
        """Set up test data for parking spot tests."""
        # Create a tariff zone
        tariff_zone = TariffZone.objects.create(
            name='Test Zone',
            description='Test Zone Description',
            is_active=True
        )

        return {
            'tariff_zone': tariff_zone
        }

    def test_parking_spot_requires_tariff_zone(self, setup_data):
        """Test that creating a ParkingSpot without a tariff_zone raises an error."""
        # Try to create a parking spot without a tariff_zone
        with pytest.raises(IntegrityError):
            ParkingSpot.objects.create(
                reference=uuid.uuid4(),
                name='Test Parking Spot'
            )

    def test_parking_spot_with_tariff_zone(self, setup_data):
        """Test creating a ParkingSpot with a tariff_zone."""
        # Create a parking spot with a tariff_zone
        parking_spot = ParkingSpot.objects.create(
            reference=uuid.uuid4(),
            name='Test Parking Spot',
            tariff_zone=setup_data['tariff_zone']
        )

        # Verify the parking spot was created
        assert parking_spot.tariff_zone == setup_data['tariff_zone']


@pytest.mark.django_db
class TestReservationWithTariff:
    """Test reservation with tariff-based pricing."""

    @pytest.fixture
    def setup_data(self):
        """Set up test data for reservation tests."""
        # Create a test user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        # Create a tariff zone
        tariff_zone = TariffZone.objects.create(
            name='Test Zone',
            description='Test Zone Description',
            is_active=True
        )

        # Create a test parking spot
        parking_spot = ParkingSpot.objects.create(
            reference=uuid.uuid4(),
            name='Test Parking Spot',
            tariff_zone=tariff_zone
        )

        # Create a tariff rule for the parking spot
        tariff_rule = TariffRule.objects.create(
            name='Test Rule',
            zone=tariff_zone,
            parking_spot=parking_spot,
            time_period='all_day',
            day_type='all',
            price_per_hour=Decimal('150.00'),
            is_active=True
        )

        # Create a test sensor
        sensor = Sensor.objects.create(
            reference=uuid.uuid4(),
            parking_spot=parking_spot,
            is_occupied=False
        )

        # Create a blocker for the parking spot
        blocker = Blocker.objects.create(
            reference=uuid.uuid4(),
            parking_spot=parking_spot,
            is_raised=False
        )

        # Set up time variables
        now = timezone.now()
        start_time = now + timedelta(hours=1)
        end_time = now + timedelta(hours=3)  # 2 hours duration

        return {
            'user': user,
            'tariff_zone': tariff_zone,
            'parking_spot': parking_spot,
            'tariff_rule': tariff_rule,
            'sensor': sensor,
            'blocker': blocker,
            'now': now,
            'start_time': start_time,
            'end_time': end_time
        }

    def test_reservation_uses_tariff_pricing(self, setup_data):
        """Test that reservation uses tariff-based pricing."""
        data = setup_data

        # Create a reservation
        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['parking_spot'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status='pending'
        )

        # Calculate total price
        total_price = reservation.calculate_total_price()

        # Should be 2 hours * 150.00 = 300.00 (using tariff rule price)
        assert total_price == Decimal('300.00')

    def test_reservation_payment_process(self, setup_data):
        """Test the reservation payment process."""
        data = setup_data

        # Create a reservation
        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['parking_spot'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status='pending'
        )

        # Create payment
        payment = reservation.create_payment()

        # Verify payment was created with correct amount
        assert payment is not None
        assert payment.amount == Decimal('300.00')  # 2 hours * 150.00
        assert payment.status == 'pending'

        # Process payment
        reservation.process_payment(
            payment_method='credit_card',
            transaction_id='txn_123456'
        )

        # Refresh from database
        reservation.refresh_from_db()

        # Verify reservation was activated after payment
        assert reservation.status == 'active'
        assert reservation.payment.status == 'completed'


@pytest.mark.django_db
class TestFlexibleTimeSelection:
    """Test flexible time selection for reservations."""

    @pytest.fixture
    def setup_data(self):
        """Set up test data for time selection tests."""
        # Create a test user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        # Create a tariff zone
        tariff_zone = TariffZone.objects.create(
            name='Test Zone',
            description='Test Zone Description',
            is_active=True
        )

        # Create a test parking spot
        parking_spot = ParkingSpot.objects.create(
            reference=uuid.uuid4(),
            name='Test Parking Spot',
            tariff_zone=tariff_zone
        )

        # Create a tariff rule for the parking spot
        tariff_rule = TariffRule.objects.create(
            name='Test Rule',
            zone=tariff_zone,
            parking_spot=parking_spot,
            time_period='all_day',
            day_type='all',
            price_per_hour=Decimal('150.00'),
            is_active=True
        )

        # Create a test sensor
        sensor = Sensor.objects.create(
            reference=uuid.uuid4(),
            parking_spot=parking_spot,
            is_occupied=False
        )

        # Set up time variables
        now = timezone.now()

        return {
            'user': user,
            'tariff_zone': tariff_zone,
            'parking_spot': parking_spot,
            'tariff_rule': tariff_rule,
            'sensor': sensor,
            'now': now
        }

    def test_flexible_start_time(self, setup_data):
        """Test that reservation can start at any time, not just on hourly boundaries."""
        data = setup_data

        # Create a reservation with a non-hourly start time (e.g., 10:30)
        start_time = data['now'].replace(minute=30, second=0, microsecond=0) + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        # Create a reservation
        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['parking_spot'],
            start_time=start_time,
            end_time=end_time,
            status='pending'
        )

        # Verify the reservation was created with the specified times
        assert reservation.start_time == start_time
        assert reservation.end_time == end_time

    def test_flexible_end_time(self, setup_data):
        """Test that reservation can end at any time, not just on hourly boundaries."""
        data = setup_data

        # Create a reservation with a non-hourly end time (e.g., 12:45)
        start_time = data['now'].replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2, minutes=45)

        # Create a reservation
        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['parking_spot'],
            start_time=start_time,
            end_time=end_time,
            status='pending'
        )

        # Verify the reservation was created with the specified times
        assert reservation.start_time == start_time
        assert reservation.end_time == end_time

    def test_next_day_reservation(self, setup_data):
        """Test that reservation can span to the next day."""
        data = setup_data

        # Create a reservation from 11:00 today to 10:00 tomorrow
        today = data['now'].replace(hour=11, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        # Create a reservation
        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['parking_spot'],
            start_time=today,
            end_time=tomorrow,
            status='pending'
        )

        # Verify the reservation was created with the specified times
        assert reservation.start_time == today
        assert reservation.end_time == tomorrow

    def test_serializer_validation(self, setup_data):
        """Test that the serializer validates flexible time selection."""
        data = setup_data

        # Create a request factory
        factory = APIRequestFactory()
        request = factory.post('/api/reservations/')
        request.user = data['user']

        # Create a reservation with non-hourly times
        start_time = data['now'] + timedelta(hours=1, minutes=30)
        end_time = start_time + timedelta(hours=2, minutes=45)

        # Create serializer data
        serializer_data = {
            'parking_spot': data['parking_spot'].reference,
            'start_time': start_time,
            'end_time': end_time
        }

        # Create serializer
        serializer = ReservationSerializer(data=serializer_data, context={'request': request})

        # Verify serializer is valid
        assert serializer.is_valid()

        # Create the reservation
        reservation = serializer.save()

        # Verify the reservation was created with the specified times
        assert reservation.start_time == start_time
        assert reservation.end_time == end_time