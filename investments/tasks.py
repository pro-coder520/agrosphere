from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum, F
from decimal import Decimal
import logging
from investments.models import Investment
from notifications.tasks import send_sms_notification

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_matured_investments(self):
    """
    Process investments that have reached maturity date
    Runs daily at midnight via Celery Beat
    Calculates and distributes returns to investors
    """
    try:
        from investments.models import Investment, InvestmentOpportunity
        from blockchain.models import Transaction
        from notifications.tasks import send_sms_notification
        
        # Get investments that matured today
        today = timezone.now().date()
        matured_investments = Investment.objects.filter(
            maturity_date=today,
            status='active'
        ).select_related('investor', 'opportunity')
        
        if not matured_investments:
            logger.info("No investments matured today")
            return {'processed': 0, 'message': 'No matured investments'}
        
        processed_count = 0
        total_paid_out = Decimal('0')
        
        for investment in matured_investments:
            try:
                # Calculate actual return (could be adjusted based on farm performance)
                # For now, use expected return
                actual_return = investment.expected_return_ac
                profit = actual_return - investment.amount_ac
                
                # Update investment record
                investment.actual_return_ac = actual_return
                investment.status = 'matured'
                investment.save(update_fields=['actual_return_ac', 'status'])
                
                # Create payout transaction
                conversion_rate = Decimal(str(settings.ETHEREUM_CONFIG['AGROCOIN_TO_NAIRA_RATE']))
                
                payout_tx = Transaction.objects.create(
                    to_wallet=investment.investor.wallet,
                    transaction_type='investment_return',
                    amount=actual_return,
                    naira_value=actual_return * conversion_rate,
                    status='confirmed',
                    description=f'Investment return: {investment.opportunity.title}',
                    confirmed_at=timezone.now(),
                    metadata={
                        'investment_id': str(investment.id),
                        'principal': float(investment.amount_ac),
                        'profit': float(profit),
                        'roi_percentage': float(investment.opportunity.expected_roi_percentage)
                    }
                )
                
                # Credit investor's wallet
                investment.investor.wallet.add_balance(actual_return)
                
                # Link payout transaction
                investment.payout_transaction = payout_tx
                investment.paid_out_at = timezone.now()
                investment.save(update_fields=['payout_transaction', 'paid_out_at'])
                
                # Send notification
                message = (
                    f"🎉 Investment matured! "
                    f"Principal: {investment.amount_ac} AC, "
                    f"Return: {actual_return} AC, "
                    f"Profit: {profit} AC (₦{profit * conversion_rate})"
                )
                send_sms_notification.delay(investment.investor.phone_number, message) #type:ignore
                
                processed_count += 1
                total_paid_out += actual_return
                
                logger.info(f"Processed investment {investment.id}: paid {actual_return} AC")
            
            except Exception as e:
                logger.error(f"Error processing investment {investment.id}: {str(e)}")
        
        # Update investment opportunities status
        update_opportunity_status.delay() #type:ignore
        
        logger.info(f"Processed {processed_count} matured investments, paid out {total_paid_out} AC")
        return {
            'processed': processed_count,
            'total_paid_out': float(total_paid_out),
            'date': today.isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in process_matured_investments: {str(e)}")
        raise self.retry(exc=e, countdown=300)


@shared_task
def update_opportunity_status():
    """
    Update investment opportunity statuses
    Check for fully funded or matured opportunities
    """
    try:
        from investments.models import InvestmentOpportunity
        
        updated_count = 0
        
        # Get all active opportunities
        opportunities = InvestmentOpportunity.objects.filter(
            status__in=['open', 'funded', 'active']
        )
        
        for opp in opportunities:
            old_status = opp.status
            
            # Check if fully funded
            if opp.funding_percentage >= 100 and opp.status == 'open':
                opp.status = 'funded'
                opp.funded_at = timezone.now()
                logger.info(f"Opportunity {opp.id} fully funded!")
            
            # Check if matured
            elif opp.status in ['funded', 'active'] and timezone.now().date() >= opp.maturity_date:
                opp.status = 'matured'
                logger.info(f"Opportunity {opp.id} matured")
            
            if opp.status != old_status:
                opp.save()
                updated_count += 1
        
        logger.info(f"Updated {updated_count} opportunity statuses")
        return {'updated': updated_count}
    
    except Exception as e:
        logger.error(f"Error updating opportunity status: {str(e)}")
        return {'error': str(e)}


@shared_task
def update_investor_portfolios():
    """
    Update all investor portfolio statistics
    Runs daily to keep portfolio data current
    """
    try:
        from investments.models import Portfolio, Investment
        from accounts.models import User
        
        # Get all users with investments
        investors = User.objects.filter(
            investments__isnull=False
        ).distinct()
        
        updated_count = 0
        
        for investor in investors:
            try:
                # Get or create portfolio
                portfolio, created = Portfolio.objects.get_or_create(user=investor)
                
                # Update statistics
                portfolio.update_stats()
                
                updated_count += 1
            
            except Exception as e:
                logger.error(f"Error updating portfolio for user {investor.id}: {str(e)}")
        
        logger.info(f"Updated {updated_count} investor portfolios")
        return {'updated': updated_count}
    
    except Exception as e:
        logger.error(f"Error in update_investor_portfolios: {str(e)}")
        return {'error': str(e)}


@shared_task
def send_investment_updates():
    """
    Send progress updates to investors
    Runs weekly to keep investors informed
    """
    try:
        from investments.models import Investment, InvestmentUpdate
        from notifications.tasks import send_sms_notification
        
        # Get active investments
        active_investments = Investment.objects.filter(
            status='active'
        ).select_related('investor', 'opportunity')
        
        updates_sent = 0
        
        # Group by opportunity for efficient processing
        from collections import defaultdict
        opp_investors = defaultdict(list)
        
        for investment in active_investments:
            opp_investors[investment.opportunity.id].append(investment.investor)
        
        # Send updates per opportunity
        for opp_id, investors in opp_investors.items():
            try:
                from investments.models import InvestmentOpportunity
                opportunity = InvestmentOpportunity.objects.get(id=opp_id)
                
                # Get latest update
                latest_update = InvestmentUpdate.objects.filter(
                    opportunity=opportunity
                ).order_by('-created_at').first()
                
                if latest_update:
                    message = (
                        f"📊 {opportunity.title}: "
                        f"{latest_update.title}. "
                        f"Progress: {latest_update.progress_percentage or 0}%"
                    )
                else:
                    # Default progress message
                    days_remaining = (opportunity.maturity_date - timezone.now().date()).days
                    message = (
                        f"📊 {opportunity.title}: "
                        f"Investment is on track. "
                        f"{days_remaining} days until maturity."
                    )
                
                # Send to all investors
                for investor in investors:
                    send_sms_notification.delay(investor.phone_number, message) #type:ignore
                    updates_sent += 1
            
            except Exception as e:
                logger.error(f"Error sending updates for opportunity {opp_id}: {str(e)}")
        
        logger.info(f"Sent {updates_sent} investment updates")
        return {'updates_sent': updates_sent}
    
    except Exception as e:
        logger.error(f"Error in send_investment_updates: {str(e)}")
        return {'error': str(e)}


@shared_task
def calculate_investment_performance():
    """
    Calculate and cache investment performance metrics
    Runs daily for analytics dashboard
    """
    try:
        from investments.models import Investment, InvestmentOpportunity
        
        # Overall platform metrics
        total_invested = Investment.objects.filter(
            status__in=['active', 'matured', 'paid_out']
        ).aggregate(total=Sum('amount_ac'))['total'] or Decimal('0')
        
        total_returned = Investment.objects.filter(
            status__in=['matured', 'paid_out']
        ).aggregate(total=Sum('actual_return_ac'))['total'] or Decimal('0')
        
        active_opportunities = InvestmentOpportunity.objects.filter(
            status__in=['open', 'funded', 'active']
        ).count()
        
        total_investors = Investment.objects.values('investor').distinct().count()
        
        # Calculate average ROI
        completed = Investment.objects.filter(
            status='paid_out',
            actual_return_ac__isnull=False
        )
        
        if completed.exists():
            avg_roi = sum(
                ((inv.actual_return_ac - inv.amount_ac) / inv.amount_ac) * 100
                for inv in completed
            ) / completed.count()
        else:
            avg_roi = 0
        
        metrics = {
            'total_invested_ac': float(total_invested),
            'total_returned_ac': float(total_returned),
            'active_opportunities': active_opportunities,
            'total_investors': total_investors,
            'average_roi_percentage': float(avg_roi),
            'updated_at': timezone.now().isoformat()
        }
        
        # Cache metrics for 24 hours
        from django.core.cache import cache
        cache.set('investment_performance_metrics', metrics, 86400)
        
        logger.info(f"Calculated investment performance metrics: {metrics}")
        return metrics
    
    except Exception as e:
        logger.error(f"Error calculating investment performance: {str(e)}")
        return {'error': str(e)}


@shared_task
def notify_investment_milestones():
    """
    Notify investors when investments reach certain milestones
    50% funded, fully funded, halfway to maturity, etc.
    """
    try:
        from investments.models import InvestmentOpportunity
        from notifications.tasks import send_bulk_notifications
        
        notifications_sent = 0
        
        # Check opportunities for milestones
        opportunities = InvestmentOpportunity.objects.filter(
            status__in=['open', 'funded', 'active']
        )
        
        for opp in opportunities:
            try:
                # Check for 50% funding milestone
                if 48 <= opp.funding_percentage < 52 and opp.status == 'open':
                    investor_ids = list(Investment.objects.filter(opportunity=opp).values_list('investor_id', flat=True))
                    message = f"🎯 {opp.title} is 50% funded! Help us reach our goal."
                    send_bulk_notifications.delay(investor_ids, message, 'sms') #type:ignore
                    notifications_sent += len(investor_ids)
                
                # Check for full funding
                elif opp.funding_percentage >= 100 and opp.status == 'funded':
                    investor_ids = list(Investment.objects.filter(opportunity=opp).values_list('investor_id', flat=True))
                    message = f"{opp.title} is fully funded! Farm operations starting soon."
                    send_bulk_notifications.delay(investor_ids, message, 'sms') #type:ignore
                    notifications_sent += len(investor_ids)
                
                # Check for halfway to maturity
                elif opp.status == 'active':
                    total_days = (opp.maturity_date - opp.funded_at.date()).days
                    days_passed = (timezone.now().date() - opp.funded_at.date()).days
                    
                    if total_days > 0 and 49 <= (days_passed / total_days * 100) <= 51:
                        investor_ids = list(Investment.objects.filter(opportunity=opp).values_list('investor_id', flat=True))
                        message = f"⏰ {opp.title} is halfway to maturity! Returns coming soon."
                        send_bulk_notifications.delay(investor_ids, message, 'sms') #type:ignore
                        notifications_sent += len(investor_ids)
            
            except Exception as e:
                logger.error(f"Error checking milestones for opportunity {opp.id}: {str(e)}")
        
        logger.info(f"Sent {notifications_sent} milestone notifications")
        return {'notifications_sent': notifications_sent}
    
    except Exception as e:
        logger.error(f"Error in notify_investment_milestones: {str(e)}")
        return {'error': str(e)}


@shared_task
def generate_investment_reports():
    """
    Generate monthly investment reports for investors
    Runs monthly on the 1st day
    """
    try:
        from investments.models import Investment, Portfolio
        from accounts.models import User
        
        # Get all investors
        investors = User.objects.filter(
            investments__isnull=False
        ).distinct()
        
        reports_generated = 0
        
        for investor in investors:
            try:
                portfolio = Portfolio.objects.get(user=investor)
                
                # Generate report data
                report = {
                    'investor': investor.get_full_name(),
                    'total_invested': float(portfolio.total_invested_ac),
                    'total_returns': float(portfolio.total_returns_ac),
                    'active_investments': portfolio.active_investments_count,
                    'matured_investments': portfolio.matured_investments_count,
                    'month': timezone.now().strftime('%B %Y')
                }
                
                # Send report via email
                from notifications.tasks import send_email_notification
                
                email_body = f"""
                Monthly Investment Report - {report['month']}
                
                Total Invested: {report['total_invested']} AC
                Total Returns: {report['total_returns']} AC
                Active Investments: {report['active_investments']}
                Matured Investments: {report['matured_investments']}
                
                Thank you for investing with AgroMentor 360!
                """
                
                if investor.email:
                    send_email_notification.delay(
                        investor.email,
                        f"Investment Report - {report['month']}",
                        email_body
                    ) #type:ignore
                    reports_generated += 1
            
            except Exception as e:
                logger.error(f"Error generating report for investor {investor.id}: {str(e)}")
        
        logger.info(f"Generated {reports_generated} investment reports")
        return {'reports_generated': reports_generated}
    
    except Exception as e:
        logger.error(f"Error in generate_investment_reports: {str(e)}")
        return {'error': str(e)}