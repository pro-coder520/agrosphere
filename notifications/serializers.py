from rest_framework import serializers
from .models import Notification, NotificationPreference

class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for listing and reading notifications
    """
    time_since = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta: #type:ignore
        model = Notification
        fields = [
            'id', 
            'type', 
            'type_display',
            'title', 
            'message', 
            'related_link', 
            'is_read', 
            'read_at', 
            'created_at', 
            'time_since'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'read_at', 'type_display']

    def get_time_since(self, obj):
        """Returns a human-readable time string (e.g., '5 mins ago')"""
        from django.utils.timesince import timesince
        return f"{timesince(obj.created_at)} ago"


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for managing user notification settings
    """
    class Meta: #type:ignore
        model = NotificationPreference
        fields = [
            'email_enabled',
            'push_enabled',
            'sms_enabled',
            'order_updates',
            'consultation_updates',
            'marketing_promotions',
            'security_alerts',
            'updated_at'
        ]
        read_only_fields = ['updated_at']