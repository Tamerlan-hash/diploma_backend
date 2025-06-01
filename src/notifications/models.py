from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Notification(models.Model):
    TYPE_CHOICES = [
        ('reservation_expiring', 'Reservation Expiring'),
        ('next_reservation', 'Next Reservation'),
        ('payment_successful', 'Payment Successful'),
        ('payment_failed', 'Payment Failed'),
        ('reservation_extended', 'Reservation Extended'),
    ]

    STATUS_CHOICES = [
        ('unread', 'Unread'),
        ('read', 'Read'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unread')
    reservation_id = models.CharField(max_length=100, blank=True, null=True)  # Optional reference to a reservation
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    def mark_as_read(self):
        self.status = 'read'
        self.read_at = timezone.now()
        self.save()

    @classmethod
    def create_notification(cls, user, notification_type, title, message, reservation_id=None):
        """Create a notification for a user"""
        notification = cls.objects.create(
            user=user,
            type=notification_type,
            title=title,
            message=message,
            reservation_id=reservation_id
        )
        return notification

    @classmethod
    def create_reservation_expiring_notification(cls, reservation, minutes_left=30):
        """Create a notification for an expiring reservation"""
        user = reservation.user
        title = "Reservation Expiring Soon"
        message = f"Your reservation for parking spot {reservation.parking_spot.name} will expire in {minutes_left} minutes."
        
        # Check if there's a next reservation
        next_reservation = reservation.parking_spot.reservations.filter(
            start_time__gte=reservation.end_time,
            status__in=['pending', 'active']
        ).order_by('start_time').first()
        
        if next_reservation:
            message += f" Note that another user has reserved this spot after your reservation ends."
        else:
            message += f" You can extend your reservation if needed."
            
        return cls.create_notification(
            user=user,
            notification_type='reservation_expiring',
            title=title,
            message=message,
            reservation_id=str(reservation.id)
        )