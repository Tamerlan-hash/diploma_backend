from django.utils import timezone
from datetime import timedelta
from .models import Reservation


def check_expiring_reservations():
    """
    Check for reservations that are about to expire and send notifications.
    This function should be called periodically by a scheduler (e.g., Celery).
    """
    # Get active reservations
    active_reservations = Reservation.objects.filter(status='active')
    
    # Check each reservation for expiration
    for reservation in active_reservations:
        # Check if notification should be sent (30 minutes before expiration)
        reservation.check_expiration_and_notify(minutes_before=30)


def auto_complete_expired_reservations():
    """
    Automatically complete reservations that have expired.
    This function should be called periodically by a scheduler (e.g., Celery).
    """
    now = timezone.now()
    
    # Get active reservations that have ended
    expired_reservations = Reservation.objects.filter(
        status='active',
        end_time__lt=now
    )
    
    # Complete each expired reservation
    for reservation in expired_reservations:
        try:
            reservation.complete()
            print(f"Auto-completed reservation {reservation.id}")
        except Exception as e:
            print(f"Error auto-completing reservation {reservation.id}: {e}")