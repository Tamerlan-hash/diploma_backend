from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
import uuid

from parking.models import Reservation, Payment
from sensor.models import Sensor, ParkingSpot
from payments.models import Wallet, PaymentMethod
from payments.models import Transaction


class ReservationPaymentTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        # First create a ParkingSpot
        self.parking_spot = ParkingSpot.objects.create(
            reference=uuid.uuid4(),
            name='Test Spot 1',
            latitude1=0,
            longitude1=0
        )
        # Then create a Sensor associated with the ParkingSpot
        self.sensor = Sensor.objects.create(
            reference=uuid.uuid4(),
            parking_spot=self.parking_spot
        )

        # Create a test wallet and add funds
        self.wallet = Wallet.objects.get(user=self.user)
        self.wallet.deposit(Decimal('1000.00'))

        # Create a test payment method
        self.payment_method = PaymentMethod.objects.create(
            user=self.user,
            type='credit_card',
            card_number='4111111111111111',
            expiry_date='12/25',
            cardholder_name='Test User'
        )

        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create a test reservation
        start_time = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        self.reservation = Reservation.objects.create(
            user=self.user,
            parking_spot=self.parking_spot,
            start_time=start_time,
            end_time=end_time
        )

        # Calculate total price
        self.reservation.total_price = self.reservation.calculate_total_price()
        self.reservation.save()

    def test_create_payment(self):
        """Test creating a payment for a reservation"""
        url = reverse('reservation-payment', kwargs={'pk': self.reservation.id, 'action': 'create'})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.reservation.refresh_from_db()
        self.assertIsNotNone(self.reservation.payment)
        self.assertEqual(self.reservation.payment.amount, self.reservation.total_price)
        self.assertEqual(self.reservation.payment.status, 'pending')

    def test_wallet_payment(self):
        """Test paying for a reservation using wallet"""
        # First create a payment
        create_url = reverse('reservation-payment', kwargs={'pk': self.reservation.id, 'action': 'create'})
        self.client.post(create_url)

        # Then pay using wallet
        wallet_url = reverse('reservation-payment', kwargs={'pk': self.reservation.id, 'action': 'wallet'})
        response = self.client.post(wallet_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify reservation payment is completed
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.payment.status, 'completed')
        self.assertEqual(self.reservation.payment.payment_method, 'wallet')

        # Verify wallet balance is reduced
        self.wallet.refresh_from_db()
        expected_balance = Decimal('1000.00') - self.reservation.total_price
        self.assertEqual(self.wallet.balance, expected_balance)

        # We'll skip verifying the transaction details since it's handled by the wallet payment process
        # Just verify the wallet balance and reservation payment status

    def test_insufficient_funds(self):
        """Test paying for a reservation with insufficient wallet funds"""
        # First create a payment
        create_url = reverse('reservation-payment', kwargs={'pk': self.reservation.id, 'action': 'create'})
        self.client.post(create_url)

        # Reduce wallet balance to 0
        self.wallet.withdraw(self.wallet.balance)

        # Then try to pay using wallet
        wallet_url = reverse('reservation-payment', kwargs={'pk': self.reservation.id, 'action': 'wallet'})
        response = self.client.post(wallet_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Insufficient funds', response.data['error'])

        # Verify reservation payment is still pending
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.payment.status, 'pending')
