from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
from .models import Reservation
from sensor.models import Sensor
import uuid

class ReservationModelTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create a test sensor (parking spot)
        self.sensor = Sensor.objects.create(
            reference=uuid.uuid4(),
            name='Test Parking Spot',
            is_lock=False
        )
        
        # Set up time variables
        self.now = timezone.now()
        self.start_time = self.now + timedelta(hours=1)
        self.end_time = self.now + timedelta(hours=2)
    
    def test_reservation_creation(self):
        """Test that a reservation can be created with valid data"""
        reservation = Reservation.objects.create(
            user=self.user,
            parking_spot=self.sensor,
            start_time=self.start_time,
            end_time=self.end_time,
            status='pending'
        )
        
        self.assertEqual(reservation.user, self.user)
        self.assertEqual(reservation.parking_spot, self.sensor)
        self.assertEqual(reservation.status, 'pending')
    
    def test_reservation_activation(self):
        """Test that a reservation can be activated"""
        reservation = Reservation.objects.create(
            user=self.user,
            parking_spot=self.sensor,
            start_time=self.start_time,
            end_time=self.end_time,
            status='pending'
        )
        
        reservation.activate()
        
        # Refresh from database
        reservation.refresh_from_db()
        self.sensor.refresh_from_db()
        
        self.assertEqual(reservation.status, 'active')
        self.assertTrue(self.sensor.is_lock)
    
    def test_reservation_completion(self):
        """Test that a reservation can be completed"""
        reservation = Reservation.objects.create(
            user=self.user,
            parking_spot=self.sensor,
            start_time=self.start_time,
            end_time=self.end_time,
            status='active'
        )
        
        # Lock the sensor
        self.sensor.lock()
        
        reservation.complete()
        
        # Refresh from database
        reservation.refresh_from_db()
        self.sensor.refresh_from_db()
        
        self.assertEqual(reservation.status, 'completed')
        self.assertFalse(self.sensor.is_lock)
    
    def test_reservation_cancellation(self):
        """Test that a reservation can be cancelled"""
        reservation = Reservation.objects.create(
            user=self.user,
            parking_spot=self.sensor,
            start_time=self.start_time,
            end_time=self.end_time,
            status='active'
        )
        
        # Lock the sensor
        self.sensor.lock()
        
        reservation.cancel()
        
        # Refresh from database
        reservation.refresh_from_db()
        self.sensor.refresh_from_db()
        
        self.assertEqual(reservation.status, 'cancelled')
        self.assertFalse(self.sensor.is_lock)

class ReservationAPITests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create a test sensor (parking spot)
        self.sensor = Sensor.objects.create(
            reference=uuid.uuid4(),
            name='Test Parking Spot',
            is_lock=False
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
            'parking_spot': self.sensor.reference,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat()
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.count(), 1)
        
        reservation = Reservation.objects.first()
        self.assertEqual(reservation.user, self.user)
        self.assertEqual(reservation.parking_spot, self.sensor)
        self.assertEqual(reservation.status, 'pending')
    
    def test_list_reservations(self):
        """Test listing a user's reservations via the API"""
        # Create some reservations
        Reservation.objects.create(
            user=self.user,
            parking_spot=self.sensor,
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
        # Create a reservation for the test sensor
        Reservation.objects.create(
            user=self.user,
            parking_spot=self.sensor,
            start_time=self.start_time,
            end_time=self.end_time,
            status='pending'
        )
        
        # Create another sensor that should be available
        available_sensor = Sensor.objects.create(
            reference=uuid.uuid4(),
            name='Available Parking Spot',
            is_lock=False
        )
        
        url = '/api/parking/available-spots/'
        params = {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat()
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Only the available sensor should be returned
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['reference'], str(available_sensor.reference))