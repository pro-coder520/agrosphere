from django.db import models
from django.conf import settings
import uuid

class Notification(models.Model):
    """
    System-wide notifications for users
    """
    NOTIFICATION_TYPES = [
        ('system', 'System Message'),
        ('order', 'Order Update'),
        ('consultation', 'Consultation Update'),
        ('payment', 'Payment Alert'),
        ('alert', 'Security Alert'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Content
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='system')
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Optional deep link (e.g., /orders/123)
    related_link = models.CharField(max_length=255, null=True, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.get_type_display()}: {self.title}"  # type: ignore[attr-defined]


class NotificationPreference(models.Model):
    """
    User settings for receiving notifications
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Channels
    email_enabled = models.BooleanField(default=True, help_text="Receive notifications via Email")
    push_enabled = models.BooleanField(default=True, help_text="Receive push notifications")
    sms_enabled = models.BooleanField(default=False, help_text="Receive notifications via SMS")
    
    # Categories (Granular control)
    order_updates = models.BooleanField(default=True)
    consultation_updates = models.BooleanField(default=True)
    marketing_promotions = models.BooleanField(default=True)
    security_alerts = models.BooleanField(default=True) # Usually forced True in logic, but good to have
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"

    def __str__(self):
        return f"Preferences for {self.user}"