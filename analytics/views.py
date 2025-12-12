"""
AgroMentor 360 - Analytics Views
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta

from .models import UserActivity
from accounts.models import User
from farming.models import Farm, Crop
from marketplace.models import Product, Order
from investments.models import FarmInvestment
from experts.models import Consultation


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_analytics(request):
    """Get personalized dashboard analytics"""
    user = request.user
    
    # User's farms
    farms = user.farms.all()
    
    # User's investments
    investments = user.investments.all()
    
    # User's marketplace activity
    products_sold = user.listings.count()
    orders = user.orders.count()
    
    # User's consultations
    consultations = user.consultations.count()
    
    analytics = {
        'farms': {
            'total': farms.count(),
            'active_crops': farms.aggregate(
                total=Count('crops', filter=Q(crops__status='growing'))
            )['total'] or 0,
            'pending_tasks': farms.aggregate(
                total=Count('tasks', filter=Q(tasks__status='pending'))
            )['total'] or 0,
        },
        'investments': {
            'total': investments.count(),
            'active': investments.filter(status='active').count(),
            'total_invested': float(investments.aggregate(
                total=Sum('amount')
            )['total'] or 0),
        },
        'marketplace': {
            'products_listed': products_sold,
            'orders_placed': orders,
        },
        'consultations': {
            'total': consultations,
            'pending': Consultation.objects.filter(
                Q(farmer=user) | Q(expert__user=user),
                status='pending'
            ).count(),
        }
    }
    
    return Response(analytics)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_activity(request):
    """Get user activity log"""
    days = int(request.query_params.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    activities = UserActivity.objects.filter(
        user=request.user,
        timestamp__gte=start_date
    ).order_by('-timestamp')[:100]
    
    # Group by activity type
    activity_summary = activities.values('activity_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    return Response({
        'total_activities': activities.count(),
        'summary': list(activity_summary),
        'recent_activities': [{
            'id': str(a.id),
            'activity_type': a.activity_type,
            'created_at': a.created_at
        } for a in activities[:20]]
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def platform_stats(request):
    """Get platform-wide statistics (admin only)"""
    
    # User stats
    total_users = User.objects.count()
    active_users = User.objects.filter(
        last_login__gte=timezone.now() - timedelta(days=30)
    ).count()
    
    # Farming stats
    total_farms = Farm.objects.count()
    total_crops = Crop.objects.count()
    
    # Marketplace stats
    total_products = Product.objects.filter(status='active').count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(
        status='delivered'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Investment stats
    total_investments = FarmInvestment.objects.count()
    total_invested = FarmInvestment.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Consultation stats
    total_consultations = Consultation.objects.count()
    completed_consultations = Consultation.objects.filter(
        status='completed'
    ).count()
    
    stats = {
        'users': {
            'total': total_users,
            'active_monthly': active_users,
            'new_this_month': User.objects.filter(
                date_joined__gte=timezone.now() - timedelta(days=30)
            ).count(),
        },
        'farming': {
            'total_farms': total_farms,
            'total_crops': total_crops,
            'active_crops': Crop.objects.filter(status='growing').count(),
        },
        'marketplace': {
            'total_products': total_products,
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'avg_order_value': float(total_revenue / total_orders if total_orders > 0 else 0),
        },
        'investments': {
            'total_investments': total_investments,
            'total_invested': float(total_invested),
            'avg_investment': float(total_invested / total_investments if total_investments > 0 else 0),
        },
        'consultations': {
            'total': total_consultations,
            'completed': completed_consultations,
            'completion_rate': float(completed_consultations / total_consultations * 100 if total_consultations > 0 else 0),
        }
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def export_analytics(request):
    """Export analytics data (admin only)"""
    # This would generate a CSV/Excel export
    # For now, return JSON
    
    export_type = request.query_params.get('type', 'all')
    
    data = {
        'exported_at': timezone.now(),
        'type': export_type,
        'message': 'Analytics export feature - implement CSV generation'
    }
    
    return Response(data)