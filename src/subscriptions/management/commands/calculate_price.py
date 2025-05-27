from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from sensor.models import Sensor
from subscriptions.models import calculate_price_with_subscription
from decimal import Decimal
import datetime

class Command(BaseCommand):
    help = 'Calculate price for a parking spot with given parameters'

    def add_arguments(self, parser):
        parser.add_argument('--user_id', type=int, help='User ID')
        parser.add_argument('--spot_id', type=str, help='Parking spot ID (reference)')
        parser.add_argument('--start_time', type=str, help='Start time (YYYY-MM-DD HH:MM)')
        parser.add_argument('--end_time', type=str, help='End time (YYYY-MM-DD HH:MM)')
        parser.add_argument('--duration', type=int, help='Duration in hours (alternative to end_time)')

    def handle(self, *args, **options):
        # Get user
        user_id = options.get('user_id')
        if not user_id:
            self.stdout.write(self.style.ERROR('User ID is required'))
            return

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with ID {user_id} not found'))
            return

        # Get parking spot
        spot_id = options.get('spot_id')
        if not spot_id:
            self.stdout.write(self.style.ERROR('Parking spot ID is required'))
            return

        try:
            # First try to get by reference (UUID)
            import uuid
            try:
                # Try to convert to UUID if it's in UUID format
                uuid_obj = uuid.UUID(spot_id)
                parking_spot = Sensor.objects.get(reference=uuid_obj)
            except (ValueError, TypeError):
                # If not a valid UUID, try to get by name
                parking_spot = Sensor.objects.get(name=spot_id)
        except Sensor.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Parking spot with ID/name {spot_id} not found'))
            return

        # Get start time
        start_time_str = options.get('start_time')
        if start_time_str:
            try:
                start_time = timezone.make_aware(datetime.datetime.strptime(start_time_str, '%Y-%m-%d %H:%M'))
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid start time format. Use YYYY-MM-DD HH:MM'))
                return
        else:
            # Use current time as default
            start_time = timezone.now()
            start_time_str = start_time.strftime('%Y-%m-%d %H:%M')

        # Get end time
        end_time_str = options.get('end_time')
        duration = options.get('duration')

        if end_time_str:
            try:
                end_time = timezone.make_aware(datetime.datetime.strptime(end_time_str, '%Y-%m-%d %H:%M'))
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid end time format. Use YYYY-MM-DD HH:MM'))
                return
        elif duration:
            end_time = start_time + datetime.timedelta(hours=duration)
            end_time_str = end_time.strftime('%Y-%m-%d %H:%M')
        else:
            # Use start time + 1 hour as default
            end_time = start_time + datetime.timedelta(hours=1)
            end_time_str = end_time.strftime('%Y-%m-%d %H:%M')

        # Calculate price
        price = calculate_price_with_subscription(user, parking_spot, start_time, end_time)

        # Print results
        self.stdout.write(self.style.SUCCESS(f'Price calculation for:'))
        self.stdout.write(f'User: {user.username} (ID: {user.id})')
        self.stdout.write(f'Parking spot: {parking_spot.name} (ID: {parking_spot.reference})')
        self.stdout.write(f'Start time: {start_time_str}')
        self.stdout.write(f'End time: {end_time_str}')
        self.stdout.write(f'Duration: {(end_time - start_time).total_seconds() / 3600:.2f} hours')
        self.stdout.write(self.style.SUCCESS(f'Total price: {price} tenge'))

        # Check if there are any spot-specific tariff rules
        from subscriptions.models import TariffRule
        spot_rules = TariffRule.objects.filter(parking_spot=parking_spot, is_active=True)
        if spot_rules.exists():
            self.stdout.write(self.style.SUCCESS(f'Found {spot_rules.count()} spot-specific tariff rules:'))
            for rule in spot_rules:
                self.stdout.write(f'- {rule.name}: {rule.price_per_hour} tenge/hour (Priority: {rule.priority})')
        else:
            self.stdout.write(self.style.WARNING('No spot-specific tariff rules found for this parking spot'))

            # Check if there are any zone rules that apply
            zone_rules = TariffRule.objects.filter(
                zone__in=parking_spot.zone.all() if hasattr(parking_spot, 'zone') else [],
                parking_spot__isnull=True,
                is_active=True
            )
            if zone_rules.exists():
                self.stdout.write(self.style.SUCCESS(f'Found {zone_rules.count()} zone tariff rules that might apply:'))
                for rule in zone_rules:
                    self.stdout.write(f'- {rule.name}: {rule.price_per_hour} tenge/hour (Priority: {rule.priority})')
            else:
                self.stdout.write(self.style.WARNING('No zone tariff rules found that might apply'))
