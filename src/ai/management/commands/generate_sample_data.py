import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from sensor.models import ParkingSpot
from ai.models import ParkingSpotOccupancyHistory

class Command(BaseCommand):
    help = 'Generate sample historical data for parking spots to enable AI model training'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days of historical data to generate (default: 7)',
        )
        parser.add_argument(
            '--samples-per-day',
            type=int,
            default=24,
            help='Number of samples per day to generate (default: 24, one per hour)',
        )
        parser.add_argument(
            '--spot-id',
            type=str,
            help='Generate data for a specific parking spot ID',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing historical data before generating new data',
        )

    def handle(self, *args, **options):
        days = options.get('days')
        samples_per_day = options.get('samples_per_day')
        spot_id = options.get('spot_id')
        clear = options.get('clear')
        
        # Get spots to generate data for
        if spot_id:
            try:
                spots = [ParkingSpot.objects.get(reference=spot_id)]
                self.stdout.write(self.style.SUCCESS(f'Generating data for parking spot {spot_id}...'))
            except ParkingSpot.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Parking spot with ID {spot_id} does not exist'))
                return
        else:
            spots = ParkingSpot.objects.all()
            self.stdout.write(self.style.SUCCESS(f'Generating data for all {spots.count()} parking spots...'))
        
        # Clear existing data if requested
        if clear:
            if spot_id:
                deleted_count = ParkingSpotOccupancyHistory.objects.filter(
                    parking_spot__reference=spot_id
                ).delete()[0]
            else:
                deleted_count = ParkingSpotOccupancyHistory.objects.all().delete()[0]
            
            self.stdout.write(self.style.SUCCESS(f'Cleared {deleted_count} existing historical records'))
        
        # Generate data
        now = timezone.now()
        total_created = 0
        
        for spot in spots:
            created_for_spot = 0
            
            # Generate data for each day
            for day in range(days):
                # Start from 'days' days ago
                day_date = now - timedelta(days=days-day)
                
                # Generate samples throughout the day
                for hour in range(0, 24, 24 // samples_per_day):
                    timestamp = day_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                    
                    # Determine occupancy based on time patterns
                    # Weekdays (0-4) during business hours (8-18) are more likely to be occupied
                    is_weekday = timestamp.weekday() < 5
                    is_business_hours = 8 <= hour <= 18
                    
                    if is_weekday and is_business_hours:
                        # 70% chance of being occupied during weekday business hours
                        is_occupied = random.random() < 0.7
                    else:
                        # 30% chance of being occupied during off-hours
                        is_occupied = random.random() < 0.3
                    
                    # Create the historical record
                    ParkingSpotOccupancyHistory.objects.create(
                        parking_spot=spot,
                        timestamp=timestamp,
                        is_occupied=is_occupied,
                        day_of_week=timestamp.weekday(),
                        hour_of_day=hour
                    )
                    
                    created_for_spot += 1
            
            self.stdout.write(self.style.SUCCESS(
                f'Created {created_for_spot} historical records for spot {spot.reference}'
            ))
            total_created += created_for_spot
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully generated {total_created} historical records for {spots.count()} parking spots'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'You can now run "python manage.py train_ai_models" to train the models'
        ))