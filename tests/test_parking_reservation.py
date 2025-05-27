import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import uuid
from rest_framework import status
from sensor.models import Sensor
from parking.models import Reservation

pytestmark = pytest.mark.e2e

@pytest.fixture
def create_sensor():
    """Factory to create sensors (parking spots) with specific attributes."""
    def _create_sensor(name="Test Parking Spot", is_lock=False):
        return Sensor.objects.create(
            reference=uuid.uuid4(),
            name=name,
            is_lock=is_lock
        )
    return _create_sensor

@pytest.fixture
def create_reservation(auth_client, create_sensor):
    """Factory to create reservations with specific attributes."""
    client, user = auth_client

    def _create_reservation(
        parking_spot=None,
        start_time=None,
        end_time=None,
        status='pending'
    ):
        if parking_spot is None:
            parking_spot = create_sensor()

        now = timezone.now()
        if start_time is None:
            start_time = now + timedelta(hours=1)
        if end_time is None:
            end_time = now + timedelta(hours=2)

        reservation = Reservation.objects.create(
            user=user,
            parking_spot=parking_spot,
            start_time=start_time,
            end_time=end_time,
            status=status
        )

        return reservation, parking_spot

    return _create_reservation

@pytest.mark.django_db
class TestReservationCreation:
    """Test creating reservations through the API."""

    def test_create_reservation_success(self, auth_client, create_sensor):
        """Test that a user can successfully create a reservation."""
        client, _ = auth_client
        sensor = create_sensor()

        now = timezone.now()
        start_time = now + timedelta(hours=1)
        end_time = now + timedelta(hours=2)

        url = reverse('reservation-list-create')
        data = {
            'parking_spot': sensor.reference,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }

        response = client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert Reservation.objects.count() == 1

        reservation = Reservation.objects.first()
        assert reservation.status == 'pending'
        assert reservation.parking_spot == sensor

    def test_create_reservation_past_start_time(self, auth_client, create_sensor):
        """Test that creating a reservation with a past start time fails."""
        client, _ = auth_client
        sensor = create_sensor()

        now = timezone.now()
        start_time = now - timedelta(hours=1)  # Past time
        end_time = now + timedelta(hours=1)

        url = reverse('reservation-list-create')
        data = {
            'parking_spot': sensor.reference,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }

        response = client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Start time cannot be in the past" in str(response.data)

    def test_create_reservation_end_before_start(self, auth_client, create_sensor):
        """Test that creating a reservation with end time before start time fails."""
        client, _ = auth_client
        sensor = create_sensor()

        now = timezone.now()
        start_time = now + timedelta(hours=2)
        end_time = now + timedelta(hours=1)  # Before start time

        url = reverse('reservation-list-create')
        data = {
            'parking_spot': sensor.reference,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }

        response = client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "End time must be after start time" in str(response.data)

    def test_create_reservation_overlapping(self, auth_client, create_sensor, create_reservation):
        """Test that creating an overlapping reservation fails."""
        client, _ = auth_client
        sensor = create_sensor()

        # Create an existing reservation
        now = timezone.now()
        existing_start = now + timedelta(hours=1)
        existing_end = now + timedelta(hours=3)

        create_reservation(
            parking_spot=sensor,
            start_time=existing_start,
            end_time=existing_end
        )

        # Try to create an overlapping reservation
        new_start = now + timedelta(hours=2)  # Within existing reservation
        new_end = now + timedelta(hours=4)

        url = reverse('reservation-list-create')
        data = {
            'parking_spot': sensor.reference,
            'start_time': new_start.isoformat(),
            'end_time': new_end.isoformat()
        }

        response = client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already reserved" in str(response.data)

