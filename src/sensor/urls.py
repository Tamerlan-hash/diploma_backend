# urls.py
from django.urls import path
from .views import (
    LockByReferenceAPIView,
    UnlockByReferenceAPIView,
    sensor_list,  # <-- импортируем
)

urlpatterns = [
    path('', sensor_list, name='sensor-list'),               # GET всех сенсоров
    path('lock/<str:reference>/', LockByReferenceAPIView.as_view(), name='lock_by_reference'),
    path('unlock/<str:reference>/', UnlockByReferenceAPIView.as_view(), name='unlock_by_reference'),
]
