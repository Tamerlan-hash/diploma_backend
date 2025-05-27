from django.urls import path
from .views import (
    ReservationListCreateView,
    ReservationDetailView,
    AvailableParkingSpotsView,
    ReservationActionView,
    UserReservationsView,
    ReservationPaymentView,
    TimeSlotReservationsView,
    ParkingSpotAvailableWindowsView,
)

urlpatterns = [
    path('reservations/', ReservationListCreateView.as_view(), name='reservation-list-create'),
    path('reservations/<int:pk>/', ReservationDetailView.as_view(), name='reservation-detail'),
    path('reservations/<int:pk>/<str:action>/', ReservationActionView.as_view(), name='reservation-action'),
    path('reservations/<int:pk>/payment/<str:action>/', ReservationPaymentView.as_view(), name='reservation-payment'),
    path('available-spots/', AvailableParkingSpotsView.as_view(), name='available-parking-spots'),
    path('my-reservations/', UserReservationsView.as_view(), name='user-reservations'),
    path('time-slot-reservations/', TimeSlotReservationsView.as_view(), name='time-slot-reservations'),
    path('parking-spot/<str:spot_id>/available-windows/', ParkingSpotAvailableWindowsView.as_view(), name='parking-spot-available-windows'),
]
