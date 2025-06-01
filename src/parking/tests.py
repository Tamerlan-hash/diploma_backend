from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
from .models import Reservation, Payment
from sensor.models import Sensor, ParkingSpot, Blocker
import uuid

class ReservationModelTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        # Create a test parking spot
        self.parking_spot = ParkingSpot.objects.create(
            reference=uuid.uuid4(),
            name='Test Parking Spot',
            price_per_hour=100.00
        )

        # Create a test sensor for the parking spot
        self.sensor = Sensor.objects.create(
            reference=uuid.uuid4(),
            parking_spot=self.parking_spot,
            is_occupied=False
        )

        # Create a blocker for the parking spot
        self.blocker = Blocker.objects.create(
            reference=uuid.uuid4(),
            parking_spot=self.parking_spot,
            is_raised=False
        )

        # Set up time variables
        self.now = timezone.now()
        self.start_time = self.now + timedelta(hours=1)
        self.end_time = self.now + timedelta(hours=2)

    def test_reservation_creation(self):
        """Test that a reservation can be created with valid data"""
        reservation = Reservation.objects.create(
            user=self.user,
            parking_spot=self.parking_spot,
            start_time=self.start_time,
            end_time=self.end_time,
            status='pending'
        )

        self.assertEqual(reservation.user, self.user)
        self.assertEqual(reservation.parking_spot, self.parking_spot)
        self.assertEqual(reservation.status, 'pending')

    def test_reservation_activation(self):
        """Test that a reservation can be activated"""
        reservation = Reservation.objects.create(
            user=self.user,
            parking_spot=self.parking_spot,
            start_time=self.start_time,
            end_time=self.end_time,
            status='pending'
        )

        # Create a payment for the reservation
        payment = Payment.objects.create(amount=100.00, status='completed')
        reservation.payment = payment
        reservation.save()

        reservation.activate()

        # Refresh from database
        reservation.refresh_from_db()
        self.blocker.refresh_from_db()

        self.assertEqual(reservation.status, 'active')
        self.assertTrue(self.blocker.is_raised)

    def test_reservation_completion(self):
        """Test that a reservation can be completed"""
        reservation = Reservation.objects.create(
            user=self.user,
            parking_spot=self.parking_spot,
            start_time=self.start_time,
            end_time=self.end_time,
            status='active'
        )

        # Raise the blocker
        self.blocker.raise_blocker()

        reservation.complete()

        # Refresh from database
        reservation.refresh_from_db()
        self.blocker.refresh_from_db()

        self.assertEqual(reservation.status, 'completed')
        self.assertFalse(self.blocker.is_raised)

    def test_reservation_cancellation(self):
        """Test that a reservation can be cancelled"""
        reservation = Reservation.objects.create(
            user=self.user,
            parking_spot=self.parking_spot,
            start_time=self.start_time,
            end_time=self.end_time,
            status='active'
        )

        # Raise the blocker
        self.blocker.raise_blocker()

        reservation.cancel()

        # Refresh from database
        reservation.refresh_from_db()
        self.blocker.refresh_from_db()

        self.assertEqual(reservation.status, 'cancelled')
        self.assertFalse(self.blocker.is_raised)

class ReservationAPITests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        # Create a test parking spot
        self.parking_spot = ParkingSpot.objects.create(
            reference=uuid.uuid4(),
            name='Test Parking Spot',
            price_per_hour=100.00
        )

        # Create a test sensor for the parking spot
        self.sensor = Sensor.objects.create(
            reference=uuid.uuid4(),
            parking_spot=self.parking_spot,
            is_occupied=False
        )

        # Create a blocker for the parking spot
        self.blocker = Blocker.objects.create(
            reference=uuid.uuid4(),
            parking_spot=self.parking_spot,
            is_raised=False
        )

        # Set up time variables
        self.now = timezone.now()
        self.start_time = self.now + timedelta(hours=1)
        self.end_time = self.now + timedelta(hours=2)

        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_reservation(self):
        """Test creating a reservation via the API"""
        url = '/api/parking/reservations/'
        data = {
            'parking_spot': self.parking_spot.reference,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat()
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.count(), 1)

        reservation = Reservation.objects.first()
        self.assertEqual(reservation.user, self.user)
        self.assertEqual(reservation.parking_spot, self.parking_spot)
        self.assertEqual(reservation.status, 'pending')

    def test_list_reservations(self):
        """Test listing a user's reservations via the API"""
        # Create some reservations
        Reservation.objects.create(
            user=self.user,
            parking_spot=self.parking_spot,
            start_time=self.start_time,
            end_time=self.end_time,
            status='pending'
        )

        url = '/api/parking/reservations/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_available_parking_spots(self):
        """Test finding available parking spots via the API"""
        # Create a reservation for the test parking spot
        Reservation.objects.create(
            user=self.user,
            parking_spot=self.parking_spot,
            start_time=self.start_time,
            end_time=self.end_time,
            status='pending'
        )

        # Create another parking spot that should be available
        available_parking_spot = ParkingSpot.objects.create(
            reference=uuid.uuid4(),
            name='Available Parking Spot',
            price_per_hour=100.00
        )

        # Create a sensor for the available parking spot
        available_sensor = Sensor.objects.create(
            reference=uuid.uuid4(),
            parking_spot=available_parking_spot,
            is_occupied=False
        )

        # Create a blocker for the available parking spot
        available_blocker = Blocker.objects.create(
            reference=uuid.uuid4(),
            parking_spot=available_parking_spot,
            is_raised=False
        )

        url = '/api/parking/available-spots/'
        params = {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat()
        }

        response = self.client.get(url, params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Only the available parking spot should be returned
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['reference'], str(available_parking_spot.reference))
