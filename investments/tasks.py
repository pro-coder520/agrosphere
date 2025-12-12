from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum, F
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_matured_investments(self):
    """
    Process investments that have reached maturity date
    Runs daily at midnight via Celery Beat
    """
    try:
        # Import FarmInvestment explicitly to match your models
        from investments.models import FarmInvestment as Investment 
        from blockchain.models import Transaction
        from notifications.tasks import send_sms_notification
        
        today = timezone.now().date()
        matured_investments = Investment.objects.filter(
            maturity_date=today,
            status='active'
        ).select_related('investor', 'opportunity')
        
        if not matured_investments:
            logger.info("No investments matured today")
            return {'processed': 0}
        
        processed_count = 0
        total_paid_out = Decimal('0')
        
        for investment in matured_investments:
            try:
                # Use getattr to safely access fields if migration isn't run yet
                expected_return = getattr(investment, 'expected_return_ac', investment.amount * Decimal('1.1'))
                principal = getattr(investment, 'amount_ac', investment.amount)
                
                profit = expected_return - principal
                
                # FIX 1: Update fields safely (silence linter for dynamically added fields)
                investment.actual_return_ac = expected_return # type: ignore
                investment.status = 'matured'
                investment.save(update_fields=['status']) 
                # Note: Add 'actual_return_ac' to update_fields only after migration
                
                # Create payout transaction
                # Safely get rate
                rate_config = getattr(settings, 'ETHEREUM_CONFIG', {}).get('AGROCOIN_TO_NAIRA_RATE', 1000)
                conversion_rate = Decimal(str(rate_config))
                
                # Ensure wallet exists
                if not hasattr(investment.investor, 'wallet'):
                    logger.error(f"Investor {investment.investor.id} has no wallet")
                    continue

                payout_tx = Transaction.objects.create(
                    to_wallet=investment.investor.wallet,
                    transaction_type='investment_return',
                    amount=expected_return,
                    naira_value=expected_return * conversion_rate,
                    status='confirmed',
                    description=f'Investment return: {investment.opportunity.title}', # type: ignore
                    confirmed_at=timezone.now(),
                    metadata={
                        'investment_id': str(investment.id),
                        'profit': float(profit)
                    }
                )
                
                # Credit wallet
                investment.investor.wallet.add_balance(expected_return)
                
                # FIX 2: Link transaction safely
                investment.payout_transaction = payout_tx # type: ignore
                investment.paid_out_at = timezone.now() # type: ignore
                investment.save()
                
                # Notification
                message = f"🎉 Investment matured! Return: {expected_return} AC (Profit: {profit} AC)"
                send_sms_notification.delay(investment.investor.phone_number, message) # type: ignore
                
                processed_count += 1
                total_paid_out += expected_return
            
            except Exception as e:
                logger.error(f"Error processing investment {investment.id}: {str(e)}")
        
        # Trigger opportunity update
        update_opportunity_status.delay() # type: ignore
        
        return {'processed': processed_count, 'total_paid_out': float(total_paid_out)}
    
    except Exception as e:
        logger.error(f"Error in process_matured_investments: {str(e)}")
        raise self.retry(exc=e, countdown=300)


@shared_task
def update_opportunity_status():
    """Update investment opportunity statuses"""
    try:
        from investments.models import InvestmentOpportunity
        
        updated_count = 0
        opportunities = InvestmentOpportunity.objects.filter(
            status__in=['open', 'funded', 'active']
        )
        
        for opp in opportunities:
            old_status = opp.status
            
            # Check funding
            if opp.funding_percentage >= 100 and opp.status == 'open':
                opp.status = 'funded'
                opp.funded_at = timezone.now()
            
            # Check maturity (Safety check for None dates)
            elif opp.status in ['funded', 'active']:
                if opp.maturity_date and timezone.now().date() >= opp.maturity_date:
                    opp.status = 'matured'
            
            if opp.status != old_status:
                opp.save()
                updated_count += 1
        
        return {'updated': updated_count}
    except Exception as e:
        return {'error': str(e)}


@shared_task
def notify_investment_milestones():
    """Notify investors of milestones"""
    try:
        from investments.models import InvestmentOpportunity, FarmInvestment
        from notifications.tasks import send_bulk_notifications
        
        notifications_sent = 0
        opportunities = InvestmentOpportunity.objects.filter(
            status__in=['open', 'funded', 'active']
        )
        
        for opp in opportunities:
            try:
                # 50% Funding
                if 48 <= opp.funding_percentage < 52 and opp.status == 'open':
                    investor_ids = list(opp.investments.values_list('investor_id', flat=True)) # type: ignore
                    message = f"🎯 {opp.title} is 50% funded!"
                    send_bulk_notifications.delay(investor_ids, message, 'sms') # type: ignore
                    notifications_sent += len(investor_ids)
                
                # Fully Funded
                elif opp.funding_percentage >= 100 and opp.status == 'funded':
                    investor_ids = list(opp.investments.values_list('investor_id', flat=True)) # type: ignore
                    message = f"{opp.title} is fully funded!"
                    send_bulk_notifications.delay(investor_ids, message, 'sms') # type: ignore
                    notifications_sent += len(investor_ids)
                
                # Halfway to Maturity (FIXED DATE MATH)
                elif opp.status == 'active':
                    # FIX 3: Check if funded_at exists before doing math
                    if opp.funded_at and opp.maturity_date:
                        total_days = (opp.maturity_date - opp.funded_at.date()).days
                        days_passed = (timezone.now().date() - opp.funded_at.date()).days
                        
                        if total_days > 0 and 49 <= (days_passed / total_days * 100) <= 51:
                            investor_ids = list(opp.investments.values_list('investor_id', flat=True)) # type: ignore
                            message = f"⏰ {opp.title} is halfway to maturity!"
                            send_bulk_notifications.delay(investor_ids, message, 'sms') # type: ignore
                            notifications_sent += len(investor_ids)
            
            except Exception as e:
                logger.error(f"Error checking milestones for {opp.id}: {str(e)}")
        
        return {'notifications_sent': notifications_sent}
    
    except Exception as e:
        return {'error': str(e)}
