from django.db import models
from django.utils import timezone
from sensor.models import ParkingSpot


class ParkingSpotOccupancyHistory(models.Model):
    """
    Model to store historical data of parking spot occupancy.
    This data can be used for training prediction models.
    """
    parking_spot = models.ForeignKey(ParkingSpot, on_delete=models.CASCADE, related_name='occupancy_history')
    timestamp = models.DateTimeField(default=timezone.now)
    is_occupied = models.BooleanField()
    day_of_week = models.IntegerField()  # 0-6 (Monday-Sunday)
    hour_of_day = models.IntegerField()  # 0-23

    class Meta:
        verbose_name_plural = 'Parking spot occupancy histories'
        ordering = ['-timestamp']

    def save(self, *args, **kwargs):
        # Automatically set day_of_week and hour_of_day based on timestamp
        if not self.day_of_week:
            self.day_of_week = self.timestamp.weekday()
        if not self.hour_of_day:
            self.hour_of_day = self.timestamp.hour
        super().save(*args, **kwargs)


class ParkingAvailabilityPrediction(models.Model):
    """
    Model to store predictions of parking spot availability.
    """
    parking_spot = models.ForeignKey(ParkingSpot, on_delete=models.CASCADE, related_name='availability_predictions')
    prediction_time = models.DateTimeField()  # Time for which the prediction is made
    probability_available = models.FloatField()  # Probability that the spot will be available (0-1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Parking availability predictions'
        ordering = ['prediction_time']