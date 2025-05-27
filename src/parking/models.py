from django.db import models
from django.contrib.auth.models import User
from sensor.models import ParkingSpot, Blocker
from django.utils import timezone
from decimal import Decimal

class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Ожидание оплаты'),
        ('completed', 'Оплачено'),
        ('failed', 'Ошибка оплаты'),
        ('refunded', 'Возвращено'),
    ]

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.id}: {self.amount} ({self.get_status_display()})"

    def mark_as_completed(self, payment_method='', transaction_id=''):
        self.status = 'completed'
        self.payment_date = timezone.now()
        self.payment_method = payment_method
        self.transaction_id = transaction_id
        self.save()

    def mark_as_failed(self):
        self.status = 'failed'
        self.save()

    def refund(self):
        if self.status == 'completed':
            self.status = 'refunded'
            self.save()

            # If payment was made using wallet, refund to wallet
            if self.payment_method == 'wallet':
                try:
                    from payments.models import Transaction, Wallet
                    # Find the user's wallet
                    wallet = Wallet.objects.get(user=self.reservation.user)
                    # Create a refund transaction
                    Transaction.create_wallet_refund(
                        wallet=wallet,
                        amount=self.amount,
                        reservation_id=str(self.reservation.id),
                        description=f'Refund for reservation #{self.reservation.id}'
                    )
                except Exception as e:
                    # Log the error but don't prevent the refund status update
                    print(f"Error processing wallet refund: {e}")

            return True
        return False

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидание'),
        ('active', 'Активно'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    parking_spot = models.ForeignKey(ParkingSpot, on_delete=models.CASCADE, related_name='reservations')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Payment related fields
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservation')

    class Meta:
        ordering = ['-created_at']
        # Ensure a parking spot can't be double-booked
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_time__gt=models.F('start_time')),
                name='end_time_after_start_time'
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.parking_spot.name} ({self.start_time} to {self.end_time})"

    def is_active(self):
        now = timezone.now()
        return self.status == 'active' and self.start_time <= now <= self.end_time

    def activate(self):
        if self.status == 'pending':
            self.status = 'active'
            # Raise the blocker when the reservation becomes active
            try:
                self.parking_spot.blocker.raise_blocker()
            except Exception as e:
                print(f"Error raising blocker: {e}")
            self.save()

    def complete(self):
        if self.status == 'active':
            self.status = 'completed'
            # Lower the blocker when the reservation is completed
            try:
                self.parking_spot.blocker.lower_blocker()
            except Exception as e:
                print(f"Error lowering blocker: {e}")
            self.save()

    def cancel(self):
        if self.status in ['pending', 'active']:
            original_status = self.status
            self.status = 'cancelled'
            if original_status == 'active':
                # Lower the blocker when an active reservation is cancelled
                try:
                    self.parking_spot.blocker.lower_blocker()
                except Exception as e:
                    print(f"Error lowering blocker: {e}")

            # Refund payment if it exists and is completed
            if self.payment and self.payment.status == 'completed':
                self.payment.refund()

            self.save()

    def calculate_total_price(self):
        """Calculate the total price based on reservation duration and hourly rate"""
        if not self.start_time or not self.end_time:
            return Decimal('0.00')

        try:
            # Try to use tariff-based pricing with subscription discount
            from subscriptions.models import calculate_price_with_subscription
            total = calculate_price_with_subscription(self.user, self.parking_spot, self.start_time, self.end_time)
            return total
        except (ImportError, Exception) as e:
            # Fallback to simple calculation if tariff functionality is not available
            print(f"Error using tariff-based pricing: {e}")

            # Calculate duration in hours
            duration = (self.end_time - self.start_time).total_seconds() / 3600
            # Round up to the nearest hour
            duration_hours = Decimal(str(duration)).quantize(Decimal('1.'), rounding='ROUND_UP')

            # Calculate total price using the parking spot's price_per_hour
            total = self.parking_spot.price_per_hour * duration_hours
            return total

    def create_payment(self):
        """Create a payment for this reservation"""
        if not self.total_price:
            self.total_price = self.calculate_total_price()
            self.save(update_fields=['total_price'])

        # Create payment if it doesn't exist
        if not self.payment:
            payment = Payment.objects.create(amount=self.total_price)
            self.payment = payment
            self.save(update_fields=['payment'])

        return self.payment

    def process_payment(self, payment_method='', transaction_id=''):
        """Process payment for this reservation"""
        if not self.payment:
            self.create_payment()

        self.payment.mark_as_completed(payment_method, transaction_id)
        # Activate the reservation after payment is completed
        self.activate()
        return True
