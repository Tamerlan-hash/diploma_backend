# users/urls.py

from django.urls import path
from .views import RegisterView, UserDetailView, UserProfileUpdateView, LoginView
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', UserDetailView.as_view(), name='user_detail'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='profile_update'),
]
