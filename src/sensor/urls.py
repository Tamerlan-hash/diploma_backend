# urls.py
from django.urls import path
from .views import (
    RaiseBlockerAPIView,
    LowerBlockerAPIView,
    SetSensorOccupiedAPIView,
    parking_spot_list,
    SensorOccupyAPIView,
    SensorUnoccupyAPIView,
    BlockerStatusAPIView,
)

urlpatterns = [
    path('', parking_spot_list, name='parking-spot-list'),  # GET all parking spots with sensors and blockers
    path('blocker/raise/<str:reference>/', RaiseBlockerAPIView.as_view(), name='raise_blocker'),
    path('blocker/lower/<str:reference>/', LowerBlockerAPIView.as_view(), name='lower_blocker'),
    path('sensor/set-occupied/<str:reference>/', SetSensorOccupiedAPIView.as_view(), name='set_sensor_occupied'),
    path('sensor/set-vacant/<str:reference>/', SetSensorOccupiedAPIView.as_view(), {'occupied': False}, name='set_sensor_vacant'),

    # New API endpoints
    path('sensor/occupy/<str:reference>/', SensorOccupyAPIView.as_view(), name='sensor_occupy'),  # POST endpoint for sensors to update their status to occupied
    path('sensor/unoccupy/<str:reference>/', SensorUnoccupyAPIView.as_view(), name='sensor_unoccupy'),  # POST endpoint for sensors to update their status to unoccupied
    path('blocker/status/<str:reference>/', BlockerStatusAPIView.as_view(), name='blocker_status'),  # GET endpoint for blockers to check their status
]
