import uuid
from django.db import models
from django.utils import timezone
from decimal import Decimal

class ParkingSpot(models.Model):
    reference = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    latitude1 = models.FloatField(null=True, blank=True)
    latitude2 = models.FloatField(null=True, blank=True)
    latitude3 = models.FloatField(null=True, blank=True)
    latitude4 = models.FloatField(null=True, blank=True)
    longitude1 = models.FloatField(null=True, blank=True)
    longitude2 = models.FloatField(null=True, blank=True)
    longitude3 = models.FloatField(null=True, blank=True)
    longitude4 = models.FloatField(null=True, blank=True)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('100.00'))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.name)

    def is_reserved(self):
        """
        Check if this parking spot is currently reserved.
        Returns True if there is an active reservation for this spot at the current time.
        """
        now = timezone.now()
        return self.reservations.filter(
            status='active',
            start_time__lte=now,
            end_time__gte=now
        ).exists()

class Sensor(models.Model):
    reference = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parking_spot = models.OneToOneField(ParkingSpot, on_delete=models.CASCADE, related_name='sensor')
    is_occupied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sensor for {self.parking_spot.name}"

    def set_occupied(self, occupied=True):
        self.is_occupied = occupied
        self.save()

class Blocker(models.Model):
    reference = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parking_spot = models.OneToOneField(ParkingSpot, on_delete=models.CASCADE, related_name='blocker')
    is_raised = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Blocker for {self.parking_spot.name}"

    def raise_blocker(self):
        self.is_raised = True
        self.save()

    def lower_blocker(self):
        self.is_raised = False
        self.save()
