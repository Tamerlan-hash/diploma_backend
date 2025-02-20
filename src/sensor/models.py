import uuid
from django.db import models

class Sensor(models.Model):
    reference = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_lock = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.reference)

    def lock(self):
        self.is_lock = True
        self.save()

    def unlock(self):
        self.is_lock = False
        self.save()
