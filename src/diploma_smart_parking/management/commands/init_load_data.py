from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import random
from datetime import timedelta

from users.models import UserProfile
from sensor.models import ParkingSpot, Sensor, Blocker
from subscriptions.models import SubscriptionPlan, UserSubscription, TariffZone, TariffRule
from payments.models import Wallet, PaymentMethod, Transaction
from parking.models import Reservation, Payment
from notifications.models import Notification


class Command(BaseCommand):
    help = 'Initialize database with test data for all models'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data initialization...'))
        
        # Create test users
        self.create_users()
        
        # Create tariff zones and subscription plans
        self.create_tariff_zones()
        self.create_subscription_plans()
        
        # Create parking spots with sensors and blockers
        self.create_parking_spots()
        
        # Create user subscriptions
        self.create_user_subscriptions()
        
        # Create payment methods and add funds to wallets
        self.create_payment_methods()
        self.add_wallet_funds()
        
        # Create reservations with payments
        self.create_reservations()
        
        # Create notifications
        self.create_notifications()
        
        self.stdout.write(self.style.SUCCESS('Data initialization completed successfully!'))
    
    def create_users(self):
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
                car_number='AA123BB',
                car_model='Admin Car'
            )
        
        # Create regular users
        test_users = [
            {'username': 'user1', 'email': 'user1@example.com', 'car': 'BMW X5', 'car_number': 'BB789CC'},
            {'username': 'user2', 'email': 'user2@example.com', 'car': 'Toyota Camry', 'car_number': 'CC456DD'},
            {'username': 'user3', 'email': 'user3@example.com', 'car': 'Honda Civic', 'car_number': 'DD123EE'},
            {'username': 'user4', 'email': 'user4@example.com', 'car': 'Tesla Model 3', 'car_number': 'EE789FF'},
            {'username': 'user5', 'email': 'user5@example.com', 'car': 'Ford Focus', 'car_number': 'FF456GG'},
        ]
        
        for user_data in test_users:
            if not User.objects.filter(username=user_data['username']).exists():
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password='password123',
                    first_name=f"Test {user_data['username'].capitalize()}",
                    last_name='User'
                )
                UserProfile.objects.create(
                    user=user,
                    car_number=user_data['car_number'],
                    car_model=user_data['car']
                )
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(test_users) + 1} test users'))
    
    def create_tariff_zones(self):
        self.stdout.write('Creating tariff zones...')
        
        zones = [
            {'name': 'City Center', 'description': 'High-demand central area with premium pricing'},
            {'name': 'Business District', 'description': 'Commercial area with moderate pricing'},
            {'name': 'Residential Area', 'description': 'Residential neighborhoods with lower pricing'},
            {'name': 'Suburban', 'description': 'Outskirts of the city with lowest pricing'},
        ]
        
        for zone_data in zones:
            TariffZone.objects.get_or_create(
                name=zone_data['name'],
                defaults={'description': zone_data['description']}
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(zones)} tariff zones'))
    
    def create_subscription_plans(self):
        self.stdout.write('Creating subscription plans...')
        
        plans = [
            {'name': 'Basic', 'description': 'Basic plan with 5% discount', 'duration_days': 30, 'price': '500.00', 'discount': '5.00'},
            {'name': 'Standard', 'description': 'Standard plan with 10% discount', 'duration_days': 90, 'price': '1200.00', 'discount': '10.00'},
            {'name': 'Premium', 'description': 'Premium plan with 15% discount', 'duration_days': 365, 'price': '4000.00', 'discount': '15.00'},
        ]
        
        for plan_data in plans:
            SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults={
                    'description': plan_data['description'],
                    'duration_days': plan_data['duration_days'],
                    'price': Decimal(plan_data['price']),
                    'discount_percentage': Decimal(plan_data['discount'])
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(plans)} subscription plans'))
    
    def create_parking_spots(self):
        self.stdout.write('Creating parking spots with sensors and blockers...')
        
        # Get tariff zones
        zones = list(TariffZone.objects.all())
        
        # Create parking spots in each zone
        spots_per_zone = 5
        total_spots = 0
        
        for zone in zones:
            for i in range(spots_per_zone):
                spot_name = f"{zone.name} Spot {i+1}"
                
                # Create or get parking spot
                spot, created = ParkingSpot.objects.get_or_create(
                    name=spot_name,
                    defaults={
                        'latitude1': 55.75 + random.uniform(-0.05, 0.05),
                        'longitude1': 37.62 + random.uniform(-0.05, 0.05),
                        'latitude2': 55.75 + random.uniform(-0.05, 0.05),
                        'longitude2': 37.62 + random.uniform(-0.05, 0.05),
                        'latitude3': 55.75 + random.uniform(-0.05, 0.05),
                        'longitude3': 37.62 + random.uniform(-0.05, 0.05),
                        'latitude4': 55.75 + random.uniform(-0.05, 0.05),
                        'longitude4': 37.62 + random.uniform(-0.05, 0.05),
                        'price_per_hour': Decimal(str(50 + (4 - zones.index(zone)) * 50)),  # Price based on zone
                        'tariff_zone': zone
                    }
                )
                
                if created:
                    total_spots += 1
                
                # Create sensor for this spot if it doesn't exist
                Sensor.objects.get_or_create(
                    parking_spot=spot,
                    defaults={'is_occupied': random.choice([True, False])}
                )
                
                # Create blocker for this spot if it doesn't exist
                Blocker.objects.get_or_create(
                    parking_spot=spot,
                    defaults={'is_raised': random.choice([True, False])}
                )
        
        # Create tariff rules
        self.create_tariff_rules()
        
        self.stdout.write(self.style.SUCCESS(f'Created {total_spots} parking spots with sensors and blockers'))
    
    def create_tariff_rules(self):
        self.stdout.write('Creating tariff rules...')
        
        # Get all zones
        zones = TariffZone.objects.all()
        
        # Create general rules for each zone
        for zone in zones:
            # Base price depends on zone
            base_price = 50 + (4 - list(zones).index(zone)) * 50
            
            # Create weekday rule
            TariffRule.objects.get_or_create(
                name=f"{zone.name} Weekday",
                zone=zone,
                day_type='weekday',
                time_period='all_day',
                defaults={
                    'price_per_hour': Decimal(str(base_price)),
                    'priority': 1
                }
            )
            
            # Create weekend rule (higher price)
            TariffRule.objects.get_or_create(
                name=f"{zone.name} Weekend",
                zone=zone,
                day_type='weekend',
                time_period='all_day',
                defaults={
                    'price_per_hour': Decimal(str(base_price * 1.2)),
                    'priority': 1
                }
            )
            
            # Create peak hours rule (even higher price)
            TariffRule.objects.get_or_create(
                name=f"{zone.name} Peak Hours",
                zone=zone,
                day_type='all',
                time_period='afternoon',
                defaults={
                    'price_per_hour': Decimal(str(base_price * 1.5)),
                    'priority': 2  # Higher priority to override the general rules
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created tariff rules for {zones.count()} zones'))
    
    def create_user_subscriptions(self):
        self.stdout.write('Creating user subscriptions...')
        
        # Get all users except admin
        users = User.objects.exclude(username='admin')
        
        # Get all subscription plans
        plans = list(SubscriptionPlan.objects.all())
        
        # Create subscriptions for some users
        subscription_count = 0
        for i, user in enumerate(users):
            # Assign different plans to different users
            if i < len(plans):
                plan = plans[i]
                
                # Create subscription if it doesn't exist
                start_date = timezone.now() - timedelta(days=random.randint(1, 10))
                end_date = start_date + timedelta(days=plan.duration_days)
                
                subscription, created = UserSubscription.objects.get_or_create(
                    user=user,
                    plan=plan,
                    defaults={
                        'start_date': start_date,
                        'end_date': end_date,
                        'status': 'active',
                        'auto_renew': random.choice([True, False])
                    }
                )
                
                if created:
                    subscription_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {subscription_count} user subscriptions'))
    
    def create_payment_methods(self):
        self.stdout.write('Creating payment methods...')
        
        # Get all users
        users = User.objects.all()
        
        # Sample card data
        card_types = ['credit_card', 'debit_card']
        card_numbers = ['4111111111111111', '5555555555554444', '378282246310005']
        
        payment_method_count = 0
        for user in users:
            # Create 1-2 payment methods per user
            for i in range(random.randint(1, 2)):
                card_type = random.choice(card_types)
                card_number = random.choice(card_numbers)
                expiry_date = f"{random.randint(1, 12):02d}/{random.randint(23, 30):02d}"
                
                payment_method, created = PaymentMethod.objects.get_or_create(
                    user=user,
                    card_number=card_number,
                    defaults={
                        'type': card_type,
                        'expiry_date': expiry_date,
                        'cardholder_name': f"{user.first_name} {user.last_name}",
                        'is_default': True
                    }
                )
                
                if created:
                    payment_method_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {payment_method_count} payment methods'))
    
    def add_wallet_funds(self):
        self.stdout.write('Adding funds to user wallets...')
        
        # Get all users
        users = User.objects.all()
        
        for user in users:
            wallet = user.wallet
            
            # Add random amount to wallet
            amount = Decimal(str(random.randint(1000, 5000)))
            
            # Get default payment method
            payment_method = PaymentMethod.objects.filter(user=user, is_default=True).first()
            
            if payment_method:
                # Create deposit transaction
                Transaction.create_wallet_deposit(
                    wallet=wallet,
                    amount=amount,
                    description=f'Initial deposit for testing',
                    payment_method=payment_method
                )
        
        self.stdout.write(self.style.SUCCESS(f'Added funds to {users.count()} user wallets'))
    
    def create_reservations(self):
        self.stdout.write('Creating reservations with payments...')
        
        # Get all users except admin
        users = User.objects.exclude(username='admin')
        
        # Get all parking spots
        spots = list(ParkingSpot.objects.all())
        
        reservation_count = 0
        for user in users:
            # Create 1-3 reservations per user
            for i in range(random.randint(1, 3)):
                # Select random spot
                spot = random.choice(spots)
                
                # Create reservation with random times
                now = timezone.now()
                
                # Some reservations in the past, some active, some in the future
                time_offset = random.choice([-2, -1, 0, 1, 2])
                
                if time_offset < 0:
                    # Past reservation
                    start_time = now + timedelta(days=time_offset, hours=random.randint(1, 5))
                    end_time = start_time + timedelta(hours=random.randint(1, 4))
                    status = 'completed'
                elif time_offset == 0:
                    # Active reservation
                    start_time = now - timedelta(hours=random.randint(1, 2))
                    end_time = now + timedelta(hours=random.randint(1, 3))
                    status = 'active'
                else:
                    # Future reservation
                    start_time = now + timedelta(days=time_offset, hours=random.randint(1, 5))
                    end_time = start_time + timedelta(hours=random.randint(1, 4))
                    status = 'pending'
                
                # Create reservation
                reservation = Reservation.objects.create(
                    user=user,
                    parking_spot=spot,
                    start_time=start_time,
                    end_time=end_time,
                    status=status
                )
                
                # Calculate price
                reservation.total_price = reservation.calculate_total_price()
                reservation.save()
                
                # Create payment
                payment = reservation.create_payment()
                
                # Process payment (50% card, 50% wallet)
                if random.choice([True, False]):
                    # Card payment
                    payment_method = PaymentMethod.objects.filter(user=user).first()
                    if payment_method:
                        try:
                            reservation.process_card_payment(payment_method.id)
                            reservation.payment_method_type = 'card'
                            reservation.save()
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f'Error processing card payment: {e}'))
                else:
                    # Wallet payment
                    try:
                        reservation.process_wallet_payment()
                        reservation.payment_method_type = 'wallet'
                        reservation.save()
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Error processing wallet payment: {e}'))
                
                # For active reservations, simulate user arrival
                if status == 'active':
                    reservation.user_arrived = True
                    reservation.arrival_time = start_time + timedelta(minutes=random.randint(5, 30))
                    reservation.save()
                
                reservation_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {reservation_count} reservations with payments'))
    
    def create_notifications(self):
        self.stdout.write('Creating notifications...')
        
        # Get all users
        users = User.objects.all()
        
        # Get active reservations
        active_reservations = Reservation.objects.filter(status='active')
        
        notification_count = 0
        
        # Create expiring notifications for active reservations
        for reservation in active_reservations:
            Notification.create_reservation_expiring_notification(reservation)
            notification_count += 1
        
        # Create some random notifications for all users
        notification_types = [
            'payment_successful',
            'payment_failed',
            'reservation_extended',
        ]
        
        for user in users:
            # Create 1-3 random notifications per user
            for i in range(random.randint(1, 3)):
                notification_type = random.choice(notification_types)
                
                if notification_type == 'payment_successful':
                    title = "Payment Successful"
                    message = "Your payment has been processed successfully."
                elif notification_type == 'payment_failed':
                    title = "Payment Failed"
                    message = "There was an issue processing your payment. Please try again."
                else:  # reservation_extended
                    title = "Reservation Extended"
                    message = "Your reservation has been extended successfully."
                
                Notification.create_notification(
                    user=user,
                    notification_type=notification_type,
                    title=title,
                    message=message
                )
                
                notification_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {notification_count} notifications'))