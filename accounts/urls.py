"""
AgroMentor 360 - Accounts URL Configuration
Complete authentication and profile management routes
"""

from django.urls import path
from accounts import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('refresh-token/', views.refresh_token, name='refresh-token'),
    
    # Phone Verification
    path('verify-phone/', views.verify_phone, name='verify-phone'),
    path('resend-code/', views.resend_verification_code, name='resend-code'),
    
    # Profile Management
    path('profile/', views.get_profile, name='profile'),
    path('profile/update/', views.update_profile, name='update-profile'),
    path('profile/change-password/', views.change_password, name='change-password'),
    
    # Password Reset
    path('password-reset/', views.request_password_reset, name='password-reset'),
    path('password-reset/confirm/', views.confirm_password_reset, name='password-reset-confirm'),
    
    # User Stats
    path('stats/', views.user_stats, name='user-stats'),
]