from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s wallet: {self.balance}"

    def deposit(self, amount):
        """Add funds to wallet"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.balance += amount
        self.save()
        return self.balance

    def withdraw(self, amount):
        """Remove funds from wallet"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient funds")
        self.balance -= amount
        self.save()
        return self.balance


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    """Create a wallet for new users"""
    if created:
        Wallet.objects.create(user=instance)


class PaymentMethod(models.Model):
    TYPE_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    card_number = models.CharField(max_length=16)  # Stored securely in production
    expiry_date = models.CharField(max_length=5)  # MM/YY format
    cardholder_name = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.get_type_display()} ending in {self.card_number[-4:]}"

    def save(self, *args, **kwargs):
        # If this payment method is set as default, unset default for all other payment methods of this user
        if self.is_default:
            PaymentMethod.objects.filter(user=self.user, is_default=True).update(is_default=False)

        # If this is the first payment method for the user, set it as default
        if not self.pk and not PaymentMethod.objects.filter(user=self.user).exists():
            self.is_default = True

        super().save(*args, **kwargs)


class Transaction(models.Model):
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
    ]

    TYPE_CHOICES = [
        ('card_payment', 'Card Payment'),
        ('wallet_deposit', 'Wallet Deposit'),
        ('wallet_withdrawal', 'Wallet Withdrawal'),
        ('wallet_payment', 'Wallet Payment'),
        ('wallet_refund', 'Wallet Refund'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    wallet = models.ForeignKey(Wallet, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='card_payment')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reservation_id = models.CharField(max_length=100, blank=True, null=True)  # Optional reference to a reservation
    description = models.TextField(blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)  # External transaction ID
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Transaction {self.id}: {self.amount} ({self.get_status_display()})"

    def mark_as_completed(self, transaction_id=''):
        self.status = 'completed'
        self.transaction_id = transaction_id
        self.save()

    def mark_as_failed(self):
        self.status = 'failed'
        self.save()

    @classmethod
    def create_wallet_deposit(cls, wallet, amount, description='', payment_method=None):
        """Create a wallet deposit transaction"""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        transaction = cls.objects.create(
            user=wallet.user,
            wallet=wallet,
            payment_method=payment_method,
            amount=amount,
            transaction_type='wallet_deposit',
            description=description or 'Deposit to wallet'
        )

        # Mark as completed and update wallet balance
        transaction.mark_as_completed(transaction_id=f"WDEPOSIT-{transaction.id}")
        wallet.deposit(amount)

        return transaction

    @classmethod
    def create_wallet_withdrawal(cls, wallet, amount, description=''):
        """Create a wallet withdrawal transaction"""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if amount > wallet.balance:
            raise ValueError("Insufficient funds")

        transaction = cls.objects.create(
            user=wallet.user,
            wallet=wallet,
            amount=amount,
            transaction_type='wallet_withdrawal',
            description=description or 'Withdrawal from wallet'
        )

        # Mark as completed and update wallet balance
        transaction.mark_as_completed(transaction_id=f"WWITHDRAW-{transaction.id}")
        wallet.withdraw(amount)

        return transaction

    @classmethod
    def create_wallet_payment(cls, wallet, amount, reservation_id=None, description=''):
        """Create a payment using wallet balance"""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if amount > wallet.balance:
            raise ValueError("Insufficient funds")

        transaction = cls.objects.create(
            user=wallet.user,
            wallet=wallet,
            amount=amount,
            transaction_type='wallet_payment',
            reservation_id=reservation_id,
            description=description or 'Payment from wallet'
        )

        # Mark as completed and update wallet balance
        transaction.mark_as_completed(transaction_id=f"WPAYMENT-{transaction.id}")
        wallet.withdraw(amount)

        return transaction

    @classmethod
    def create_wallet_refund(cls, wallet, amount, reservation_id=None, description=''):
        """Create a refund to wallet for a previous payment"""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        transaction = cls.objects.create(
            user=wallet.user,
            wallet=wallet,
            amount=amount,
            transaction_type='wallet_refund',
            reservation_id=reservation_id,
            description=description or 'Refund to wallet'
        )

        # Mark as completed and update wallet balance
        transaction.mark_as_completed(transaction_id=f"WREFUND-{transaction.id}")
        wallet.deposit(amount)

        return transaction
