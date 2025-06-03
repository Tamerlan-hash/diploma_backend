import time
from django.core.management.base import BaseCommand
from ai.ml_models import train_all_models
from sensor.models import ParkingSpot

class Command(BaseCommand):
    help = 'Train machine learning models for parking spot availability prediction'

    def add_arguments(self, parser):
        parser.add_argument(
            '--spot-id',
            type=str,
            help='Train model for a specific parking spot ID',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force retraining even if models already exist',
        )

    def handle(self, *args, **options):
        start_time = time.time()
        spot_id = options.get('spot_id')
        force = options.get('force', False)
        
        if spot_id:
            # Train model for a specific spot
            try:
                spot = ParkingSpot.objects.get(reference=spot_id)
                self.stdout.write(self.style.SUCCESS(f'Training model for parking spot {spot_id}...'))
                
                spot_ids = [spot_id]
                results = train_all_models(spot_ids=spot_ids)
                
                if results.get(spot_id, False):
                    self.stdout.write(self.style.SUCCESS(f'Successfully trained model for parking spot {spot_id}'))
                else:
                    self.stdout.write(self.style.WARNING(f'Not enough data to train model for parking spot {spot_id}'))
            except ParkingSpot.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Parking spot with ID {spot_id} does not exist'))
        else:
            # Train models for all spots
            self.stdout.write(self.style.SUCCESS('Training models for all parking spots...'))
            
            results = train_all_models()
            
            success_count = sum(results.values())
            total_count = len(results)
            
            self.stdout.write(self.style.SUCCESS(
                f'Successfully trained {success_count} out of {total_count} models'
            ))
            
            if success_count < total_count:
                self.stdout.write(self.style.WARNING(
                    f'{total_count - success_count} spots did not have enough data for training'
                ))
        
        elapsed_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f'Training completed in {elapsed_time:.2f} seconds'))