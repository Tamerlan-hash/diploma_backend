import pytest
from django.utils import timezone
from datetime import timedelta
import uuid
from decimal import Decimal
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from sensor.models import Sensor
from parking.models import Reservation, Payment

@pytest.mark.django_db
class TestReservationModel:
    """Test the Reservation model functionality."""

    @pytest.fixture
    def setup_data(self):
        """Set up test data for reservation tests."""
        # Create a test user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        # Create a test sensor
        sensor = Sensor.objects.create(
            reference=uuid.uuid4(),
            name='Test Parking Spot',
            is_lock=False
        )

        # Set up time variables
        now = timezone.now()
        start_time = now + timedelta(hours=1)
        end_time = now + timedelta(hours=2)

        return {
            'user': user,
            'sensor': sensor,
            'now': now,
            'start_time': start_time,
            'end_time': end_time
        }

    def test_reservation_str_representation(self, setup_data):
        """Test the string representation of a reservation."""
        data = setup_data

        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status='pending'
        )

        expected_str = f"{data['user'].username} - {data['sensor'].name} ({data['start_time']} to {data['end_time']})"
        assert str(reservation) == expected_str

    def test_reservation_is_active_method(self, setup_data):
        """Test the is_active method of the Reservation model."""
        data = setup_data

        # Create a reservation that should be active
        now = timezone.now()
        active_reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=now - timedelta(minutes=30),  # Started 30 minutes ago
            end_time=now + timedelta(minutes=30),    # Ends 30 minutes from now
            status='active'
        )

        # Create a reservation that should not be active (future start time)
        future_reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            status='active'
        )

        # Create a reservation that should not be active (past end time)
        past_reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
            status='active'
        )

        # Create a reservation that should not be active (wrong status)
        wrong_status_reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=now - timedelta(minutes=30),
            end_time=now + timedelta(minutes=30),
            status='pending'
        )

        assert active_reservation.is_active() is True
        assert future_reservation.is_active() is False
        assert past_reservation.is_active() is False
        assert wrong_status_reservation.is_active() is False

    def test_activate_method_from_pending(self, setup_data):
        """Test activating a reservation from pending status."""
        data = setup_data

        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status='pending'
        )

        reservation.activate()

        # Refresh from database
        reservation.refresh_from_db()
        data['sensor'].refresh_from_db()

        assert reservation.status == 'active'
        assert data['sensor'].is_lock is True

    def test_activate_method_from_non_pending(self, setup_data):
        """Test that activating a non-pending reservation has no effect."""
        data = setup_data

        # Create reservations with non-pending statuses
        active_reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status='active'
        )

        completed_reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status='completed'
        )

        cancelled_reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status='cancelled'
        )

        # Try to activate each reservation
        active_reservation.activate()
        completed_reservation.activate()
        cancelled_reservation.activate()

        # Refresh from database
        active_reservation.refresh_from_db()
        completed_reservation.refresh_from_db()
        cancelled_reservation.refresh_from_db()

        # Status should remain unchanged
        assert active_reservation.status == 'active'
        assert completed_reservation.status == 'completed'
        assert cancelled_reservation.status == 'cancelled'

    def test_complete_method_from_active(self, setup_data):
        """Test completing a reservation from active status."""
        data = setup_data

        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status='active'
        )

        # Lock the sensor
        data['sensor'].lock()

        reservation.complete()

        # Refresh from database
        reservation.refresh_from_db()
        data['sensor'].refresh_from_db()

        assert reservation.status == 'completed'
        assert data['sensor'].is_lock is False

    def test_complete_method_from_non_active(self, setup_data):
        """Test that completing a non-active reservation has no effect."""
        data = setup_data

        # Create reservations with non-active statuses
        pending_reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status='pending'
        )

        completed_reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status='completed'
        )

        cancelled_reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status='cancelled'
        )

        # Try to complete each reservation
        pending_reservation.complete()
        completed_reservation.complete()
        cancelled_reservation.complete()

        # Refresh from database
        pending_reservation.refresh_from_db()
        completed_reservation.refresh_from_db()
        cancelled_reservation.refresh_from_db()

        # Status should remain unchanged
        assert pending_reservation.status == 'pending'
        assert completed_reservation.status == 'completed'
        assert cancelled_reservation.status == 'cancelled'

    def test_cancel_method_from_pending(self, setup_data):
        """Test cancelling a reservation from pending status."""
        data = setup_data

        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status='pending'
        )

        reservation.cancel()

        # Refresh from database
        reservation.refresh_from_db()

        assert reservation.status == 'cancelled'

    def test_cancel_method_from_active(self, setup_data):
        """Test cancelling a reservation from active status."""
        data = setup_data

        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status='active'
        )

        # Lock the sensor
        data['sensor'].lock()

        reservation.cancel()

        # Refresh from database
        reservation.refresh_from_db()
        data['sensor'].refresh_from_db()

        assert reservation.status == 'cancelled'
        assert data['sensor'].is_lock is False

    def test_cancel_method_from_non_cancellable(self, setup_data):
        """Test that cancelling a completed reservation has no effect."""
        data = setup_data

        # Create a completed reservation
        completed_reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status='completed'
        )

        # Try to cancel the reservation
        completed_reservation.cancel()

        # Refresh from database
        completed_reservation.refresh_from_db()

        # Status should remain unchanged
        assert completed_reservation.status == 'completed'

    def test_end_time_after_start_time_constraint(self, setup_data):
        """Test that the end_time_after_start_time constraint is enforced."""
        data = setup_data

        # Try to create a reservation with end_time before start_time
        with pytest.raises(IntegrityError):
            Reservation.objects.create(
                user=data['user'],
                parking_spot=data['sensor'],
                start_time=data['now'] + timedelta(hours=2),
                end_time=data['now'] + timedelta(hours=1),  # Before start_time
                status='pending'
            )

    def test_calculate_total_price(self, setup_data):
        """Test calculating the total price based on reservation duration."""
        data = setup_data

        # Create a reservation for 2 hours with default price_per_hour (100.00)
        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['start_time'] + timedelta(hours=2),
            status='pending'
        )

        # Calculate total price
        total_price = reservation.calculate_total_price()

        # Should be 2 hours * 100.00 = 200.00
        assert total_price == Decimal('200.00')

    def test_calculate_total_price_partial_hour(self, setup_data):
        """Test calculating the total price with partial hours (should round up)."""
        data = setup_data

        # Create a reservation for 1.5 hours with default price_per_hour (100.00)
        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['start_time'] + timedelta(hours=1, minutes=30),
            status='pending'
        )

        # Calculate total price (should round up to 2 hours)
        total_price = reservation.calculate_total_price()

        # Should be 2 hours * 100.00 = 200.00 (rounded up from 1.5 hours)
        assert total_price == Decimal('200.00')

    def test_create_payment(self, setup_data):
        """Test creating a payment for a reservation."""
        data = setup_data

        # Create a reservation
        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['start_time'] + timedelta(hours=2),
            status='pending'
        )

        # Create payment
        payment = reservation.create_payment()

        # Refresh from database
        reservation.refresh_from_db()

        # Verify payment was created
        assert payment is not None
        assert payment.amount == Decimal('200.00')  # 2 hours * 100.00
        assert payment.status == 'pending'
        assert reservation.total_price == Decimal('200.00')
        assert reservation.payment == payment

    def test_process_payment(self, setup_data):
        """Test processing a payment for a reservation."""
        data = setup_data

        # Create a reservation
        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['start_time'] + timedelta(hours=2),
            status='pending'
        )

        # Process payment (this should create a payment if it doesn't exist)
        result = reservation.process_payment(
            payment_method='credit_card',
            transaction_id='txn_123456'
        )

        # Refresh from database
        reservation.refresh_from_db()

        # Verify payment was processed
        assert result is True
        assert reservation.payment is not None
        assert reservation.payment.status == 'completed'
        assert reservation.payment.payment_method == 'credit_card'
        assert reservation.payment.transaction_id == 'txn_123456'
        assert reservation.payment.payment_date is not None

    def test_cancel_with_payment_refund(self, setup_data):
        """Test cancelling a reservation with a completed payment."""
        data = setup_data

        # Create a reservation
        reservation = Reservation.objects.create(
            user=data['user'],
            parking_spot=data['sensor'],
            start_time=data['start_time'],
            end_time=data['start_time'] + timedelta(hours=2),
            status='pending'
        )

        # Process payment
        reservation.process_payment()

        # Cancel reservation
        reservation.cancel()

        # Refresh from database
        reservation.refresh_from_db()

        # Verify reservation was cancelled and payment was refunded
        assert reservation.status == 'cancelled'
        assert reservation.payment.status == 'refunded'

