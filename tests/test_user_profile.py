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