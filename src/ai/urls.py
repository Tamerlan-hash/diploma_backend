from django.urls import path
from .views import (
    ParkingAvailabilityPredictionView,
    RecommendedParkingSpotsView,
    update_occupancy_history_view
)

app_name = 'ai'

urlpatterns = [
    path('predictions/parking-spot/<uuid:spot_id>/', ParkingAvailabilityPredictionView.as_view(), name='parking-availability-prediction'),
    path('recommendations/parking-spots/', RecommendedParkingSpotsView.as_view(), name='recommended-parking-spots'),
    path('update-occupancy-history/', update_occupancy_history_view, name='update-occupancy-history'),
]