@pytest.mark.django_db
class TestPaymentModel:
    """Test the Payment model functionality."""

    @pytest.fixture
    def setup_payment(self):
        """Set up test data for payment tests."""
        payment = Payment.objects.create(
            amount=Decimal('100.00'),
            status='pending'
        )
        return payment

    def test_payment_str_representation(self, setup_payment):
        """Test the string representation of a payment."""
        payment = setup_payment

        expected_str = f"Payment {payment.id}: {payment.amount} ({payment.get_status_display()})"
        assert str(payment) == expected_str

    def test_mark_as_completed(self, setup_payment):
        """Test marking a payment as completed."""
        payment = setup_payment

        payment.mark_as_completed(
            payment_method='credit_card',
            transaction_id='txn_123456'
        )

        # Refresh from database
        payment.refresh_from_db()

        assert payment.status == 'completed'
        assert payment.payment_method == 'credit_card'
        assert payment.transaction_id == 'txn_123456'
        assert payment.payment_date is not None

    def test_mark_as_failed(self, setup_payment):
        """Test marking a payment as failed."""
        payment = setup_payment

        payment.mark_as_failed()

        # Refresh from database
        payment.refresh_from_db()

        assert payment.status == 'failed'

    def test_refund_completed_payment(self, setup_payment):
        """Test refunding a completed payment."""
        payment = setup_payment

        # First mark as completed
        payment.mark_as_completed()

        # Then refund
        result = payment.refund()

        # Refresh from database
        payment.refresh_from_db()

        assert result is True
        assert payment.status == 'refunded'

    def test_refund_non_completed_payment(self, setup_payment):
        """Test that refunding a non-completed payment has no effect."""
        payment = setup_payment

        # Try to refund a pending payment
        result = payment.refund()

        # Refresh from database
        payment.refresh_from_db()

        assert result is False
        assert payment.status == 'pending'  # Status should remain unchanged
