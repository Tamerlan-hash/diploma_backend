# users/views.py

from django.contrib.auth.models import User
from rest_framework import generics, parsers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import RegisterSerializer, UserSerializer, UserProfileUpdateSerializer
from .models import UserProfile
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response


@swagger_auto_schema(
    operation_description="Публичная регистрация",
    security=[],
)
class RegisterView(generics.CreateAPIView):
    """
    Публичный эндпоинт для регистрации.
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


@swagger_auto_schema(
    operation_description="Публичная аутентификация",
    security=[],
)
class LoginView(TokenObtainPairView):
    """
    Публичный эндпоинт для получения JWT-токенов.
    """
    permission_classes = [AllowAny]


class UserDetailView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(self.get_serializer(request.user).data)


@swagger_auto_schema(
    operation_description="Обновление профиля пользователя",
)
class UserProfileUpdateView(generics.UpdateAPIView):
    """
    Эндпоинт для обновления профиля пользователя.
    Требует аутентификации.
    """
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get_object(self):
        """
        Returns the UserProfile object for the authenticated user.
        Creates it if it doesn't exist.
        """
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
