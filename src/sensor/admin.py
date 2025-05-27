from django.contrib import admin
from .models import ParkingSpot, Sensor, Blocker

@admin.register(ParkingSpot)
class ParkingSpotAdmin(admin.ModelAdmin):
    list_display = (
        'reference',
        'name',
        'latitude1',
        'latitude2',
        'latitude3',
        'latitude4',
        'longitude1',
        'longitude2',
        'longitude3',
        'longitude4',
        'price_per_hour',
        'created_at',
    )

@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = (
        'reference',
        'parking_spot',
        'is_occupied',
        'created_at',
    )

@admin.register(Blocker)
class BlockerAdmin(admin.ModelAdmin):
    list_display = (
        'reference',
        'parking_spot',
        'is_raised',
        'created_at',
    )
