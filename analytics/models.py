"""
AgroMentor 360 - Analytics Models
"""

from django.db import models
from django.conf import settings
import uuid


class UserActivity(models.Model):
    """
    Track user activity for analytics
    """
    
    ACTIVITY_TYPES = [
        ('login', 'Login'),
        ('farm_create', 'Farm Created'),
        ('crop_create', 'Crop Created'),
        ('investment', 'Investment Made'),
        ('purchase', 'Marketplace Purchase'),
        ('consultation', 'Consultation Booked'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    metadata = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_activities'
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'activity_type']),
            models.Index(fields=['created_at']),
        ]