@pytest.mark.django_db
class TestReservationActions:
    """Test reservation actions (activate, complete, cancel)."""

    def test_activate_reservation(self, auth_client, create_reservation):
        """Test that a user can activate their reservation."""
        client, _ = auth_client
        reservation, sensor = create_reservation(status='pending')

        url = reverse('reservation-action', kwargs={'pk': reservation.id, 'action': 'activate'})
        response = client.post(url)

        assert response.status_code == status.HTTP_200_OK

        # Refresh from database
        reservation.refresh_from_db()
        sensor.refresh_from_db()

        assert reservation.status == 'active'
        assert sensor.is_lock is True

    def test_complete_reservation(self, auth_client, create_reservation):
        """Test that a user can complete their active reservation."""
        client, _ = auth_client
        reservation, sensor = create_reservation(status='active')

        # Lock the sensor
        sensor.lock()

        url = reverse('reservation-action', kwargs={'pk': reservation.id, 'action': 'complete'})
        response = client.post(url)

        assert response.status_code == status.HTTP_200_OK

        # Refresh from database
        reservation.refresh_from_db()
        sensor.refresh_from_db()

        assert reservation.status == 'completed'
        assert sensor.is_lock is False

    def test_cancel_reservation(self, auth_client, create_reservation):
        """Test that a user can cancel their reservation."""
        client, _ = auth_client
        reservation, sensor = create_reservation(status='pending')

        url = reverse('reservation-action', kwargs={'pk': reservation.id, 'action': 'cancel'})
        response = client.post(url)

        assert response.status_code == status.HTTP_200_OK

        # Refresh from database
        reservation.refresh_from_db()

        assert reservation.status == 'cancelled'

    def test_invalid_action(self, auth_client, create_reservation):
        """Test that an invalid action returns an error."""
        client, _ = auth_client
        reservation, _ = create_reservation()

        url = reverse('reservation-action', kwargs={'pk': reservation.id, 'action': 'invalid'})
        response = client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid action" in str(response.data)

@pytest.mark.django_db
class TestUserReservations:
    """Test listing user reservations with filtering."""

    def test_list_user_reservations(self, auth_client, create_reservation):
        """Test that a user can list their reservations."""
        client, _ = auth_client

        # Create reservations with different statuses
        create_reservation(status='pending')
        create_reservation(status='active')
        create_reservation(status='completed')

        url = reverse('user-reservations')
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

    def test_filter_reservations_by_status(self, auth_client, create_reservation):
        """Test that reservations can be filtered by status."""
        client, _ = auth_client

        # Create reservations with different statuses
        create_reservation(status='pending')
        create_reservation(status='active')
        create_reservation(status='completed')

        # Filter by active status
        url = reverse('user-reservations')
        response = client.get(f"{url}?status=active")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['status'] == 'active'

