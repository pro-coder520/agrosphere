"""
AgroMentor 360 - Expert Serializers
"""

from rest_framework import serializers
from .models import Expert, Consultation, ConsultationMessage
from accounts.serializers import UserProfileSerializer


class ExpertSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    consultation_count = serializers.IntegerField(source='consultations.count', read_only=True)
    
    class Meta: #type:ignore
        model = Expert
        fields = [
            'id', 'user', 'user_name', 'specializations', 'bio',
            'years_of_experience', 'certifications', 'consultation_fee',
            'rating', 'is_verified', 'consultation_count', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'rating', 'is_verified', 'created_at']


class ExpertDetailSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(source='user.profile', read_only=True)
    consultation_count = serializers.IntegerField(source='consultations.count', read_only=True)
    completed_consultations = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(source='rating', read_only=True)
    
    class Meta: #type:ignore
        model = Expert
        fields = [
            'id', 'user', 'specializations', 'bio', 'years_of_experience',
            'certifications', 'consultation_fee', 'rating', 'is_verified',
            'consultation_count', 'completed_consultations', 'average_rating',
            'created_at'
        ]
        read_only_fields = ['id', 'rating', 'is_verified', 'created_at']
    
    def get_completed_consultations(self, obj):
        return obj.consultations.filter(status='completed').count()


class ConsultationMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    is_own_message = serializers.SerializerMethodField()
    
    class Meta: #type:ignore
        model = ConsultationMessage
        fields = [
            'id', 'consultation', 'sender', 'sender_name', 'message',
            'sent_at', 'is_own_message'
        ]
        read_only_fields = ['id', 'sender', 'sent_at']
    
    def get_is_own_message(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.sender == request.user
        return False


class ConsultationSerializer(serializers.ModelSerializer):
    farmer_name = serializers.CharField(source='farmer.get_full_name', read_only=True)
    expert_name = serializers.CharField(source='expert.user.get_full_name', read_only=True)
    message_count = serializers.IntegerField(source='messages.count', read_only=True)
    
    class Meta: #type:ignore
        model = Consultation
        fields = [
            'id', 'farmer', 'farmer_name', 'expert', 'expert_name',
            'topic', 'description', 'status', 'rating', 'message_count',
            'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'farmer', 'rating', 'created_at', 'completed_at']


class ConsultationDetailSerializer(serializers.ModelSerializer):
    farmer = UserProfileSerializer(source='farmer.profile', read_only=True)
    expert = ExpertSerializer(read_only=True)
    messages = ConsultationMessageSerializer(many=True, read_only=True)
    message_count = serializers.IntegerField(source='messages.count', read_only=True)
    
    class Meta: #type:ignore
        model = Consultation
        fields = [
            'id', 'farmer', 'expert', 'topic', 'description', 'status',
            'rating', 'review', 'messages', 'message_count', 'created_at',
            'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at']