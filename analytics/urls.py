"""
AgroMentor 360 - Analytics URL Configuration
"""

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.dashboard_analytics, name='dashboard'),
    path('user-activity/', views.user_activity, name='user-activity'),
    path('platform-stats/', views.platform_stats, name='platform-stats'),
    path('export/', views.export_analytics, name='export-analytics'),
]