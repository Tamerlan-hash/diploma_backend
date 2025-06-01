import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
import uuid
from rest_framework import status
from sensor.models import Sensor, ParkingSpot, Blocker
from parking.models import Reservation
from django.conf import settings

pytestmark = pytest.mark.e2e

@pytest.fixture
def create_sensor():
    """Factory to create sensors (parking spots) with specific attributes."""
    def _create_sensor(name="Test Parking Spot", is_lock=False):
        # First create a ParkingSpot
        parking_spot = ParkingSpot.objects.create(
            reference=uuid.uuid4(),
            name=name
        )
        # Then create a Sensor associated with the ParkingSpot
        sensor = Sensor.objects.create(
            reference=uuid.uuid4(),
            parking_spot=parking_spot
        )
        # Create a Blocker if is_lock is True
        if is_lock:
            blocker = Blocker.objects.create(
                parking_spot=parking_spot,
                is_raised=True
            )
        return sensor
    return _create_sensor

@pytest.mark.django_db
class TestParkingSpotAvailableWindows:
    """Test the ParkingSpotAvailableWindowsView."""

    def test_available_windows_timezone(self, auth_client, create_sensor):
        """Test that available windows are generated in the correct timezone (Asia/Almaty)."""
        client, _ = auth_client
        sensor = create_sensor()
        parking_spot = sensor.parking_spot

        # Verify that the timezone setting is correct
        assert settings.TIME_ZONE == 'Asia/Almaty', f"Expected timezone to be 'Asia/Almaty', got '{settings.TIME_ZONE}'"

        # Get the current time in the configured timezone
        now = timezone.now()

        # Format the date for the API request
        date_str = now.strftime('%Y-%m-%d')

        # Make the API request
        url = reverse('parking-spot-available-windows', kwargs={'spot_id': str(parking_spot.reference)})
        response = client.get(f"{url}?date={date_str}")

        assert response.status_code == status.HTTP_200_OK

        # Check that we have windows in the response
        assert len(response.data) > 0, "No available windows returned"

        # The first window should start at the current hour + 1, rounded up to the next hour
        first_window = response.data[0]
        first_window_start = datetime.fromisoformat(first_window['start_time'].replace('Z', '+00:00'))

        # Convert to aware datetime in the same timezone as now
        first_window_start = timezone.make_aware(first_window_start.replace(tzinfo=None))

        # Expected start time: current time + 1 hour, rounded up to the next hour
        expected_start = now + timedelta(hours=1)
        if expected_start.minute > 0 or expected_start.second > 0:
            expected_start = expected_start.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            expected_start = expected_start.replace(minute=0, second=0, microsecond=0)

        # Allow a small tolerance for time differences during test execution
        time_difference = abs((first_window_start - expected_start).total_seconds())
        assert time_difference < 10, f"First window start time {first_window_start} differs from expected {expected_start} by {time_difference} seconds"

    def test_available_windows_past_slots_blocked(self, auth_client, create_sensor):
        """Test that time slots in the past are not included in available windows."""
        client, _ = auth_client
        sensor = create_sensor()
        parking_spot = sensor.parking_spot

        # Get the current time in the configured timezone
        now = timezone.now()

        # Format the date for the API request
        date_str = now.strftime('%Y-%m-%d')

        # Make the API request
        url = reverse('parking-spot-available-windows', kwargs={'spot_id': str(parking_spot.reference)})
        response = client.get(f"{url}?date={date_str}")

        assert response.status_code == status.HTTP_200_OK

        # Check that all windows start in the future
        for window in response.data:
            window_start = datetime.fromisoformat(window['start_time'].replace('Z', '+00:00'))
            window_start = timezone.make_aware(window_start.replace(tzinfo=None))
            assert window_start > now, f"Window start time {window_start} is not after current time {now}"

    def test_available_windows_with_reservation(self, auth_client, create_sensor):
        """Test that time slots with existing reservations are marked as blocked."""
        client, user = auth_client
        sensor = create_sensor()
        parking_spot = sensor.parking_spot

        # Get the current time in the configured timezone
        now = timezone.now()

        # Create a reservation for 2 hours from now
        start_time = now + timedelta(hours=2)
        start_time = start_time.replace(minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)

        Reservation.objects.create(
            user=user,
            parking_spot=parking_spot,
            start_time=start_time,
            end_time=end_time,
            status='active'
        )

        # Format the date for the API request
        date_str = now.strftime('%Y-%m-%d')

        # Make the API request
        url = reverse('parking-spot-available-windows', kwargs={'spot_id': str(parking_spot.reference)})
        response = client.get(f"{url}?date={date_str}")

        assert response.status_code == status.HTTP_200_OK

        # Find the window that corresponds to our reservation
        reserved_window = None
        for window in response.data:
            window_start = datetime.fromisoformat(window['start_time'].replace('Z', '+00:00'))
            window_start = timezone.make_aware(window_start.replace(tzinfo=None))

            if window_start == start_time:
                reserved_window = window
                break

        assert reserved_window is not None, f"Could not find window starting at {start_time} in response"
        assert reserved_window['status'] == 'blocked', f"Expected window status to be 'blocked', got '{reserved_window['status']}'"
        assert reserved_window['reason'] == 'already_booked', f"Expected window reason to be 'already_booked', got '{reserved_window['reason']}'"

    def test_available_windows_different_date(self, auth_client, create_sensor):
        """Test that available windows for a different date start from the beginning of the day."""
        client, _ = auth_client
        sensor = create_sensor()
        parking_spot = sensor.parking_spot

        # Get the current time in the configured timezone
        now = timezone.now()

        # Use tomorrow's date
        tomorrow = (now + timedelta(days=1)).date()
        date_str = tomorrow.strftime('%Y-%m-%d')

        # Make the API request
        url = reverse('parking-spot-available-windows', kwargs={'spot_id': str(parking_spot.reference)})
        response = client.get(f"{url}?date={date_str}")

        assert response.status_code == status.HTTP_200_OK

        # Check that we have windows in the response
        assert len(response.data) > 0, "No available windows returned"

        # The first window should start at the beginning of the day (00:00)
        first_window = response.data[0]
        first_window_start = datetime.fromisoformat(first_window['start_time'].replace('Z', '+00:00'))

        # Convert to aware datetime in the same timezone as now
        first_window_start = timezone.make_aware(first_window_start.replace(tzinfo=None))

        # For a future date, the first window should start at 00:00
        expected_start = timezone.make_aware(datetime.combine(tomorrow, datetime.min.time()))

        # Check that the first window starts at 00:00
        assert first_window_start.hour == 0, f"Expected first window to start at 00:00, got {first_window_start.hour}:{first_window_start.minute}"
        assert first_window_start.minute == 0, f"Expected first window to start at 00:00, got {first_window_start.hour}:{first_window_start.minute}"

        # The date should be tomorrow
        assert first_window_start.date() == tomorrow, f"Expected window date to be {tomorrow}, got {first_window_start.date()}"
