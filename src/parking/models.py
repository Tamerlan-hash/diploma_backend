from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import uuid
from payments.models import Transaction
from sensor.models import ParkingSpot, Blocker

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

    class Meta:
        app_label = 'parking'

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
                    from payments.models import Wallet
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

    PAYMENT_METHOD_CHOICES = [
        ('card', 'Банковская карта'),
        ('wallet', 'Кошелек'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    parking_spot = models.ForeignKey(ParkingSpot, on_delete=models.CASCADE, related_name='reservations')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Hourly booking fields
    selected_hours = models.JSONField(default=list, blank=True, help_text="List of selected hour slots in ISO format")

    # Payment related fields
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservation')
    payment_method_type = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)

    # User arrival tracking
    user_arrived = models.BooleanField(default=False)
    arrival_time = models.DateTimeField(null=True, blank=True)

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
        # Only activate if status is pending and payment is completed
        if self.status == 'pending':
            # Check if payment exists and is completed
            if not self.payment or self.payment.status != 'completed':
                raise ValueError("Cannot activate reservation: payment is not completed")

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
        """Calculate the total price based on selected hours and tariff rules"""
        if not self.selected_hours and (not self.start_time or not self.end_time):
            return Decimal('0.00')

        from subscriptions.models import calculate_price_with_subscription

        # If we have selected hours, calculate price based on those
        if self.selected_hours:
            total = Decimal('0.00')
            for hour_slot in self.selected_hours:
                start = timezone.datetime.fromisoformat(hour_slot['start'])
                end = timezone.datetime.fromisoformat(hour_slot['end'])
                slot_price = calculate_price_with_subscription(self.user, self.parking_spot, start, end)
                total += slot_price
            return total
        else:
            # Fall back to the old calculation method
            total = calculate_price_with_subscription(self.user, self.parking_spot, self.start_time, self.end_time)
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

    def process_card_payment(self, payment_method_id):
        """Process payment using a credit/debit card"""
        from payments.models import PaymentMethod, Transaction

        if not self.payment:
            self.create_payment()

        try:
            # Get the payment method
            payment_method = PaymentMethod.objects.get(id=payment_method_id, user=self.user)

            # Create a card payment transaction
            transaction = Transaction.create_card_payment(
                user=self.user,
                payment_method=payment_method,
                amount=self.total_price,
                reservation_id=str(self.id),
                description=f'Payment for reservation #{self.id}'
            )

            # Mark the payment as completed
            self.payment.mark_as_completed('card', transaction.transaction_id)
            self.payment_method_type = 'card'
            self.save(update_fields=['payment_method_type'])

            # Activate the reservation
            self.activate()

            return True
        except PaymentMethod.DoesNotExist:
            raise ValueError("Invalid payment method")
        except Exception as e:
            # Log the error
            print(f"Error processing card payment: {e}")
            self.payment.mark_as_failed()
            return False

    def process_wallet_payment(self):
        """Process payment using wallet balance"""
        from payments.models import Wallet, Transaction

        if not self.payment:
            self.create_payment()

        try:
            # Get the user's wallet
            wallet = Wallet.objects.get(user=self.user)

            # Create a wallet payment transaction
            transaction = Transaction.create_wallet_payment(
                wallet=wallet,
                amount=self.total_price,
                reservation_id=str(self.id),
                description=f'Payment for reservation #{self.id}'
            )

            # Mark the payment as completed
            self.payment.mark_as_completed('wallet', transaction.transaction_id)
            self.payment_method_type = 'wallet'
            self.save(update_fields=['payment_method_type'])

            # Activate the reservation
            self.activate()

            return True
        except Wallet.DoesNotExist:
            raise ValueError("User wallet not found")
        except ValueError as e:
            # This will catch "Insufficient funds" errors
            print(f"Error processing wallet payment: {e}")
            self.payment.mark_as_failed()
            return False
        except Exception as e:
            # Log the error
            print(f"Error processing wallet payment: {e}")
            self.payment.mark_as_failed()
            return False

    def user_arrive(self):
        """Called when user arrives at the parking spot"""
        from django.utils import timezone

        if self.status != 'active':
            raise ValueError("Reservation is not active")

        # Lower the blocker to let the user in
        try:
            self.parking_spot.blocker.lower_blocker()
            self.user_arrived = True
            self.arrival_time = timezone.now()
            self.save(update_fields=['user_arrived', 'arrival_time'])

            # Create a notification
            try:
                from notifications.models import Notification
                Notification.create_notification(
                    user=self.user,
                    notification_type='payment_successful',
                    title="Welcome to Your Parking Spot",
                    message=f"You have successfully arrived at parking spot {self.parking_spot.name}. Enjoy your stay!",
                    reservation_id=str(self.id)
                )
            except Exception as e:
                print(f"Error creating arrival notification: {e}")

            return True
        except Exception as e:
            print(f"Error lowering blocker: {e}")
            return False

    def extend_reservation(self, additional_hours=1):
        """Extend the reservation by the specified number of hours"""
        from django.utils import timezone
        from datetime import timedelta

        if self.status != 'active':
            raise ValueError("Only active reservations can be extended")

        now = timezone.now()
        if now > self.end_time:
            raise ValueError("Reservation has already ended")

        # Check if the spot is available for the extended time
        extended_end_time = self.end_time + timedelta(hours=additional_hours)

        # Check if there's another reservation for this spot that would overlap
        next_reservation = self.parking_spot.reservations.filter(
            start_time__lt=extended_end_time,
            end_time__gt=self.end_time,
            status__in=['pending', 'active']
        ).exclude(id=self.id).first()

        if next_reservation:
            raise ValueError("Cannot extend reservation: spot is already reserved")

        # Calculate additional price
        from subscriptions.models import calculate_price_with_subscription
        additional_price = calculate_price_with_subscription(
            self.user, 
            self.parking_spot, 
            self.end_time, 
            extended_end_time
        )

        # Update the reservation
        original_end_time = self.end_time
        self.end_time = extended_end_time
        self.total_price = self.total_price + additional_price
        self.save(update_fields=['end_time', 'total_price'])

        # Create a payment for the extension
        extension_payment = Payment.objects.create(amount=additional_price)

        # Process the payment based on the original payment method
        if self.payment_method_type == 'card':
            # Find the user's default payment method
            from payments.models import PaymentMethod
            payment_method = PaymentMethod.objects.filter(user=self.user, is_default=True).first()
            if payment_method:
                from payments.models import Transaction
                transaction = Transaction.create_card_payment(
                    user=self.user,
                    payment_method=payment_method,
                    amount=additional_price,
                    reservation_id=str(self.id),
                    description=f'Extension payment for reservation #{self.id}'
                )
                extension_payment.mark_as_completed('card', transaction.transaction_id)
            else:
                raise ValueError("No default payment method found")
        elif self.payment_method_type == 'wallet':
            from payments.models import Wallet, Transaction
            wallet = Wallet.objects.get(user=self.user)
            transaction = Transaction.create_wallet_payment(
                wallet=wallet,
                amount=additional_price,
                reservation_id=str(self.id),
                description=f'Extension payment for reservation #{self.id}'
            )
            extension_payment.mark_as_completed('wallet', transaction.transaction_id)

        # Create a notification
        try:
            from notifications.models import Notification
            Notification.create_notification(
                user=self.user,
                notification_type='reservation_extended',
                title="Reservation Extended",
                message=f"Your reservation for parking spot {self.parking_spot.name} has been extended until {extended_end_time.strftime('%Y-%m-%d %H:%M')}.",
                reservation_id=str(self.id)
            )
        except Exception as e:
            print(f"Error creating extension notification: {e}")

        return True

    def check_expiration_and_notify(self, minutes_before=30):
        """Check if the reservation is about to expire and send a notification if needed"""
        from django.utils import timezone
        from datetime import timedelta

        if self.status != 'active':
            return False

        now = timezone.now()
        expiration_threshold = self.end_time - timedelta(minutes=minutes_before)

        if now >= expiration_threshold and now < self.end_time:
            # Reservation is about to expire
            try:
                from notifications.models import Notification
                Notification.create_reservation_expiring_notification(self, minutes_before)
                return True
            except Exception as e:
                print(f"Error creating expiration notification: {e}")
                return False

        return False
