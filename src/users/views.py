# users/views.py

from django.contrib.auth.models import User
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import RegisterSerializer, UserSerializer
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