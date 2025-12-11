"""
URL configuration for agrosphere project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint for monitoring and load balancers
    """
    return Response({
        'status': 'healthy',
        'service': 'AgroMentor 360 API',
        'version': '1.0.0',
        'demo_mode': settings.DEMO_MODE,
        'features': {
            'web3': settings.ENABLE_WEB3,
            'ussd': settings.ENABLE_USSD,
            'ai': settings.ENABLE_AI_FEATURES,
            'notifications': settings.ENABLE_NOTIFICATIONS,
        }
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
def api_root(request):
    """
    API root endpoint with available endpoints
    """
    return Response({
        'message': 'Welcome to the Agrosehere API',
        'version': '1.0.0',
        'documentation': request.build_absolute_uri('/api/docs/'),
        'endpoints': {
            'authentication': request.build_absolute_uri('/api/v1/auth/'),
            'farming': request.build_absolute_uri('/api/v1/farming/'),
            'experts': request.build_absolute_uri('/api/v1/experts/'),
            'investments': request.build_absolute_uri('/api/v1/investments/'),
            'marketplace': request.build_absolute_uri('/api/v1/marketplace/'),
            'blockchain': request.build_absolute_uri('/api/v1/blockchain/'),
            'ussd': request.build_absolute_uri('/api/v1/ussd/'),
            'notifications': request.build_absolute_uri('/api/v1/notifications/'),
            'analytics': request.build_absolute_uri('/api/v1/analytics/'),
        }
    })

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),
    
    # Health check and API root
    path('health/', health_check, name='health-check'),
    path('api/', api_root, name='api-root'),
    
    # API Documentation (Swagger)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # API v1 Endpoints
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/farming/', include('farming.urls')),
    path('api/v1/experts/', include('experts.urls')),
    path('api/v1/investments/', include('investments.urls')),
    path('api/v1/marketplace/', include('marketplace.urls')),
    path('api/v1/blockchain/', include('blockchain.urls')),
    path('api/v1/ussd/', include('ussd.urls')),
    path('api/v1/notifications/', include('notifications.urls')),
    path('api/v1/analytics/', include('analytics.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Customize admin site
admin.site.site_header = "Agrosphere Administration"
admin.site.site_title = "Agrosphere 360 Admin"
admin.site.index_title = "Welcome to Agrosphere Admin Panel"