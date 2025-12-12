"""
AgroMentor 360 - USSD URL Configuration
"""

from django.urls import path
from . import views

app_name = 'ussd'

urlpatterns = [
    path('callback/', views.ussd_callback, name='ussd-callback'),
    path('payment-callback/', views.ussd_payment_callback, name='payment-callback'),
]