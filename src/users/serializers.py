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
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'car_number', 'car_model', 'avatar_url')

    def get_avatar_url(self, obj):
        if hasattr(obj, 'profile') and obj.profile.avatar:
            return obj.profile.avatar.url
        return None


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', required=False)
    email = serializers.EmailField(source='user.email', required=False)
    avatar = serializers.ImageField(required=False)

    class Meta:
        model = UserProfile
        fields = ('username', 'email', 'car_number', 'car_model', 'avatar')

    def to_representation(self, instance):
        """Return a representation of the user profile including the avatar URL if available."""
        ret = super().to_representation(instance)
        if instance.avatar:
            ret['avatar_url'] = instance.avatar.url
        return ret

    def update(self, instance, validated_data):
        # Update User model fields if provided
        user_data = validated_data.pop('user', {})
        if 'email' in user_data:
            instance.user.email = user_data['email']
        if 'username' in user_data:
            # Check if username is already taken
            if User.objects.filter(username=user_data['username']).exclude(id=instance.user.id).exists():
                raise serializers.ValidationError({'username': 'This username is already taken.'})
            instance.user.username = user_data['username']

        if user_data:
            instance.user.save()

        # Update UserProfile fields
        instance.car_number = validated_data.get('car_number', instance.car_number)
        instance.car_model = validated_data.get('car_model', instance.car_model)
        if 'avatar' in validated_data:
            instance.avatar = validated_data['avatar']
        instance.save()

        return instance
