import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from users.models import UserProfile
from sensor.models import ParkingSpot, Sensor, Blocker
from parking.models import Payment, Reservation
from payments.models import Wallet, PaymentMethod, Transaction
from subscriptions.models import SubscriptionPlan, UserSubscription, TariffZone, TariffRule


class Command(BaseCommand):
    help = 'Initialize database with test data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting database initialization with test data...'))

        # Clear existing data (optional, comment out if you don't want to clear data)
        self.clear_data()

        # Create test data
        self.create_users()
        self.create_subscription_plans()
        self.create_tariff_zones_and_rules()
        self.create_parking_spots()
        self.create_special_tariff_rules()
        self.create_user_subscriptions()
        self.create_reservations()

        self.stdout.write(self.style.SUCCESS('Database initialization completed successfully!'))

    def clear_data(self):
        """Clear existing data from the database"""
        self.stdout.write('Clearing existing data...')

        # Delete in reverse order of dependencies
        try:
            Reservation.objects.all().delete()
            Payment.objects.all().delete()
            UserSubscription.objects.all().delete()
            TariffRule.objects.all().delete()
            Blocker.objects.all().delete()
            Sensor.objects.all().delete()
            ParkingSpot.objects.all().delete()
            # Skip TariffZone deletion due to database schema issue
            # TariffZone.objects.all().delete()
            SubscriptionPlan.objects.all().delete()
            Transaction.objects.all().delete()
            PaymentMethod.objects.all().delete()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Error during data clearing: {e}'))
            self.stdout.write(self.style.WARNING('Continuing with initialization...'))

        # Delete users, profiles, and wallets
        UserProfile.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()  # Delete regular users but keep superusers
        Wallet.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('Data cleared successfully!'))

    def create_users(self):
        """Create test users with profiles and wallets"""
        self.stdout.write('Creating test users...')

        # Create admin user if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='adminpassword'
            )
            UserProfile.objects.create(
                user=admin_user,
                car_number='A123BC',
                car_model='Admin Car'
            )
            # Wallet is created automatically by signal
            admin_wallet = Wallet.objects.get(user=admin_user)
            admin_wallet.deposit(Decimal('10000.00'))

            self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin_user.username}'))

        # Create regular test users
        test_users_data = [
            {
                'username': 'user1',
                'email': 'user1@example.com',
                'password': 'userpassword',
                'first_name': 'John',
                'last_name': 'Doe',
                'car_number': 'B456DE',
                'car_model': 'Toyota Camry',
                'initial_balance': Decimal('5000.00')
            },
            {
                'username': 'user2',
                'email': 'user2@example.com',
                'password': 'userpassword',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'car_number': 'C789FG',
                'car_model': 'Honda Civic',
                'initial_balance': Decimal('3000.00')
            },
            {
                'username': 'user3',
                'email': 'user3@example.com',
                'password': 'userpassword',
                'first_name': 'Bob',
                'last_name': 'Johnson',
                'car_number': 'D012HI',
                'car_model': 'Ford Focus',
                'initial_balance': Decimal('2000.00')
            },
            {
                'username': 'user4',
                'email': 'user4@example.com',
                'password': 'userpassword',
                'first_name': 'Alice',
                'last_name': 'Williams',
                'car_number': 'E345JK',
                'car_model': 'Nissan Altima',
                'initial_balance': Decimal('1500.00')
            },
            {
                'username': 'user5',
                'email': 'user5@example.com',
                'password': 'userpassword',
                'first_name': 'Charlie',
                'last_name': 'Brown',
                'car_number': 'F678LM',
                'car_model': 'Chevrolet Malibu',
                'initial_balance': Decimal('1000.00')
            },
        ]

        for user_data in test_users_data:
            if not User.objects.filter(username=user_data['username']).exists():
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name']
                )

                UserProfile.objects.create(
                    user=user,
                    car_number=user_data['car_number'],
                    car_model=user_data['car_model']
                )

                # Wallet is created automatically by signal
                wallet = Wallet.objects.get(user=user)
                wallet.deposit(user_data['initial_balance'])

                # Create payment methods for users
                card_types = ['credit_card', 'debit_card']
                for i in range(1, 3):  # Create 2 payment methods per user
                    PaymentMethod.objects.create(
                        user=user,
                        type=random.choice(card_types),
                        card_number=f'411111{i:02d}{user.id % 100:02d}111111',
                        expiry_date=f'12/2{i+5}',
                        cardholder_name=f'{user.first_name} {user.last_name}',
                        is_default=(i == 1)  # First card is default
                    )

                self.stdout.write(self.style.SUCCESS(f'Created user: {user.username}'))

        self.stdout.write(self.style.SUCCESS('Test users created successfully!'))

    def create_parking_spots(self):
        """Create test parking spots with sensors and blockers"""
        self.stdout.write('Creating test parking spots...')

        # Get tariff zones
        tariff_zones = TariffZone.objects.all()
        if not tariff_zones.exists():
            self.stdout.write(self.style.WARNING('No tariff zones found. Creating parking spots will fail.'))
            return

        # Create parking spots in different locations
        parking_spots_data = [
            {
                'name': 'Spot A1',
                'latitude1': 43.235658,
                'longitude1': 76.911137,
                'latitude2': 43.235658,
                'longitude2': 76.911235,
                'latitude3': 43.235572,
                'longitude3': 76.911235,
                'latitude4': 43.235572,
                'longitude4': 76.911137,
                'price_per_hour': Decimal('100.00'),
                'tariff_zone': tariff_zones[0]  # City Center
            },
            {
                'name': 'Spot A2',
                'latitude1': 43.235673,
                'longitude1': 76.911145,
                'latitude2': 43.235673,
                'longitude2': 76.911244,
                'latitude3': 43.235588,
                'longitude3': 76.911244,
                'latitude4': 43.235588,
                'longitude4': 76.911145,
                'price_per_hour': Decimal('100.00'),
                'tariff_zone': tariff_zones[0]  # City Center
            },
            {
                'name': 'Spot A3',
                'latitude1': 43.235687,
                'longitude1': 76.911153,
                'latitude2': 43.235687,
                'longitude2': 76.911252,
                'latitude3': 43.235603,
                'longitude3': 76.911252,
                'latitude4': 43.235603,
                'longitude4': 76.911153,
                'price_per_hour': Decimal('100.00'),
                'tariff_zone': tariff_zones[0]  # City Center
            },
            {
                'name': 'Spot A4',
                'latitude1': 43.235702,
                'longitude1': 76.911161,
                'latitude2': 43.235702,
                'longitude2': 76.911260,
                'latitude3': 43.235618,
                'longitude3': 76.911260,
                'latitude4': 43.235618,
                'longitude4': 76.911161,
                'price_per_hour': Decimal('100.00'),
                'tariff_zone': tariff_zones[0]  # City Center
            },
            {
                'name': 'Spot B1',
                'latitude1': 43.236658,
                'longitude1': 76.912137,
                'latitude2': 43.236658,
                'longitude2': 76.912235,
                'latitude3': 43.236572,
                'longitude3': 76.912235,
                'latitude4': 43.236572,
                'longitude4': 76.912137,
                'price_per_hour': Decimal('120.00'),
                'tariff_zone': tariff_zones[1]  # Residential Area
            },
            {
                'name': 'Spot B2',
                'latitude1': 43.236673,
                'longitude1': 76.912145,
                'latitude2': 43.236673,
                'longitude2': 76.912244,
                'latitude3': 43.236588,
                'longitude3': 76.912244,
                'latitude4': 43.236588,
                'longitude4': 76.912145,
                'price_per_hour': Decimal('120.00'),
                'tariff_zone': tariff_zones[1]  # Residential Area
            },
            {
                'name': 'Spot B3',
                'latitude1': 43.236687,
                'longitude1': 76.912153,
                'latitude2': 43.236687,
                'longitude2': 76.912252,
                'latitude3': 43.236603,
                'longitude3': 76.912252,
                'latitude4': 43.236603,
                'longitude4': 76.912153,
                'price_per_hour': Decimal('120.00'),
                'tariff_zone': tariff_zones[1]  # Residential Area
            },
            {
                'name': 'Spot B4',
                'latitude1': 43.236702,
                'longitude1': 76.912161,
                'latitude2': 43.236702,
                'longitude2': 76.912260,
                'latitude3': 43.236618,
                'longitude3': 76.912260,
                'latitude4': 43.236618,
                'longitude4': 76.912161,
                'price_per_hour': Decimal('120.00'),
                'tariff_zone': tariff_zones[1]  # Residential Area
            },
            {
                'name': 'Spot C1',
                'latitude1': 43.237658,
                'longitude1': 76.913137,
                'latitude2': 43.237658,
                'longitude2': 76.913235,
                'latitude3': 43.237572,
                'longitude3': 76.913235,
                'latitude4': 43.237572,
                'longitude4': 76.913137,
                'price_per_hour': Decimal('150.00'),
                'tariff_zone': tariff_zones[2]  # Suburban Area
            },
            {
                'name': 'Spot C2',
                'latitude1': 43.237673,
                'longitude1': 76.913145,
                'latitude2': 43.237673,
                'longitude2': 76.913244,
                'latitude3': 43.237588,
                'longitude3': 76.913244,
                'latitude4': 43.237588,
                'longitude4': 76.913145,
                'price_per_hour': Decimal('150.00'),
                'tariff_zone': tariff_zones[2]  # Suburban Area
            },
        ]

        for spot_data in parking_spots_data:
            # Create parking spot
            spot = ParkingSpot.objects.create(
                name=spot_data['name'],
                latitude1=spot_data['latitude1'],
                longitude1=spot_data['longitude1'],
                latitude2=spot_data['latitude2'],
                longitude2=spot_data['longitude2'],
                latitude3=spot_data['latitude3'],
                longitude3=spot_data['longitude3'],
                latitude4=spot_data['latitude4'],
                longitude4=spot_data['longitude4'],
                price_per_hour=spot_data['price_per_hour'],
                tariff_zone=spot_data['tariff_zone']
            )

            # Create sensor for the spot
            sensor = Sensor.objects.create(
                parking_spot=spot,
                is_occupied=random.choice([True, False])
            )

            # Create blocker for the spot
            blocker = Blocker.objects.create(
                parking_spot=spot,
                is_raised=random.choice([True, False])
            )

            self.stdout.write(self.style.SUCCESS(f'Created parking spot: {spot.name}'))

        self.stdout.write(self.style.SUCCESS('Test parking spots created successfully!'))

    def create_subscription_plans(self):
        """Create test subscription plans"""
        self.stdout.write('Creating test subscription plans...')

        subscription_plans_data = [
            {
                'name': 'Basic Plan',
                'description': 'Basic subscription plan with 10% discount on parking',
                'duration_days': 30,
                'price': Decimal('500.00'),
                'discount_percentage': Decimal('10.00')
            },
            {
                'name': 'Standard Plan',
                'description': 'Standard subscription plan with 20% discount on parking',
                'duration_days': 90,
                'price': Decimal('1200.00'),
                'discount_percentage': Decimal('20.00')
            },
            {
                'name': 'Premium Plan',
                'description': 'Premium subscription plan with 30% discount on parking',
                'duration_days': 365,
                'price': Decimal('4000.00'),
                'discount_percentage': Decimal('30.00')
            }
        ]

        for plan_data in subscription_plans_data:
            plan = SubscriptionPlan.objects.create(
                name=plan_data['name'],
                description=plan_data['description'],
                duration_days=plan_data['duration_days'],
                price=plan_data['price'],
                discount_percentage=plan_data['discount_percentage']
            )

            self.stdout.write(self.style.SUCCESS(f'Created subscription plan: {plan.name}'))

        self.stdout.write(self.style.SUCCESS('Test subscription plans created successfully!'))

    def create_tariff_zones_and_rules(self):
        """Create test tariff zones and rules"""
        self.stdout.write('Creating test tariff zones and rules...')

        # Create tariff zones
        zones_data = [
            {
                'name': 'City Center',
                'description': 'Central business district with high demand'
            },
            {
                'name': 'Residential Area',
                'description': 'Residential neighborhoods with moderate demand'
            },
            {
                'name': 'Suburban Area',
                'description': 'Suburban areas with lower demand'
            }
        ]

        zones = []
        for zone_data in zones_data:
            zone = TariffZone.objects.create(
                name=zone_data['name'],
                description=zone_data['description']
            )
            zones.append(zone)
            self.stdout.write(self.style.SUCCESS(f'Created tariff zone: {zone.name}'))

        # Create tariff rules
        rules_data = [
            # City Center rules
            {
                'name': 'City Center - Weekday',
                'zone': zones[0],
                'time_period': 'all_day',
                'day_type': 'weekday',
                'price_per_hour': Decimal('200.00'),
                'priority': 10
            },
            {
                'name': 'City Center - Weekend',
                'zone': zones[0],
                'time_period': 'all_day',
                'day_type': 'weekend',
                'price_per_hour': Decimal('150.00'),
                'priority': 10
            },
            {
                'name': 'City Center - Night',
                'zone': zones[0],
                'time_period': 'night',
                'day_type': 'all',
                'price_per_hour': Decimal('100.00'),
                'priority': 20  # Higher priority to override the all_day rules
            },

            # Residential Area rules
            {
                'name': 'Residential - Weekday',
                'zone': zones[1],
                'time_period': 'all_day',
                'day_type': 'weekday',
                'price_per_hour': Decimal('150.00'),
                'priority': 10
            },
            {
                'name': 'Residential - Weekend',
                'zone': zones[1],
                'time_period': 'all_day',
                'day_type': 'weekend',
                'price_per_hour': Decimal('100.00'),
                'priority': 10
            },
            {
                'name': 'Residential - Night',
                'zone': zones[1],
                'time_period': 'night',
                'day_type': 'all',
                'price_per_hour': Decimal('75.00'),
                'priority': 20
            },

            # Suburban Area rules
            {
                'name': 'Suburban - Weekday',
                'zone': zones[2],
                'time_period': 'all_day',
                'day_type': 'weekday',
                'price_per_hour': Decimal('100.00'),
                'priority': 10
            },
            {
                'name': 'Suburban - Weekend',
                'zone': zones[2],
                'time_period': 'all_day',
                'day_type': 'weekend',
                'price_per_hour': Decimal('75.00'),
                'priority': 10
            },
            {
                'name': 'Suburban - Night',
                'zone': zones[2],
                'time_period': 'night',
                'day_type': 'all',
                'price_per_hour': Decimal('50.00'),
                'priority': 20
            }
        ]

        for rule_data in rules_data:
            rule = TariffRule.objects.create(
                name=rule_data['name'],
                zone=rule_data['zone'],
                time_period=rule_data['time_period'],
                day_type=rule_data['day_type'],
                price_per_hour=rule_data['price_per_hour'],
                priority=rule_data['priority']
            )

            self.stdout.write(self.style.SUCCESS(f'Created tariff rule: {rule.name}'))

        # Special rules for specific spots will be created after parking spots are created

        self.stdout.write(self.style.SUCCESS('Test tariff zones and rules created successfully!'))

    def create_special_tariff_rules(self):
        """Create special tariff rules for specific parking spots"""
        self.stdout.write('Creating special tariff rules for specific parking spots...')

        # Get tariff zones
        zones = TariffZone.objects.all()
        if not zones.exists():
            self.stdout.write(self.style.WARNING('No tariff zones found. Creating special tariff rules will fail.'))
            return

        # Get parking spots
        parking_spots = ParkingSpot.objects.all()
        if not parking_spots.exists():
            self.stdout.write(self.style.WARNING('No parking spots found. Creating special tariff rules will fail.'))
            return

        # Create special rules for specific spots
        special_rules_data = [
            {
                'name': 'Special Spot Rule - A1',
                'parking_spot': parking_spots.filter(name='Spot A1').first(),
                'time_period': 'all_day',
                'day_type': 'all',
                'price_per_hour': Decimal('250.00'),
                'priority': 30  # Highest priority to override zone rules
            },
            {
                'name': 'Special Spot Rule - A4',
                'parking_spot': parking_spots.filter(name='Spot A4').first(),
                'time_period': 'all_day',
                'day_type': 'all',
                'price_per_hour': Decimal('300.00'),
                'priority': 30
            }
        ]

        for rule_data in special_rules_data:
            if rule_data['parking_spot'] is None:
                self.stdout.write(self.style.WARNING(f"Parking spot for rule {rule_data['name']} not found. Skipping."))
                continue

            rule = TariffRule.objects.create(
                name=rule_data['name'],
                zone=zones[0],  # City Center zone
                parking_spot=rule_data['parking_spot'],
                time_period=rule_data['time_period'],
                day_type=rule_data['day_type'],
                price_per_hour=rule_data['price_per_hour'],
                priority=rule_data['priority']
            )

            self.stdout.write(self.style.SUCCESS(f'Created special tariff rule: {rule.name}'))

        self.stdout.write(self.style.SUCCESS('Special tariff rules created successfully!'))

    def create_user_subscriptions(self):
        """Create test user subscriptions"""
        self.stdout.write('Creating test user subscriptions...')

        users = User.objects.filter(is_staff=False)
        plans = SubscriptionPlan.objects.all()

        if users.exists() and plans.exists():
            # Assign subscriptions to some users
            for i, user in enumerate(users):
                # Skip some users to have a mix of users with and without subscriptions
                if i % 2 == 0:
                    continue

                # Select a plan for the user (cycling through available plans)
                plan = plans[i % len(plans)]

                # Create a subscription
                start_date = timezone.now() - timedelta(days=random.randint(1, 10))
                end_date = start_date + timedelta(days=plan.duration_days)

                subscription = UserSubscription.objects.create(
                    user=user,
                    plan=plan,
                    start_date=start_date,
                    end_date=end_date,
                    status='active',
                    auto_renew=random.choice([True, False]),
                    payment_method='wallet'
                )

                self.stdout.write(self.style.SUCCESS(f'Created subscription for user {user.username}: {plan.name}'))

        self.stdout.write(self.style.SUCCESS('Test user subscriptions created successfully!'))

    def create_reservations(self):
        """Create test reservations with payments"""
        self.stdout.write('Creating test reservations...')

        users = User.objects.filter(is_staff=False)
        parking_spots = ParkingSpot.objects.all()

        if users.exists() and parking_spots.exists():
            # Create a mix of active, completed, and pending reservations
            now = timezone.now()

            # Active reservations (current time is between start and end time)
            for i in range(5):
                if i >= len(users) or i >= len(parking_spots):
                    break

                user = users[i]
                spot = parking_spots[i]

                start_time = now - timedelta(hours=1)
                end_time = now + timedelta(hours=2)

                # Create selected_hours for hourly booking
                selected_hours = []
                current_hour = start_time.replace(minute=0, second=0, microsecond=0)
                while current_hour < end_time:
                    next_hour = current_hour + timedelta(hours=1)
                    selected_hours.append({
                        'start': current_hour.isoformat(),
                        'end': next_hour.isoformat()
                    })
                    current_hour = next_hour

                reservation = Reservation.objects.create(
                    user=user,
                    parking_spot=spot,
                    start_time=start_time,
                    end_time=end_time,
                    status='active',
                    selected_hours=selected_hours,
                    payment_method_type='wallet',
                    user_arrived=True,
                    arrival_time=start_time + timedelta(minutes=15)
                )

                # Calculate and set total price
                reservation.total_price = reservation.calculate_total_price()
                reservation.save()

                # Create payment
                payment = Payment.objects.create(
                    amount=reservation.total_price,
                    status='completed',
                    payment_date=start_time - timedelta(minutes=30),
                    payment_method='wallet',
                    transaction_id=f'WALLET-{user.id}-{reservation.id}'
                )

                # Link payment to reservation
                reservation.payment = payment
                reservation.save()

                # Create transaction for the payment
                wallet = Wallet.objects.get(user=user)
                Transaction.objects.create(
                    user=user,
                    wallet=wallet,
                    amount=reservation.total_price,
                    transaction_type='wallet_payment',
                    status='completed',
                    reservation_id=str(reservation.id),
                    description=f'Payment for reservation #{reservation.id}',
                    transaction_id=f'WALLET-{user.id}-{reservation.id}'
                )

                self.stdout.write(self.style.SUCCESS(f'Created active reservation for user {user.username} at spot {spot.name}'))

            # Completed reservations (end time is in the past)
            for i in range(3, 6):
                if i >= len(users) or i >= len(parking_spots):
                    break

                user = users[i % len(users)]
                spot = parking_spots[i % len(parking_spots)]

                start_time = now - timedelta(days=1, hours=3)
                end_time = now - timedelta(days=1)

                # Create selected_hours for hourly booking
                selected_hours = []
                current_hour = start_time.replace(minute=0, second=0, microsecond=0)
                while current_hour < end_time:
                    next_hour = current_hour + timedelta(hours=1)
                    selected_hours.append({
                        'start': current_hour.isoformat(),
                        'end': next_hour.isoformat()
                    })
                    current_hour = next_hour

                reservation = Reservation.objects.create(
                    user=user,
                    parking_spot=spot,
                    start_time=start_time,
                    end_time=end_time,
                    status='completed',
                    selected_hours=selected_hours,
                    payment_method_type='credit_card',
                    user_arrived=True,
                    arrival_time=start_time + timedelta(minutes=20)
                )

                # Calculate and set total price
                reservation.total_price = reservation.calculate_total_price()
                reservation.save()

                # Create payment
                payment = Payment.objects.create(
                    amount=reservation.total_price,
                    status='completed',
                    payment_date=start_time - timedelta(minutes=30),
                    payment_method='credit_card',
                    transaction_id=f'CARD-{user.id}-{reservation.id}'
                )

                # Link payment to reservation
                reservation.payment = payment
                reservation.save()

                self.stdout.write(self.style.SUCCESS(f'Created completed reservation for user {user.username} at spot {spot.name}'))

            # Pending reservations (start time is in the future)
            for i in range(6, 9):
                if i >= len(users) or i >= len(parking_spots):
                    break

                user = users[i % len(users)]
                spot = parking_spots[i % len(parking_spots)]

                start_time = now + timedelta(days=1)
                end_time = now + timedelta(days=1, hours=3)

                # Create selected_hours for hourly booking
                selected_hours = []
                current_hour = start_time.replace(minute=0, second=0, microsecond=0)
                while current_hour < end_time:
                    next_hour = current_hour + timedelta(hours=1)
                    selected_hours.append({
                        'start': current_hour.isoformat(),
                        'end': next_hour.isoformat()
                    })
                    current_hour = next_hour

                reservation = Reservation.objects.create(
                    user=user,
                    parking_spot=spot,
                    start_time=start_time,
                    end_time=end_time,
                    status='pending',
                    selected_hours=selected_hours,
                    payment_method_type='wallet',
                    user_arrived=False,
                    arrival_time=None
                )

                # Calculate and set total price
                reservation.total_price = reservation.calculate_total_price()
                reservation.save()

                # Create payment (pending)
                payment = Payment.objects.create(
                    amount=reservation.total_price,
                    status='pending'
                )

                # Link payment to reservation
                reservation.payment = payment
                reservation.save()

                self.stdout.write(self.style.SUCCESS(f'Created pending reservation for user {user.username} at spot {spot.name}'))

            # Cancelled reservations
            for i in range(9, 12):
                if i >= len(users) or i >= len(parking_spots):
                    break

                user = users[i % len(users)]
                spot = parking_spots[i % len(parking_spots)]

                start_time = now + timedelta(days=2)
                end_time = now + timedelta(days=2, hours=3)

                # Create selected_hours for hourly booking
                selected_hours = []
                current_hour = start_time.replace(minute=0, second=0, microsecond=0)
                while current_hour < end_time:
                    next_hour = current_hour + timedelta(hours=1)
                    selected_hours.append({
                        'start': current_hour.isoformat(),
                        'end': next_hour.isoformat()
                    })
                    current_hour = next_hour

                reservation = Reservation.objects.create(
                    user=user,
                    parking_spot=spot,
                    start_time=start_time,
                    end_time=end_time,
                    status='cancelled',
                    selected_hours=selected_hours,
                    payment_method_type='wallet',
                    user_arrived=False,
                    arrival_time=None
                )

                # Calculate and set total price
                reservation.total_price = reservation.calculate_total_price()
                reservation.save()

                # Create payment (refunded)
                payment = Payment.objects.create(
                    amount=reservation.total_price,
                    status='refunded',
                    payment_date=now - timedelta(days=1),
                    payment_method='wallet',
                    transaction_id=f'WALLET-{user.id}-{reservation.id}'
                )

                # Link payment to reservation
                reservation.payment = payment
                reservation.save()

                self.stdout.write(self.style.SUCCESS(f'Created cancelled reservation for user {user.username} at spot {spot.name}'))

        self.stdout.write(self.style.SUCCESS('Test reservations created successfully!'))
