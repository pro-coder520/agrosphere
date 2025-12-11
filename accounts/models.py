from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, db_index=True, default=uuid.uuid4)
    videos_watched = models.IntegerField(null=False, blank=False, default=0)
    is_farmer = models.BooleanField(default=0, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_index = ['id']