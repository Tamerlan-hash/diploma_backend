from django.contrib import admin
from .models import Sensor

@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ('reference', 'name', 'latitude', 'longitude', 'is_lock', 'created_at')