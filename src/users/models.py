from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    car_number = models.CharField(max_length=20, blank=True, null=True)
    car_model = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.username
