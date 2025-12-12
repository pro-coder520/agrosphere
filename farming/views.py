from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from typing import Dict, Any # Added for type hinting
from .tts_service import tts_service
from .speech_service import sts_service
from django.http import HttpResponse
from rest_framework.parsers import MultiPartParser, FormParser # Required for file uploads

from .models import Farm, Crop, FarmTask
from .serializers import (
    FarmSerializer, 
    CropSerializer, 
    FarmTaskSerializer,
)

# ----------------------------------------------------------------
# Farm Management
# ----------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def farm_list(request):
    """List all farms owned by the user"""
    farms = Farm.objects.filter(owner=request.user)
    serializer = FarmSerializer(farms, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_farm(request):
    """Create a new farm"""
    serializer = FarmSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(owner=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def farm_detail(request, pk):
    """Retrieve, update or delete a specific farm"""
    farm = get_object_or_404(Farm, pk=pk, owner=request.user)

    if request.method == 'GET':
        serializer = FarmSerializer(farm)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = FarmSerializer(farm, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        farm.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


# ----------------------------------------------------------------
# Crop Management
# ----------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def crop_list(request):
    """List crops (optionally filtered by farm_id)"""
    farm_id = request.query_params.get('farm_id')
    if farm_id:
        crops = Crop.objects.filter(farm__owner=request.user, farm__id=farm_id)
    else:
        crops = Crop.objects.filter(farm__owner=request.user)
        
    serializer = CropSerializer(crops, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_crop(request):
    """Add a new crop cycle to a farm"""
    # Ensure the user owns the farm they are adding a crop to
    farm_id = request.data.get('farm')
    if not Farm.objects.filter(id=farm_id, owner=request.user).exists():
        return Response(
            {'error': 'You do not own this farm.'}, 
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = CropSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def crop_detail(request, pk):
    """Manage a specific crop"""
    crop = get_object_or_404(Crop, pk=pk, farm__owner=request.user)

    if request.method == 'GET':
        serializer = CropSerializer(crop)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = CropSerializer(crop, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        crop.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


# ----------------------------------------------------------------
# AI Features (Simulated for MVP)
# ----------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_crop_recommendations(request):
    """
    Returns crop recommendations based on soil data and location.
    """
    soil_ph = request.data.get('soil_ph')
    location = request.data.get('location')
    
    # TODO: Connect to actual ML model
    # Simulation:
    recommendations = [
        {
            "crop": "Cassava",
            "confidence": 0.95,
            "reason": "High drought resistance suitable for your region."
        },
        {
            "crop": "Maize",
            "confidence": 0.85,
            "reason": "Soil pH is optimal for cereal growth."
        }
    ]
    
    return Response({
        "status": "success",
        "recommendations": recommendations,
        "soil_analysis": "Loamy soil detected, nitrogen levels adequate."
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def detect_disease(request):
    """
    Analyze uploaded leaf image for diseases.
    """
    # Access the uploaded file
    image_file = request.FILES.get('image')
    
    if not image_file:
        return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    # TODO: Send image to TensorFlow/PyTorch model
    # Simulation:
    return Response({
        "disease_detected": True,
        "diagnosis": "Cassava Mosaic Disease",
        "confidence": 0.92,
        "treatment": "Remove infected plants immediately. Use resistant stem cuttings for replanting.",
        "severity": "High"
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_farming_tips(request):
    """
    Context-aware farming tips based on user's active crops.
    """
    user_crops = Crop.objects.filter(farm__owner=request.user, status='growing')
    crop_names = list(user_crops.values_list('name', flat=True).distinct())
    
    tips = []
    if "Maize" in crop_names:
        tips.append("Apply NPK fertilizer now for your growing Maize.")
    if "Cassava" in crop_names:
        tips.append("Ensure your Cassava field is weed-free to maximize tuber growth.")
    
    # Generic tip if no specific crops found
    if not tips:
        tips.append("Regular soil testing helps improve yield by 30%.")

    return Response({"tips": tips})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_audio_guidance(request):
    """
    Text-to-Speech: Convert text (e.g., AI tip) to audio in local language.
    Used when a farmer clicks "Listen" on a text tip.
    """
    text = request.data.get('text')
    lang = request.data.get('language', 'pcm') # Default to Pidgin
    
    if not text:
        return Response({'error': 'Text is required'}, status=status.HTTP_400_BAD_REQUEST)

    # FIX: Call the instance 'tts_service', not the class 'YarnGPTService'
    audio_content = tts_service.generate_audio(text, lang)
    
    if audio_content:
        # Return audio file directly (streamed)
        return HttpResponse(audio_content, content_type="audio/mpeg")
    
    return Response({'error': 'Failed to generate audio'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser]) # Enable file uploads
def voice_assistant(request):
    """
    Speech-to-Speech: Full voice conversation pipeline.
    Used when a farmer records a question via microphone.
    
    Pipeline:
    1. Upload Audio -> 2. Transcribe (Deepgram) -> 3. AI Answer (Gemini) -> 4. Generate Audio (TTS)
    """
    audio_file = request.FILES.get('audio')
    language = request.data.get('language', 'ha') # Default to Hausa for rural context

    if not audio_file:
        return Response({'error': 'No audio recorded'}, status=status.HTTP_400_BAD_REQUEST)

    # Call the Speech Service Manager
    result = sts_service.process_voice_query(audio_file, language)

    if not result:
        return Response({'error': 'Failed to process voice command'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Return audio blob so it plays immediately
    response = HttpResponse(result['audio_content'], content_type="audio/mpeg")
    
    # Attach text transcripts in headers so the UI can display them
    # (Optional: You might need to base64 encode these if they contain special characters)
    try:
        response['X-Transcription'] = result['transcription']
        # Truncate response header to avoid overflow
        response['X-Text-Response'] = result['text_response'][:500] 
    except:
        pass # Ignore header errors, audio is the priority
    
    return response

# ----------------------------------------------------------------
# Task Management
# ----------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_list(request):
    """Get pending farming tasks"""
    tasks = FarmTask.objects.filter(farm__owner=request.user)
    
    # Filter by status
    status_param = request.query_params.get('status')
    if status_param:
        tasks = tasks.filter(status=status_param)
        
    serializer = FarmTaskSerializer(tasks, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_task(request):
    """Create a new task"""
    serializer = FarmTaskSerializer(data=request.data)
    
    if serializer.is_valid():
        # FIX: Explicit type hint to tell Pylance this is a Dict, not Empty
        validated_data: Dict[str, Any] = serializer.validated_data # type: ignore
        
        # Now accessing ['farm'] works correctly
        farm = validated_data['farm']
        
        if farm.owner != request.user:
             return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
             
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ----------------------------------------------------------------
# Weather Service
# ----------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weather_alerts(request):
    """
    Get weather alerts for the user's farm locations.
    """
    # Logic: Get user's farm location -> Call OpenWeatherMap API
    # Simulation:
    return Response({
        "location": "Ibadan, Nigeria",
        "current_temp": "28°C",
        "alerts": [
            {
                "type": "Rain Warning",
                "message": "Heavy rainfall expected in 24 hours. Delay fertilizer application.",
                "severity": "Medium"
            }
        ]
    })