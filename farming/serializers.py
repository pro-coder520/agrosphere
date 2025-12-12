"""
AgroMentor 360 - Farming Serializers
"""

from rest_framework import serializers
from .models import Farm, Crop, FarmTask, WeatherAlert, DiseaseDetection
from accounts.serializers import UserProfileSerializer


class FarmSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    crop_count = serializers.IntegerField(source='crops.count', read_only=True)
    
    class Meta: #type:ignore
        model = Farm
        fields = [
            'id', 'owner', 'owner_name', 'name', 'location', 'size',
            'latitude', 'longitude', 'description', 'crop_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']


class CropSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    days_to_harvest = serializers.IntegerField(read_only=True)
    growth_percentage = serializers.FloatField(read_only=True)
    
    class Meta: #type:ignore
        model = Crop
        fields = [
            'id', 'farm', 'farm_name', 'crop_type', 'variety', 'quantity',
            'planting_date', 'expected_harvest_date', 'harvest_date',
            'expected_yield', 'actual_yield', 'status', 'notes',
            'days_to_harvest', 'growth_percentage', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class FarmTaskSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta: #type:ignore
        model = FarmTask
        fields = [
            'id', 'farm', 'farm_name', 'title', 'description', 'task_type',
            'priority', 'due_date', 'status', 'completed_at', 'is_overdue',
            'created_at'
        ]
        read_only_fields = ['id', 'completed_at', 'created_at']


class WeatherDataSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    
    class Meta: #type:ignore
        model = WeatherAlert
        fields = [
            'id', 'farm', 'temperature', 'humidity',
            'rainfall', 'wind_speed', 'created_at'
        ]
        read_only_fields = ['id', 'timestamp']


class DiseaseDetectionSerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(source='crop.crop_type', read_only=True)
    
    class Meta: #type:ignore
        model = DiseaseDetection
        fields = [
            'id', 'crop', 'crop_name', 'image', 'disease_name',
            'confidence', 'recommendations', 'status', 'detected_at'
        ]
        read_only_fields = ['id', 'detected_at']


class FarmDetailSerializer(serializers.ModelSerializer):
    owner = UserProfileSerializer(source='owner.profile', read_only=True)
    crops = CropSerializer(many=True, read_only=True)
    tasks = FarmTaskSerializer(many=True, read_only=True)
    recent_weather = WeatherDataSerializer(source='weather_data.first', read_only=True)
    
    class Meta: #type:ignore
        model = Farm
        fields = [
            'id', 'owner', 'name', 'location', 'size', 'latitude', 'longitude',
            'description', 'crops', 'tasks', 'recent_weather', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']