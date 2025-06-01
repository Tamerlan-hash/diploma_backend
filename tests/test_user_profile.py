import pytest
from django.urls import reverse
from users.models import UserProfile

pytestmark = pytest.mark.e2e

@pytest.mark.django_db
class TestUserProfile:
    """Test the user profile API endpoint."""

    def test_get_user_profile(self, auth_client):
        """Test that an authenticated user can retrieve their profile."""
        client, user = auth_client

        # Create a profile with car details for the user
        profile = UserProfile.objects.get(user=user)
        profile.car_number = "TEST123"
        profile.car_model = "Test Car"
        profile.save()

        url = reverse('user_detail')
        response = client.get(url)

        assert response.status_code == 200
        assert response.data['username'] == user.username
        assert response.data['car_number'] == "TEST123"
        assert response.data['car_model'] == "Test Car"

    def test_get_user_profile_without_car_details(self, auth_client):
        """Test that a user profile can be retrieved even without car details."""
        client, user = auth_client

        url = reverse('user_detail')
        response = client.get(url)

        assert response.status_code == 200
        assert response.data['username'] == user.username
        # Car details should be null or empty string depending on serializer implementation
        assert response.data['car_number'] in [None, '']
        assert response.data['car_model'] in [None, '']

    def test_update_user_profile(self, auth_client):
        """Test that an authenticated user can update their profile."""
        client, user = auth_client

        # Ensure profile exists
        profile, created = UserProfile.objects.get_or_create(user=user)

        # Data to update
        update_data = {
            'car_number': 'NEW123',
            'car_model': 'New Car Model',
            'email': 'newemail@example.com'
        }

        url = reverse('profile_update')
        response = client.put(url, update_data, format='multipart')

        assert response.status_code == 200

        # Refresh user and profile from database
        user.refresh_from_db()
        profile.refresh_from_db()

        # Check that the data was updated
        assert profile.car_number == 'NEW123'
        assert profile.car_model == 'New Car Model'
        assert user.email == 'newemail@example.com'

    def test_partial_update_user_profile(self, auth_client):
        """Test that an authenticated user can partially update their profile."""
        client, user = auth_client

        # Set initial profile data
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.car_number = 'INITIAL123'
        profile.car_model = 'Initial Car'
        profile.save()

        # Data to update (only car_number)
        update_data = {
            'car_number': 'PARTIAL123'
        }

        url = reverse('profile_update')
        response = client.patch(url, update_data, format='multipart')

        assert response.status_code == 200

        # Refresh profile from database
        profile.refresh_from_db()

        # Check that only car_number was updated
        assert profile.car_number == 'PARTIAL123'
        assert profile.car_model == 'Initial Car'  # Should remain unchanged

    def test_update_user_profile_unauthenticated(self, client):
        """Test that an unauthenticated user cannot update a profile."""
        url = reverse('profile_update')
        response = client.put(url, {'car_number': 'TEST123'}, format='multipart')

        # Should return 401 Unauthorized
        assert response.status_code == 401
