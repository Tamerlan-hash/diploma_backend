from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from sensor.models import Sensor
from decimal import Decimal


class SubscriptionPlan(models.Model):
    """
    Subscription plans available for users to purchase.
    """
    DURATION_CHOICES = [
        (30, '30 дней'),
        (90, '90 дней'),
        (365, '365 дней'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    duration_days = models.IntegerField(choices=DURATION_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_duration_days_display()})"


class UserSubscription(models.Model):
    """
    User's active subscriptions.
    """
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('expired', 'Истекла'),
        ('cancelled', 'Отменена'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    auto_renew = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Payment related fields
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"

    def save(self, *args, **kwargs):
        # Set end_date based on plan duration if not provided
        if not self.end_date:
            self.end_date = self.start_date + timezone.timedelta(days=self.plan.duration_days)
        super().save(*args, **kwargs)

    def is_active(self):
        """Check if subscription is currently active"""
        now = timezone.now()
        return self.status == 'active' and self.start_date <= now <= self.end_date

    def cancel(self):
        """Cancel the subscription"""
        self.status = 'cancelled'
        self.auto_renew = False
        self.save()

    def renew(self):
        """Renew the subscription for another period"""
        if self.status != 'active':
            return False

        # Create a new subscription period
        new_start_date = self.end_date
        new_end_date = new_start_date + timezone.timedelta(days=self.plan.duration_days)

        # Update current subscription
        self.start_date = new_start_date
        self.end_date = new_end_date
        self.save()

        return True


class TariffZone(models.Model):
    """
    Different zones for pricing (city center, suburbs, etc.)
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class TariffRule(models.Model):
    """
    Rules for pricing based on location, time, etc.
    """
    TIME_PERIOD_CHOICES = [
        ('all_day', 'Весь день'),
        ('morning', 'Утро (6:00-12:00)'),
        ('afternoon', 'День (12:00-18:00)'),
        ('evening', 'Вечер (18:00-23:00)'),
        ('night', 'Ночь (23:00-6:00)'),
        ('custom', 'Пользовательский'),
    ]

    DAY_TYPE_CHOICES = [
        ('all', 'Все дни'),
        ('weekday', 'Будние дни'),
        ('weekend', 'Выходные дни'),
        ('holiday', 'Праздничные дни'),
        ('custom', 'Пользовательские дни'),
    ]

    name = models.CharField(max_length=100)
    zone = models.ForeignKey(TariffZone, on_delete=models.CASCADE, related_name='tariff_rules')
    parking_spot = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='tariff_rules', null=True, blank=True)

    # Time period
    time_period = models.CharField(max_length=20, choices=TIME_PERIOD_CHOICES, default='all_day')
    custom_start_time = models.TimeField(null=True, blank=True)
    custom_end_time = models.TimeField(null=True, blank=True)

    # Day type
    day_type = models.CharField(max_length=20, choices=DAY_TYPE_CHOICES, default='all')
    custom_days = models.CharField(max_length=100, blank=True, help_text="Comma-separated list of days (1-7, where 1 is Monday)")

    # Pricing
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)

    # Validity period
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text="Higher priority rules override lower priority ones")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', '-created_at']

    def __str__(self):
        spot_name = self.parking_spot.name if self.parking_spot else "All spots"
        return f"{self.name} - {self.zone.name} - {spot_name} - {self.price_per_hour}"

    def is_applicable(self, datetime_obj):
        """Check if this rule is applicable for the given datetime"""
        # Check validity period
        if self.valid_to and datetime_obj > self.valid_to:
            return False
        if datetime_obj < self.valid_from:
            return False

        # Check day type
        weekday = datetime_obj.weekday()  # 0-6 (Monday is 0)
        if self.day_type == 'weekday' and weekday >= 5:  # 5, 6 are weekend days
            return False
        if self.day_type == 'weekend' and weekday < 5:
            return False
        if self.day_type == 'custom' and str(weekday + 1) not in self.custom_days.split(','):
            return False

        # Check time period
        time_obj = datetime_obj.time()
        if self.time_period == 'morning' and not (time_obj >= timezone.datetime.strptime('06:00', '%H:%M').time() and 
                                                time_obj < timezone.datetime.strptime('12:00', '%H:%M').time()):
            return False
        if self.time_period == 'afternoon' and not (time_obj >= timezone.datetime.strptime('12:00', '%H:%M').time() and 
                                                  time_obj < timezone.datetime.strptime('18:00', '%H:%M').time()):
            return False
        if self.time_period == 'evening' and not (time_obj >= timezone.datetime.strptime('18:00', '%H:%M').time() and 
                                                time_obj < timezone.datetime.strptime('23:00', '%H:%M').time()):
            return False
        if self.time_period == 'night' and not (time_obj >= timezone.datetime.strptime('23:00', '%H:%M').time() or 
                                              time_obj < timezone.datetime.strptime('06:00', '%H:%M').time()):
            return False
        if self.time_period == 'custom' and not (self.custom_start_time <= time_obj < self.custom_end_time):
            return False

        return True


def calculate_price_with_subscription(user, parking_spot, start_time, end_time):
    """
    Calculate the price for a parking spot reservation with subscription discount if applicable.
    """
    # Check if user has active subscription
    active_subscription = UserSubscription.objects.filter(
        user=user,
        status='active',
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    ).first()

    # Get applicable tariff rules
    applicable_rules = []

    # First check for spot-specific rules
    spot_rules = TariffRule.objects.filter(
        parking_spot=parking_spot,
        is_active=True
    )

    # Then check for zone rules
    zone_rules = TariffRule.objects.filter(
        zone__in=TariffZone.objects.filter(is_active=True),
        parking_spot__isnull=True,
        is_active=True
    )

    # Calculate duration in hours
    duration = (end_time - start_time).total_seconds() / 3600

    # Find applicable rules for each hour of the reservation
    current_time = start_time
    total_price = Decimal('0.00')

    while current_time < end_time:
        # First try to find an applicable spot-specific rule
        applicable_rule = None

        # Check spot-specific rules first (they have highest precedence)
        for rule in spot_rules:
            if rule.is_applicable(current_time):
                if applicable_rule is None or rule.priority > applicable_rule.priority:
                    applicable_rule = rule

        # If no spot-specific rule found, check zone rules
        if applicable_rule is None:
            for rule in zone_rules:
                if rule.is_applicable(current_time):
                    if applicable_rule is None or rule.priority > applicable_rule.priority:
                        applicable_rule = rule

        # If no rule found, use default price
        if applicable_rule is None:
            hour_price = Decimal('100.00')  # Default price
        else:
            hour_price = applicable_rule.price_per_hour

        # Apply subscription discount if applicable
        if active_subscription and active_subscription.plan.discount_percentage > 0:
            discount = hour_price * (active_subscription.plan.discount_percentage / Decimal('100.00'))
            hour_price -= discount

        total_price += hour_price

        # Move to next hour
        current_time += timezone.timedelta(hours=1)

        # If we've reached the end time, break
        if current_time >= end_time:
            break

    return total_price
