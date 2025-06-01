"""
URL configuration for diploma_smart_parking project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions

from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Simple view that returns CSRF token
@ensure_csrf_cookie
def get_csrf(request):
    return JsonResponse({"detail": "CSRF cookie set"})

schema_view = get_schema_view(
    openapi.Info(
        title="API",
        default_version='v1',
        description="Документация API",
    ),
    public=True,
    permission_classes=[permissions.AllowAny,],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', get_csrf, name='api-root'),  # Root API endpoint for CSRF token
    path('api/sensor/', include('sensor.urls')),
    path('api/auth/', include('users.urls')),
    path('api/parking/', include('parking.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    # Схема без UI (JSON/YAML)
    path('swagger<str:format>', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    # Swagger UI
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    # Redoc UI
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
