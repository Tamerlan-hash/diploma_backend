import pytest
import uuid
from django.urls import reverse
from rest_framework import status
from sensor.models import ParkingSpot, Sensor, Blocker
from subscriptions.models import TariffZone

@pytest.mark.django_db
class TestSensorOccupyAPI:
    """Test the SensorOccupyAPIView."""

    @pytest.fixture
    def setup_data(self):
        """Set up test data for API tests."""
        # Create a tariff zone
        tariff_zone = TariffZone.objects.create(
            name='Test Tariff Zone',
            description='Test tariff zone for API tests'
        )

        # Create a parking spot
        parking_spot = ParkingSpot.objects.create(
            reference=uuid.uuid4(),
            name='Test Parking Spot',
            tariff_zone=tariff_zone
        )

        # Create a sensor associated with the parking spot
        sensor = Sensor.objects.create(
            reference=uuid.uuid4(),
            parking_spot=parking_spot,
            is_occupied=False
        )

        return {
            'parking_spot': parking_spot,
            'sensor': sensor
        }

    def test_sensor_occupy_success(self, api_client, setup_data):
        """Test successful sensor occupation."""
        data = setup_data
        url = reverse('sensor_occupy', kwargs={'reference': str(data['sensor'].reference)})

        response = api_client.post(url, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_occupied'] is True

        # Verify the sensor was updated in the database
        data['sensor'].refresh_from_db()
        assert data['sensor'].is_occupied is True

    def test_sensor_occupy_invalid_reference(self, api_client):
        """Test sensor occupation with invalid reference."""
        url = reverse('sensor_occupy', kwargs={'reference': str(uuid.uuid4())})  # Random UUID that doesn't exist

        response = api_client.post(url, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND



@pytest.mark.django_db
class TestSensorUnoccupyAPI:
    """Test the SensorUnoccupyAPIView."""

    @pytest.fixture
    def setup_data(self):
        """Set up test data for API tests."""
        # Create a tariff zone
        tariff_zone = TariffZone.objects.create(
            name='Test Tariff Zone',
            description='Test tariff zone for API tests'
        )

        # Create a parking spot
        parking_spot = ParkingSpot.objects.create(
            reference=uuid.uuid4(),
            name='Test Parking Spot',
            tariff_zone=tariff_zone
        )

        # Create a sensor associated with the parking spot
        sensor = Sensor.objects.create(
            reference=uuid.uuid4(),
            parking_spot=parking_spot,
            is_occupied=True
        )

        return {
            'parking_spot': parking_spot,
            'sensor': sensor
        }

    def test_sensor_unoccupy_success(self, api_client, setup_data):
        """Test successful sensor unoccupation."""
        data = setup_data
        url = reverse('sensor_unoccupy', kwargs={'reference': str(data['sensor'].reference)})

        response = api_client.post(url, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_occupied'] is False

        # Verify the sensor was updated in the database
        data['sensor'].refresh_from_db()
        assert data['sensor'].is_occupied is False

    def test_sensor_unoccupy_invalid_reference(self, api_client):
        """Test sensor unoccupation with invalid reference."""
        url = reverse('sensor_unoccupy', kwargs={'reference': str(uuid.uuid4())})  # Random UUID that doesn't exist

        response = api_client.post(url, format='json')

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestBlockerStatusAPI:
    """Test the BlockerStatusAPIView."""

    @pytest.fixture
    def setup_data(self):
        """Set up test data for API tests."""
        # Create a tariff zone
        tariff_zone = TariffZone.objects.create(
            name='Test Tariff Zone',
            description='Test tariff zone for API tests'
        )

        # Create a parking spot
        parking_spot = ParkingSpot.objects.create(
            reference=uuid.uuid4(),
            name='Test Parking Spot',
            tariff_zone=tariff_zone
        )

        # Create a blocker associated with the parking spot
        blocker = Blocker.objects.create(
            reference=uuid.uuid4(),
            parking_spot=parking_spot,
            is_raised=False
        )

        return {
            'parking_spot': parking_spot,
            'blocker': blocker
        }

    def test_blocker_status_success(self, api_client, setup_data):
        """Test successful blocker status retrieval."""
        data = setup_data
        url = reverse('blocker_status', kwargs={'reference': str(data['blocker'].reference)})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['reference'] == str(data['blocker'].reference)
        assert response.data['is_raised'] is False

    def test_blocker_status_invalid_reference(self, api_client):
        """Test blocker status with invalid reference."""
        url = reverse('blocker_status', kwargs={'reference': str(uuid.uuid4())})  # Random UUID that doesn't exist

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
