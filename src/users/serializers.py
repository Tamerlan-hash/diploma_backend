# users/serializers.py

from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Не менее 8 символов"
    )
    car_number = serializers.CharField(max_length=20, required=False, help_text="Номер машины")
    car_model = serializers.CharField(max_length=100, required=False, help_text="Модель машины")

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'car_number', 'car_model')

    def create(self, validated_data):
        car_number = validated_data.pop('car_number', None)
        car_model = validated_data.pop('car_model', None)

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )

        # Create the user profile with car information
        UserProfile.objects.create(
            user=user,
            car_number=car_number,
            car_model=car_model
        )

        return user


class UserSerializer(serializers.ModelSerializer):
    car_number = serializers.CharField(source='profile.car_number', read_only=True)
    car_model = serializers.CharField(source='profile.car_model', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'car_number', 'car_model')
