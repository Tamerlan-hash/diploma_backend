from django.contrib import admin
from .models import Sensor

@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
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
        'is_lock',
        'created_at',
    )