import pytest
from django.urls import reverse
from django.contrib.auth.models import User

pytestmark = pytest.mark.e2e

@pytest.mark.django_db
class TestUserAuthentication:
    """Test the user authentication API endpoints."""
    
    def test_login_success(self, api_client, create_user):
        """Test that a user can successfully login with valid credentials."""
        # Create a test user
        username = "loginuser"
        password = "loginpassword123"
        create_user(username=username, password=password)
        
        url = reverse('token_obtain_pair')
        response = api_client.post(url, {
            "username": username,
            "password": password
        }, format='json')
        
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data
    
    def test_login_invalid_credentials(self, api_client, create_user):
        """Test that login fails with invalid credentials."""
        # Create a test user
        username = "loginuser"
        password = "loginpassword123"
        create_user(username=username, password=password)
        
        url = reverse('token_obtain_pair')
        response = api_client.post(url, {
            "username": username,
            "password": "wrongpassword"
        }, format='json')
        
        assert response.status_code == 401
    
    def test_token_refresh(self, api_client, create_user):
        """Test that a refresh token can be used to get a new access token."""
        # Create a test user
        username = "refreshuser"
        password = "refreshpassword123"
        create_user(username=username, password=password)
        
        # Get tokens
        login_url = reverse('token_obtain_pair')
        login_response = api_client.post(login_url, {
            "username": username,
            "password": password
        }, format='json')
        
        refresh_token = login_response.data['refresh']
        
        # Use refresh token to get new access token
        refresh_url = reverse('token_refresh')
        refresh_response = api_client.post(refresh_url, {
            "refresh": refresh_token
        }, format='json')
        
        assert refresh_response.status_code == 200
        assert 'access' in refresh_response.data
    
    def test_access_protected_endpoint(self, auth_client):
        """Test that a protected endpoint can be accessed with a valid token."""
        client, _ = auth_client
        url = reverse('user_detail')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'username' in response.data
    
    def test_access_protected_endpoint_without_token(self, api_client):
        """Test that a protected endpoint cannot be accessed without a token."""
        url = reverse('user_detail')
        response = api_client.get(url)
        
        assert response.status_code == 401