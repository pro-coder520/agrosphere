from celery import shared_task
from django.utils import timezone
from django.db.models import Sum, Count
from django.core.cache import cache
from datetime import timedelta
from typing import Any, Dict # <--- Added for type hinting

import logging

logger = logging.getLogger(__name__)

@shared_task
def update_marketplace_metrics():
    """
    Update marketplace analytics metrics
    Runs every 4 hours via Celery Beat
    """
    try:
        from marketplace.models import Product, Order
        from accounts.models import User
        
        # Calculate metrics
        total_products = Product.objects.filter(status='available').count()
        total_orders = Order.objects.filter(status__in=['paid', 'delivered']).count()
        
        total_sales = Order.objects.filter(
            status__in=['paid', 'delivered']
        ).aggregate(
            ac=Sum('total_ac'),
            ngn=Sum('total_naira')
        )
        
        # Use explicit string lookup or type ignore for reverse relationships
        active_sellers = User.objects.filter(
            products__status='available' # type: ignore
        ).distinct().count()
        
        active_buyers = User.objects.filter(
            orders__status__in=['paid', 'delivered'] # type: ignore
        ).distinct().count()
        
        # Top products
        top_products = Product.objects.filter(
            status='available'
        ).order_by('-total_sold')[:10]
        
        metrics = {
            'total_products': total_products,
            'total_orders': total_orders,
            'total_sales_ac': float(total_sales['ac'] or 0),
            'total_sales_ngn': float(total_sales['ngn'] or 0),
            'active_sellers': active_sellers,
            'active_buyers': active_buyers,
            'top_products': [
                {
                    'name': p.name,
                    'sold': float(p.total_sold),
                    'price_ac': float(p.price_agrocoin)
                }
                for p in top_products
            ],
            'updated_at': timezone.now().isoformat()
        }
        
        # Cache for 4 hours
        cache.set('marketplace_metrics', metrics, 14400)
        
        logger.info(f"Updated marketplace metrics: {metrics}")
        return metrics
    
    except Exception as e:
        logger.error(f"Error updating marketplace metrics: {str(e)}")
        return {'error': str(e)}


@shared_task
def update_platform_statistics():
    """
    Update overall platform statistics
    Runs daily for dashboard
    """
    try:
        from accounts.models import User
        from farming.models import Farm, Crop
        from investments.models import FarmInvestment as Investment # Renamed to match your previous model
        from blockchain.models import Transaction
        
        # User statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        users_by_role = {}
        # Assuming USER_ROLE_CHOICES is defined on User model
        choices = getattr(User, 'USER_ROLE_CHOICES', [])
        for role, _ in choices:
            users_by_role[role] = User.objects.filter(role=role).count()
        
        # Farming statistics (Using string lookups to avoid import errors if models vary)
        total_farms = Farm.objects.filter(is_active=True).count() if hasattr(Farm, 'is_active') else Farm.objects.count()
        total_crops = Crop.objects.filter(status__in=['planted', 'growing', 'flowering']).count()
        
        # Investment statistics
        # Note: using 'amount' based on your FarmInvestment model
        total_invested = Investment.objects.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        active_investments = Investment.objects.filter(status='active').count()
        
        # Transaction statistics
        # Safety check if Transaction model exists
        try:
            total_transactions = Transaction.objects.filter(status='confirmed').count()
            total_volume = Transaction.objects.filter(
                status='confirmed'
            ).aggregate(total=Sum('amount'))['total'] or 0
        except:
            total_transactions = 0
            total_volume = 0
        
        statistics = {
            'users': {
                'total': total_users,
                'active': active_users,
                'by_role': users_by_role
            },
            'farming': {
                'total_farms': total_farms,
                'total_crops': total_crops
            },
            'investments': {
                'total_invested_ac': float(total_invested),
                'active_investments': active_investments
            },
            'transactions': {
                'total_count': total_transactions,
                'total_volume_ac': float(total_volume)
            },
            'updated_at': timezone.now().isoformat()
        }
        
        # Cache for 24 hours
        cache.set('platform_statistics', statistics, 86400)
        
        logger.info("Updated platform statistics")
        return statistics
    
    except Exception as e:
        logger.error(f"Error updating platform statistics: {str(e)}")
        return {'error': str(e)}


@shared_task
def generate_user_insights():
    """
    Generate personalized insights for users
    Runs weekly
    """
    try:
        from accounts.models import User
        # FIX 1: Import Crop here (it was missing in this scope)
        from farming.models import Crop 
        
        active_users = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(days=7)
        ).select_related('profile')[:100]  # Batch limit
        
        insights_generated = 0
        
        for user in active_users:
            try:
                # FIX 2: Type hint the dictionary so it accepts strings AND dicts
                insights: Dict[str, Any] = {
                    'user_id': str(user.id),
                    'generated_at': timezone.now().isoformat()
                }
                
                # Farming insights
                # FIX 3: Use getattr or type ignore for reverse relationships
                if getattr(user, 'role', '') == 'farmer':
                    # Using 'farms' related_name from User -> Farm
                    user_farms = getattr(user, 'farms', None)
                    if user_farms:
                        farms_count = user_farms.count() 
                        # Crops linked via Farm
                        crops_count = Crop.objects.filter(farm__owner=user, status='growing').count()
                        
                        insights['farming'] = {
                            'active_farms': farms_count,
                            'growing_crops': crops_count
                        }
                
                # Investment insights
                if getattr(user, 'role', '') == 'investor':
                    # Using 'investments' related_name from User -> FarmInvestment
                    user_investments = getattr(user, 'investments', None)
                    if user_investments:
                        inv_count = user_investments.filter(status='active').count()
                        
                        # FIX 4: Handle portfolio calculation safely
                        # If you don't have a Portfolio model, calculate sum manually
                        portfolio_value = user_investments.aggregate(
                            total=Sum('amount')
                        )['total'] or 0
                        
                        insights['investments'] = {
                            'active_count': inv_count,
                            'portfolio_value_ac': float(portfolio_value)
                        }
                
                # Store insights (could be in database or cache)
                cache.set(f'user_insights_{user.id}', insights, 604800)  # 1 week
                
                insights_generated += 1
            
            except Exception as e:
                logger.error(f"Error generating insights for user {user.id}: {str(e)}")
        
        logger.info(f"Generated insights for {insights_generated} users")
        return {'insights_generated': insights_generated}
    
    except Exception as e:
        logger.error(f"Error in generate_user_insights: {str(e)}")
        return {'error': str(e)}