@pytest.mark.django_db
class TestAvailableParkingSpots:
    """Test finding available parking spots."""

    def test_available_spots_with_no_reservations(self, auth_client, create_sensor):
        """Test finding available spots when there are no reservations."""
        client, _ = auth_client

        # Create some sensors
        sensor1 = create_sensor(name="Spot 1")
        sensor2 = create_sensor(name="Spot 2")

        now = timezone.now()
        start_time = now + timedelta(hours=1)
        end_time = now + timedelta(hours=2)

        url = reverse('available-parking-spots')
        # Format datetime in a way that Django's parse_datetime can handle
        formatted_start = start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        formatted_end = end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        response = client.get(
            f"{url}?start_time={formatted_start}&end_time={formatted_end}"
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_available_spots_with_reservations(self, auth_client, create_sensor, create_reservation):
        """Test finding available spots when some are reserved."""
        client, _ = auth_client

        # Create some sensors
        sensor1 = create_sensor(name="Spot 1")
        sensor2 = create_sensor(name="Spot 2")

        now = timezone.now()
        start_time = now + timedelta(hours=1)
        end_time = now + timedelta(hours=2)

        # Reserve sensor1
        create_reservation(
            parking_spot=sensor1,
            start_time=start_time,
            end_time=end_time
        )

        url = reverse('available-parking-spots')
        # Format datetime in a way that Django's parse_datetime can handle
        formatted_start = start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        formatted_end = end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        response = client.get(
            f"{url}?start_time={formatted_start}&end_time={formatted_end}"
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['name'] == "Spot 2"

    def test_available_spots_invalid_times(self, auth_client):
        """Test that invalid time parameters return an error."""
        client, _ = auth_client

        now = timezone.now()
        start_time = now + timedelta(hours=2)
        end_time = now + timedelta(hours=1)  # Before start time

        url = reverse('available-parking-spots')
        # Format datetime in a way that Django's parse_datetime can handle
        formatted_start = start_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        formatted_end = end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        response = client.get(
            f"{url}?start_time={formatted_start}&end_time={formatted_end}"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "End time must be after start time" in str(response.data)

@pytest.mark.django_db
class TestReservationPayment:
    """Test payment operations for reservations."""

    def test_create_payment(self, auth_client, create_reservation):
        """Test creating a payment for a reservation."""
        client, _ = auth_client
        reservation, _ = create_reservation()

        url = reverse('reservation-payment', kwargs={'pk': reservation.id, 'action': 'create'})
        response = client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'amount' in response.data
        assert 'status' in response.data
        assert response.data['status'] == 'pending'

        # Verify reservation has payment in database
        reservation.refresh_from_db()
        assert reservation.payment is not None
        assert reservation.total_price is not None

    def test_process_payment(self, auth_client, create_reservation):
        """Test processing a payment for a reservation."""
        client, _ = auth_client
        reservation, _ = create_reservation()

        # First create the payment
        create_url = reverse('reservation-payment', kwargs={'pk': reservation.id, 'action': 'create'})
        client.post(create_url)

        # Then process the payment
        process_url = reverse('reservation-payment', kwargs={'pk': reservation.id, 'action': 'process'})
        payment_data = {
            'payment_method': 'credit_card',
            'transaction_id': 'txn_123456'
        }
        response = client.post(process_url, payment_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'completed'
        assert response.data['payment_method'] == 'credit_card'
        assert response.data['transaction_id'] == 'txn_123456'

        # Verify payment status in database
        reservation.refresh_from_db()
        assert reservation.payment.status == 'completed'

    def test_process_payment_without_creating_first(self, auth_client, create_reservation):
        """Test that processing a payment without creating it first returns an error."""
        client, _ = auth_client
        reservation, _ = create_reservation()

        # Try to process payment without creating it first
        process_url = reverse('reservation-payment', kwargs={'pk': reservation.id, 'action': 'process'})
        response = client.post(process_url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Payment not created yet" in str(response.data)

    def test_process_payment_already_completed(self, auth_client, create_reservation):
        """Test that processing an already completed payment returns an error."""
        client, _ = auth_client
        reservation, _ = create_reservation()

        # Create and process the payment
        create_url = reverse('reservation-payment', kwargs={'pk': reservation.id, 'action': 'create'})
        client.post(create_url)

        process_url = reverse('reservation-payment', kwargs={'pk': reservation.id, 'action': 'process'})
        client.post(process_url)

        # Try to process it again
        response = client.post(process_url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Payment already completed" in str(response.data)

    def test_invalid_payment_action(self, auth_client, create_reservation):
        """Test that an invalid payment action returns an error."""
        client, _ = auth_client
        reservation, _ = create_reservation()

        url = reverse('reservation-payment', kwargs={'pk': reservation.id, 'action': 'invalid'})
        response = client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid action" in str(response.data)

    def test_cancel_reservation_with_payment(self, auth_client, create_reservation):
        """Test that cancelling a reservation with a payment refunds the payment."""
        client, _ = auth_client
        reservation, _ = create_reservation()

        # Create and process the payment
        create_url = reverse('reservation-payment', kwargs={'pk': reservation.id, 'action': 'create'})
        client.post(create_url)

        process_url = reverse('reservation-payment', kwargs={'pk': reservation.id, 'action': 'process'})
        client.post(process_url)

        # Cancel the reservation
        cancel_url = reverse('reservation-action', kwargs={'pk': reservation.id, 'action': 'cancel'})
        response = client.post(cancel_url)

        assert response.status_code == status.HTTP_200_OK

        # Verify reservation is cancelled and payment is refunded
        reservation.refresh_from_db()
        assert reservation.status == 'cancelled'
        assert reservation.payment.status == 'refunded'
