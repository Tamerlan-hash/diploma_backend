# serializers.py
from rest_framework import serializers
from .models import Sensor

class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = (
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
