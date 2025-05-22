import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import UserProfile

@pytest.fixture
def api_client():
    """Return an API client for testing."""
    return APIClient()

@pytest.fixture
def create_user():
    """Factory to create users with specific attributes."""
    def _create_user(username="testuser", email="test@example.com", password="testpassword123", car_number=None, car_model=None):
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # Create a UserProfile for the user
        UserProfile.objects.create(
            user=user,
            car_number=car_number,
            car_model=car_model
        )

        return user
    return _create_user

@pytest.fixture
def auth_client(create_user):
    """Return an authenticated API client."""
    user = create_user()
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client, user

@pytest.fixture
def user_data():
    """Return valid user data for registration."""
    return {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "securepassword123",
        "car_number": "ABC123",
        "car_model": "Tesla Model 3"
    }
