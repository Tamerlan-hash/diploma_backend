from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Loads initial data for subscriptions app'

    def handle(self, *args, **options):
        fixture_path = os.path.join(
            settings.BASE_DIR, 
            'subscriptions', 
            'fixtures', 
            'initial_data.json'
        )
        
        self.stdout.write(self.style.SUCCESS(f'Loading fixture from {fixture_path}'))
        
        try:
            with transaction.atomic():
                # Load the fixture
                call_command('loaddata', fixture_path, verbosity=1)
                
                self.stdout.write(self.style.SUCCESS('Successfully loaded initial data'))
                
                # Print summary of loaded data
                from subscriptions.models import SubscriptionPlan, TariffZone, TariffRule
                
                plans_count = SubscriptionPlan.objects.count()
                zones_count = TariffZone.objects.count()
                rules_count = TariffRule.objects.count()
                
                self.stdout.write(self.style.SUCCESS(f'Loaded {plans_count} subscription plans'))
                self.stdout.write(self.style.SUCCESS(f'Loaded {zones_count} tariff zones'))
                self.stdout.write(self.style.SUCCESS(f'Loaded {rules_count} tariff rules'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading initial data: {e}'))
            raise