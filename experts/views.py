"""
AgroMentor 360 - Expert Views
Expert consultation and advice management endpoints
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg, Count
from django.utils import timezone

from .models import Expert, Consultation, ConsultationMessage
from .serializers import (
    ExpertSerializer,
    ExpertDetailSerializer,
    ConsultationSerializer,
    ConsultationDetailSerializer,
    ConsultationMessageSerializer
)


@api_view(['GET'])
@permission_classes([AllowAny])
def expert_list(request):
    """List all experts"""
    experts = Expert.objects.filter(is_verified=True)
    
    # Filter by specialization
    specialization = request.query_params.get('specialization')
    if specialization:
        experts = experts.filter(specializations__icontains=specialization)
    
    # Filter by rating
    min_rating = request.query_params.get('min_rating')
    if min_rating:
        experts = experts.filter(rating__gte=float(min_rating))
    
    # Sort
    sort_by = request.query_params.get('sort', '-rating')
    experts = experts.order_by(sort_by)
    
    serializer = ExpertSerializer(experts, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def expert_detail(request, expert_id):
    """Get expert details"""
    expert = get_object_or_404(Expert, id=expert_id)
    serializer = ExpertDetailSerializer(expert)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_as_expert(request):
    """Apply to become an expert"""
    # Check if already an expert
    if hasattr(request.user, 'expert_profile'):
        return Response(
            {'error': 'You are already registered as an expert'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ExpertSerializer(data=request.data)
    if serializer.is_valid():
        expert = serializer.save(user=request.user, is_verified=False)
        return Response({
            'message': 'Application submitted. Awaiting verification.',
            'expert': ExpertDetailSerializer(expert).data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_expert_profile(request):
    """Update expert profile"""
    if not hasattr(request.user, 'expert_profile'):
        return Response(
            {'error': 'You are not registered as an expert'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    expert = request.user.expert_profile
    serializer = ExpertSerializer(expert, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response(ExpertDetailSerializer(expert).data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_consultation(request):
    """Request a consultation with an expert"""
    expert_id = request.data.get('expert_id')
    if not expert_id:
        return Response(
            {'error': 'Expert ID required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    expert = get_object_or_404(Expert, id=expert_id, is_verified=True)
    
    serializer = ConsultationSerializer(data=request.data)
    if serializer.is_valid():
        consultation = serializer.save(
            farmer=request.user,
            expert=expert
        )
        return Response(
            ConsultationDetailSerializer(consultation).data,
            status=status.HTTP_201_CREATED
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_consultations(request):
    """Get user's consultations"""
    consultations = Consultation.objects.filter(
        Q(farmer=request.user) | Q(expert__user=request.user)
    ).order_by('-created_at')
    
    # Filter by status
    consultation_status = request.query_params.get('status')
    if consultation_status:
        consultations = consultations.filter(status=consultation_status)
    
    serializer = ConsultationSerializer(consultations, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consultation_detail(request, consultation_id):
    """Get consultation details"""
    consultation = get_object_or_404(
        Consultation,
        id=consultation_id
    )
    
    # Verify access
    if consultation.farmer != request.user and consultation.expert.user != request.user:
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ConsultationDetailSerializer(consultation)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_consultation(request, consultation_id):
    """Accept a consultation (for experts)"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    # Verify expert
    if not hasattr(request.user, 'expert_profile') or consultation.expert.user != request.user:
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if consultation.status != 'pending':
        return Response(
            {'error': 'Consultation cannot be accepted in current status'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    consultation.status = 'accepted'
    consultation.save()
    
    return Response({
        'message': 'Consultation accepted',
        'consultation': ConsultationDetailSerializer(consultation).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_consultation(request, consultation_id):
    """Reject a consultation (for experts)"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    # Verify expert
    if not hasattr(request.user, 'expert_profile') or consultation.expert.user != request.user:
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if consultation.status != 'pending':
        return Response(
            {'error': 'Consultation cannot be rejected in current status'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    consultation.status = 'cancelled'
    consultation.save()
    
    return Response({
        'message': 'Consultation rejected',
        'consultation': ConsultationDetailSerializer(consultation).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_consultation(request, consultation_id):
    """Mark consultation as completed"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    # Verify expert
    if not hasattr(request.user, 'expert_profile') or consultation.expert.user != request.user:
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if consultation.status != 'in_progress':
        return Response(
            {'error': 'Consultation must be in progress to complete'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    consultation.status = 'completed'
    consultation.completed_at = timezone.now()
    consultation.save()
    
    return Response({
        'message': 'Consultation completed',
        'consultation': ConsultationDetailSerializer(consultation).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, consultation_id):
    """Send a message in consultation"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    # Verify access
    if consultation.farmer != request.user and consultation.expert.user != request.user:
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    message_text = request.data.get('message')
    if not message_text:
        return Response(
            {'error': 'Message text required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    message = ConsultationMessage.objects.create(
        consultation=consultation,
        sender=request.user,
        message=message_text
    )
    
    # Update consultation status
    if consultation.status == 'accepted':
        consultation.status = 'in_progress'
        consultation.save()
    
    serializer = ConsultationMessageSerializer(message)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def consultation_messages(request, consultation_id):
    """Get consultation messages"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    # Verify access
    if consultation.farmer != request.user and consultation.expert.user != request.user:
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    messages = ConsultationMessage.objects.filter(consultation=consultation).order_by('sent_at')
    serializer = ConsultationMessageSerializer(messages, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rate_consultation(request, consultation_id):
    """Rate a completed consultation"""
    consultation = get_object_or_404(
        Consultation,
        id=consultation_id,
        farmer=request.user
    )
    
    if consultation.status != 'completed':
        return Response(
            {'error': 'Can only rate completed consultations'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if consultation.rating is not None:
        return Response(
            {'error': 'Consultation already rated'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    rating = request.data.get('rating')
    review = request.data.get('review', '')
    
    if not rating or not (1 <= int(rating) <= 5):
        return Response(
            {'error': 'Rating must be between 1 and 5'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    consultation.rating = rating
    consultation.review = review
    consultation.save()
    
    # Update expert rating
    expert = consultation.expert
    avg_rating = expert.consultations.filter(
        rating__isnull=False
    ).aggregate(Avg('rating'))['rating__avg']
    
    expert.rating = avg_rating
    expert.save(update_fields=['rating'])
    
    return Response({
        'message': 'Rating submitted successfully',
        'consultation': ConsultationDetailSerializer(consultation).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expert_earnings(request):
    """Get expert earnings (for experts)"""
    if not hasattr(request.user, 'expert_profile'):
        return Response(
            {'error': 'You are not registered as an expert'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    expert = request.user.expert_profile
    consultations = expert.consultations.filter(status='completed')
    
    total_earnings = consultations.count() * expert.consultation_fee
    
    earnings = {
        'total_consultations': consultations.count(),
        'consultation_fee': float(expert.consultation_fee),
        'total_earnings': float(total_earnings),
        'pending_consultations': expert.consultations.filter(
            status__in=['pending', 'accepted', 'in_progress']
        ).count(),
        'average_rating': float(expert.rating or 0)
    }
    
    return Response(earnings)


@api_view(['GET'])
@permission_classes([AllowAny])
def expert_stats(request):
    """Get platform expert statistics"""
    stats = {
        'total_experts': Expert.objects.filter(is_verified=True).count(),
        'total_consultations': Consultation.objects.count(),
        'completed_consultations': Consultation.objects.filter(status='completed').count(),
        'average_rating': float(Expert.objects.filter(
            is_verified=True
        ).aggregate(Avg('rating'))['rating__avg'] or 0),
        'top_experts': ExpertSerializer(
            Expert.objects.filter(is_verified=True).order_by('-rating')[:5],
            many=True
        ).data
    }
    
    return Response(stats)