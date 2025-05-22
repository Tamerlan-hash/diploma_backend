import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from users.models import UserProfile

pytestmark = pytest.mark.e2e

@pytest.mark.django_db
class TestUserRegistration:
    """Test the user registration API endpoint."""
    
    def test_successful_registration(self, api_client, user_data):
        """Test that a user can successfully register with valid data."""
        url = reverse('register')
        response = api_client.post(url, user_data, format='json')
        
        assert response.status_code == 201
        assert User.objects.filter(username=user_data['username']).exists()
        
        # Check that UserProfile was created with car details
        user = User.objects.get(username=user_data['username'])
        profile = UserProfile.objects.get(user=user)
        assert profile.car_number == user_data['car_number']
        assert profile.car_model == user_data['car_model']
    
    def test_registration_with_missing_required_fields(self, api_client):
        """Test that registration fails when required fields are missing."""
        url = reverse('register')
        incomplete_data = {
            "email": "incomplete@example.com",
            "password": "securepassword123"
        }
        response = api_client.post(url, incomplete_data, format='json')
        
        assert response.status_code == 400
        assert 'username' in response.data
    
    def test_registration_with_duplicate_username(self, api_client, create_user, user_data):
        """Test that registration fails when username already exists."""
        # Create a user with the same username
        create_user(username=user_data['username'])
        
        url = reverse('register')
        response = api_client.post(url, user_data, format='json')
        
        assert response.status_code == 400
        assert 'username' in response.data
    
    def test_registration_with_short_password(self, api_client, user_data):
        """Test that registration fails when password is too short."""
        user_data['password'] = 'short'
        url = reverse('register')
        response = api_client.post(url, user_data, format='json')
        
        assert response.status_code == 400
        assert 'password' in response.data
    
    def test_registration_without_car_details(self, api_client):
        """Test that registration works without car details (they're optional)."""
        url = reverse('register')
        data = {
            "username": "nocars",
            "email": "nocars@example.com",
            "password": "securepassword123"
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == 201
        user = User.objects.get(username="nocars")
        profile = UserProfile.objects.get(user=user)
        assert profile.car_number is None
        assert profile.car_model is None