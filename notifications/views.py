"""
AgroMentor 360 - Notification Views
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Notification, NotificationPreference
from .serializers import NotificationSerializer, NotificationPreferenceSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    """Get user notifications"""
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Filter by read status
    is_read = request.query_params.get('is_read')
    if is_read is not None:
        notifications = notifications.filter(is_read=is_read.lower() == 'true')
    
    # Pagination
    page_size = int(request.query_params.get('page_size', 20))
    page = int(request.query_params.get('page', 1))
    start = (page - 1) * page_size
    end = start + page_size
    
    total = notifications.count()
    notifications = notifications[start:end]
    
    serializer = NotificationSerializer(notifications, many=True)
    
    return Response({
        'count': total,
        'page': page,
        'page_size': page_size,
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_detail(request, notification_id):
    """Get notification details"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user
    )
    
    # Mark as read when viewed
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
    
    serializer = NotificationSerializer(notification)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user
    )
    
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save()
    
    return Response({
        'message': 'Notification marked as read',
        'notification': NotificationSerializer(notification).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_as_read(request):
    """Mark all notifications as read"""
    updated = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    return Response({
        'message': f'{updated} notifications marked as read',
        'count': updated
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notification_preferences(request):
    """Get notification preferences"""
    preferences, created = NotificationPreference.objects.get_or_create(
        user=request.user
    )
    
    serializer = NotificationPreferenceSerializer(preferences)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_notification_preferences(request):
    """Update notification preferences"""
    preferences, created = NotificationPreference.objects.get_or_create(
        user=request.user
    )
    
    serializer = NotificationPreferenceSerializer(
        preferences,
        data=request.data,
        partial=True
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Preferences updated successfully',
            'preferences': serializer.data
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)