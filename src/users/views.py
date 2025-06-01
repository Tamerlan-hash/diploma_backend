# users/views.py

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from rest_framework import generics, parsers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import RegisterSerializer, UserSerializer, UserProfileUpdateSerializer
from .models import UserProfile
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView


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
    operation_description="Публичная аутентификация с использованием JWT",
    security=[],
)
class LoginView(generics.GenericAPIView):
    """
    Публичный эндпоинт для аутентификации с использованием JWT токенов.
    """
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user is not None:
            # Import here to avoid circular imports
            from rest_framework_simplejwt.tokens import RefreshToken

            # Generate tokens
            refresh = RefreshToken.for_user(user)

            # Get user data
            user_data = self.get_serializer(user).data

            # Return tokens and user data
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': user_data
            })
        else:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


class UserDetailView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # With JWT authentication, request.user will be automatically set
        # if the token is valid, and the view will return 401 if not
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


@swagger_auto_schema(
    operation_description="Выход из системы (JWT)",
)
class LogoutView(APIView):
    """
    Эндпоинт для выхода из системы с использованием JWT.
    Требует аутентификации и refresh токен в теле запроса.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                # Import here to avoid circular imports
                from rest_framework_simplejwt.tokens import RefreshToken
                from rest_framework_simplejwt.exceptions import TokenError

                # Blacklist the refresh token
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except TokenError:
                    # Token is invalid or already blacklisted
                    pass

            # For backward compatibility, also logout from session
            logout(request)

            return Response({"detail": "Successfully logged out"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
