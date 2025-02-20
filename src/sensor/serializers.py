# serializers.py
from rest_framework import serializers
from .models import Sensor

class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = ('reference', 'name', 'latitude', 'longitude', 'is_lock', 'created_at')
