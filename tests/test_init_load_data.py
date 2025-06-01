import pytest
from django.core.management import call_command
from django.contrib.auth.models import User
from sensor.models import ParkingSpot, Sensor, Blocker
from parking.models import Reservation, Payment
from subscriptions.models import SubscriptionPlan, UserSubscription, TariffZone, TariffRule
from payments.models import Wallet, Transaction
from io import StringIO
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
class TestInitLoadDataCommand:
    """Test the init_load_data management command."""

    def test_command_output(self):
        """Test that the command produces the expected output."""
        # Capture command output
        out = StringIO()
        call_command('init_load_data', stdout=out)
        output = out.getvalue()

        # Check for expected output messages
        assert 'Starting database initialization with test data...' in output
        assert 'Data cleared successfully!' in output
        assert 'Test users created successfully!' in output
        assert 'Test parking spots created successfully!' in output
        assert 'Test subscription plans created successfully!' in output
        assert 'Test tariff zones and rules created successfully!' in output
        assert 'Test user subscriptions created successfully!' in output
        assert 'Test reservations created successfully!' in output
        assert 'Database initialization completed successfully!' in output

    def test_users_created(self):
        """Test that users are created correctly."""
        # Clear existing data
        call_command('init_load_data')

        # Check that users were created
        users = User.objects.filter(is_staff=False)
        assert users.count() >= 5  # At least 5 test users should be created

        # Check specific user
        user1 = User.objects.filter(username='user1').first()
        assert user1 is not None
        assert user1.email == 'user1@example.com'
        assert hasattr(user1, 'profile')
        assert user1.profile.car_number == 'B456DE'
        assert user1.profile.car_model == 'Toyota Camry'

        # Check wallet
        wallet = Wallet.objects.get(user=user1)
        assert wallet is not None
        assert wallet.balance > 0

    def test_parking_spots_created(self):
        """Test that parking spots are created correctly."""
        # Clear existing data
        call_command('init_load_data')

        # Check that parking spots were created
        spots = ParkingSpot.objects.all()
        assert spots.count() >= 10  # At least 10 test spots should be created

        # Check specific spot
        spot_a1 = ParkingSpot.objects.filter(name='Spot A1').first()
        assert spot_a1 is not None
        assert spot_a1.price_per_hour == 100.00

        # Check sensor and blocker
        assert hasattr(spot_a1, 'sensor')
        assert hasattr(spot_a1, 'blocker')

    def test_subscription_plans_created(self):
        """Test that subscription plans are created correctly."""
        # Clear existing data
        call_command('init_load_data')

        # Check that subscription plans were created
        plans = SubscriptionPlan.objects.all()
        assert plans.count() >= 3  # At least 3 test plans should be created

        # Check specific plan
        basic_plan = SubscriptionPlan.objects.filter(name='Basic Plan').first()
        assert basic_plan is not None
        assert basic_plan.price == 500.00
        assert basic_plan.discount_percentage == 10.00
        assert basic_plan.duration_days == 30

    def test_tariff_zones_and_rules_created(self):
        """Test that tariff zones and rules are created correctly."""
        # Clear existing data
        call_command('init_load_data')

        # Check that tariff zones were created
        zones = TariffZone.objects.all()
        assert zones.count() >= 3  # At least 3 test zones should be created

        # Check specific zone
        city_center = TariffZone.objects.filter(name='City Center').first()
        assert city_center is not None

        # Check tariff rules
        rules = TariffRule.objects.all()
        assert rules.count() >= 9  # At least 9 test rules should be created

        # Check specific rule
        weekday_rule = TariffRule.objects.filter(name='City Center - Weekday').first()
        assert weekday_rule is not None
        assert weekday_rule.zone == city_center
        assert weekday_rule.price_per_hour == 200.00

        # Check special spot rules
        special_rules = TariffRule.objects.filter(parking_spot__isnull=False)
        assert special_rules.count() >= 2  # At least 2 special rules should be created

    def test_user_subscriptions_created(self):
        """Test that user subscriptions are created correctly."""
        # Clear existing data
        call_command('init_load_data')

        # Check that user subscriptions were created
        subscriptions = UserSubscription.objects.all()
        assert subscriptions.count() >= 2  # At least 2 test subscriptions should be created

        # Check specific subscription
        user2 = User.objects.filter(username='user2').first()
        user2_subscription = UserSubscription.objects.filter(user=user2).first()
        assert user2_subscription is not None
        assert user2_subscription.plan.name == 'Standard Plan'
        assert user2_subscription.status == 'active'

    def test_reservations_created(self):
        """Test that reservations are created correctly."""
        # Clear existing data
        call_command('init_load_data')

        # Check that reservations were created
        reservations = Reservation.objects.all()
        assert reservations.count() >= 5  # At least 5 test reservations should be created

        # Check active reservations
        active_reservations = Reservation.objects.filter(status='active')
        assert active_reservations.count() >= 3  # At least 3 active reservations should be created

        # Check completed reservations
        completed_reservations = Reservation.objects.filter(status='completed')
        assert completed_reservations.count() >= 2  # At least 2 completed reservations should be created

        # Check payments
        payments = Payment.objects.all()
        assert payments.count() >= 5  # At least 5 payments should be created
