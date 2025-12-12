from django.urls import path
from . import views

app_name = 'farming'

urlpatterns = [
    # Farms
    path('farms/', views.farm_list, name='farm-list'),
    path('farms/create/', views.create_farm, name='create-farm'),
    path('farms/<uuid:pk>/', views.farm_detail, name='farm-detail'),
    
    # Crops
    path('crops/', views.crop_list, name='crop-list'),
    path('crops/create/', views.create_crop, name='create-crop'),
    path('crops/<uuid:pk>/', views.crop_detail, name='crop-detail'),
    
    # AI Features
    path('ai/recommendations/', views.get_crop_recommendations, name='ai-recommendations'),
    path('ai/detect-disease/', views.detect_disease, name='detect-disease'),
    path('ai/farming-tips/', views.get_farming_tips, name='farming-tips'),
    
    # Text-to-Speech (For reading tips aloud)
    path('ai/tts/', views.get_audio_guidance, name='text-to-speech'),
    
    # Voice Assistant (For talking to the AI)
    path('ai/voice-assistant/', views.voice_assistant, name='voice-assistant'),

    # Tasks
    path('tasks/', views.task_list, name='task-list'),
    path('tasks/create/', views.create_task, name='create-task'),
    
    # Weather
    path('weather/alerts/', views.weather_alerts, name='weather-alerts'),
]