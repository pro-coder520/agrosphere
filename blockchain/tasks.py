from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.db import models
from decimal import Decimal
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5)
def sync_pending_transactions(self):
    """
    Sync pending Ethereum transactions and update their status
    Runs every 5 minutes via Celery Beat
    """
    try:
        from blockchain.models import Transaction
        from blockchain.ethereum_service import ethereum_service
        
        if not getattr(settings, 'ENABLE_WEB3', False) or getattr(settings, 'DEMO_MODE', False):
            logger.info("Blockchain sync skipped (demo mode or disabled)")
            return {'status': 'skipped', 'reason': 'demo_mode'}
        
        # Get pending transactions (last 24 hours to avoid old stuck txs)
        pending_txs = Transaction.objects.filter(
            status__in=['pending', 'processing'],
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).order_by('-created_at')[:50]  # Batch limit
        
        if not pending_txs:
            logger.info("No pending transactions to sync")
            return {'synced': 0, 'message': 'No pending transactions'}
        
        synced_count = 0
        confirmed_count = 0
        failed_count = 0
        
        for tx in pending_txs:
            try:
                if not tx.ethereum_tx_hash:
                    logger.warning(f"Transaction {tx.id} has no tx hash")
                    continue
                
                # Verify transaction on blockchain
                verification = ethereum_service.verify_transaction(tx.ethereum_tx_hash)
                
                if verification.get('confirmed'):
                    # Transaction confirmed
                    tx.status = 'confirmed'
                    tx.confirmed_at = timezone.now()
                    tx.block_number = verification.get('block_number')
                    tx.gas_used = verification.get('gas_used')
                    tx.save(update_fields=['status', 'confirmed_at', 'block_number', 'gas_used'])
                    
                    confirmed_count += 1
                    
                    # Trigger post-confirmation tasks
                    # FIX: Add type: ignore because 'delay' is added dynamically by Celery
                    process_confirmed_transaction.delay(str(tx.id)) # type: ignore
                
                elif verification.get('status') == 'failed':
                    # Transaction failed
                    tx.status = 'failed'
                    tx.save(update_fields=['status'])
                    
                    failed_count += 1
                    
                    # Handle failed transaction
                    handle_failed_transaction.delay(str(tx.id)) # type: ignore
                
                synced_count += 1
            
            except Exception as e:
                logger.error(f"Error syncing transaction {tx.id}: {str(e)}")
        
        logger.info(f"Synced {synced_count} transactions: {confirmed_count} confirmed, {failed_count} failed")
        return {
            'synced': synced_count,
            'confirmed': confirmed_count,
            'failed': failed_count
        }
    
    except Exception as e:
        logger.error(f"Error in sync_pending_transactions: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task
def process_confirmed_transaction(transaction_id):
    """
    Process actions after transaction confirmation
    Send notifications and update related records
    """
    try:
        from blockchain.models import Transaction
        from notifications.tasks import send_sms_notification
        
        tx = Transaction.objects.select_related('from_wallet__user', 'to_wallet__user').get(id=transaction_id)
        
        # Send confirmation notification
        if tx.from_wallet:
            message = f"✅ Transaction confirmed! {tx.amount} AC sent successfully. TxHash: {tx.ethereum_tx_hash[:10]}..."
            send_sms_notification.delay(tx.from_wallet.user.phone_number, message) # type: ignore
        
        if tx.to_wallet:
            message = f"✅ You received {tx.amount} AC! TxHash: {tx.ethereum_tx_hash[:10]}..."
            send_sms_notification.delay(tx.to_wallet.user.phone_number, message) # type: ignore
        
        # Update related records based on transaction type
        if tx.transaction_type == 'marketplace_purchase':
            update_marketplace_order.delay(transaction_id) # type: ignore
        elif tx.transaction_type == 'investment':
            update_investment_record.delay(transaction_id) # type: ignore
        elif tx.transaction_type == 'expert_payment':
            notify_expert_payment.delay(transaction_id) # type: ignore
        
        logger.info(f"Processed confirmed transaction {transaction_id}")
        return {'status': 'processed'}
    
    except Exception as e:
        logger.error(f"Error processing confirmed transaction {transaction_id}: {str(e)}")
        return {'status': 'failed', 'error': str(e)}


@shared_task
def handle_failed_transaction(transaction_id):
    """
    Handle failed transaction - refund and notify user
    """
    try:
        from blockchain.models import Transaction
        from notifications.tasks import send_sms_notification
        
        tx = Transaction.objects.select_related('from_wallet__user').get(id=transaction_id)
        
        # Refund the amount to sender's wallet (if applicable)
        if tx.from_wallet and tx.transaction_type != 'purchase':
            tx.from_wallet.add_balance(tx.amount)
            logger.info(f"Refunded {tx.amount} AC to wallet {tx.from_wallet.public_key}")
        
        # Notify user
        if tx.from_wallet:
            message = f"❌ Transaction failed and has been refunded. Please try again or contact support."
            send_sms_notification.delay(tx.from_wallet.user.phone_number, message) # type: ignore
        
        logger.info(f"Handled failed transaction {transaction_id}")
        return {'status': 'refunded'}
    
    except Exception as e:
        logger.error(f"Error handling failed transaction {transaction_id}: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task(bind=True, max_retries=3)
def sync_wallet_balances(self):
    """
    Sync wallet balances from Ethereum blockchain
    Runs periodically to ensure accuracy
    """
    try:
        from blockchain.models import Wallet
        from blockchain.ethereum_service import ethereum_service
        
        if not getattr(settings, 'ENABLE_WEB3', False) or getattr(settings, 'DEMO_MODE', False):
            return {'status': 'skipped', 'reason': 'demo_mode'}
        
        # Get wallets that need syncing (last synced > 1 hour ago)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        wallets = Wallet.objects.filter(
            is_active=True
        ).filter(
            models.Q(last_sync__lt=one_hour_ago) | models.Q(last_sync__isnull=True)
        )[:100]  # Batch limit
        
        synced_count = 0
        
        for wallet in wallets:
            try:
                # Get blockchain balance
                blockchain_balance = ethereum_service.get_token_balance(wallet.public_key)
                
                # Update if different
                if blockchain_balance != wallet.agrocoin_balance:
                    wallet.agrocoin_balance = blockchain_balance
                    wallet.update_naira_equivalent()
                    logger.info(f"Updated wallet {wallet.public_key} balance to {blockchain_balance} AC")
                
                # Update ETH balance for gas
                eth_balance = ethereum_service.get_balance(wallet.public_key)
                wallet.eth_balance = eth_balance
                
                wallet.last_sync = timezone.now()
                wallet.save(update_fields=['agrocoin_balance', 'naira_equivalent', 'eth_balance', 'last_sync'])
                
                synced_count += 1
            
            except Exception as e:
                logger.error(f"Error syncing wallet {wallet.public_key}: {str(e)}")
        
        logger.info(f"Synced {synced_count} wallet balances")
        return {'synced': synced_count}
    
    except Exception as e:
        logger.error(f"Error in sync_wallet_balances: {str(e)}")
        raise self.retry(exc=e, countdown=300)


@shared_task
def update_gas_price_cache():
    """
    Update cached Ethereum gas prices
    Runs every 10 minutes for efficient gas estimation
    """
    try:
        from blockchain.ethereum_service import ethereum_service
        
        if not getattr(settings, 'ENABLE_WEB3', False) or getattr(settings, 'DEMO_MODE', False):
            return {'status': 'skipped'}
        
        # Get current gas prices
        gas_estimate = ethereum_service.estimate_gas_fee('token_transfer')
        
        # Cache for 10 minutes
        cache.set('current_gas_price', gas_estimate, 600)
        
        # Alert if gas price is very high
        if gas_estimate.get('gas_price_gwei', 0) > 100:
            logger.warning(f"High gas prices detected: {gas_estimate['gas_price_gwei']} Gwei")
        
        logger.info(f"Updated gas price cache: {gas_estimate.get('gas_price_gwei')} Gwei")
        return {'gas_price_gwei': gas_estimate.get('gas_price_gwei')}
    
    except Exception as e:
        logger.error(f"Error updating gas price cache: {str(e)}")
        return {'error': str(e)}


@shared_task
def update_marketplace_order(transaction_id):
    """
    Update marketplace order after successful payment
    """
    try:
        from blockchain.models import Transaction
        from marketplace.models import Order
        
        tx = Transaction.objects.get(id=transaction_id)
        
        # Find related order
        order = Order.objects.filter(
            payment_transaction=tx
        ).first()
        
        if order:
            order.status = 'paid'
            order.paid_at = timezone.now()
            order.save(update_fields=['status', 'paid_at'])
            
            logger.info(f"Updated order {order.order_number} to paid status")
            return {'status': 'updated', 'order_id': str(order.id)}
        
        return {'status': 'no_order_found'}
    
    except Exception as e:
        logger.error(f"Error updating marketplace order: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def update_investment_record(transaction_id):
    """
    Update investment record after successful payment
    """
    try:
        from blockchain.models import Transaction
        from investments.models import Investment
        
        tx = Transaction.objects.get(id=transaction_id)
        
        # Find related investment
        investment = Investment.objects.filter(
            payment_transaction=tx
        ).first()
        
        if investment:
            investment.status = 'active'
            investment.save(update_fields=['status'])
            
            # Update opportunity funding
            opportunity = investment.opportunity
            opportunity.current_amount_ac += investment.amount_ac
            opportunity.total_investors += 1
            opportunity.save()
            
            logger.info(f"Updated investment {investment.id} to active status")
            return {'status': 'updated', 'investment_id': str(investment.id)}
        
        return {'status': 'no_investment_found'}
    
    except Exception as e:
        logger.error(f"Error updating investment record: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def notify_expert_payment(transaction_id):
    """
    Notify expert of successful payment
    """
    try:
        from blockchain.models import Transaction
        from notifications.tasks import send_sms_notification
        
        tx = Transaction.objects.select_related('to_wallet__user').get(id=transaction_id)
        
        if tx.to_wallet:
            message = f"💰 Payment received: {tx.amount} AC (₦{tx.naira_value}) for consultation"
            send_sms_notification.delay(tx.to_wallet.user.phone_number, message) # type: ignore
            
            logger.info(f"Notified expert of payment {transaction_id}")
            return {'status': 'notified'}
        
        return {'status': 'no_recipient'}
    
    except Exception as e:
        logger.error(f"Error notifying expert payment: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def record_price_history():
    """
    Record AgroCoin to Naira conversion rate history
    Runs daily for historical tracking
    """
    try:
        from blockchain.models import PriceHistory
        
        # Safely get rate or default to 1000
        rate_config = getattr(settings, 'ETHEREUM_CONFIG', {}).get('AGROCOIN_TO_NAIRA_RATE', 1000)
        current_rate = Decimal(str(rate_config))
        
        # Check if rate already recorded today
        today = timezone.now().date()
        exists = PriceHistory.objects.filter(
            timestamp__date=today
        ).exists()
        
        if not exists:
            PriceHistory.objects.create(rate=current_rate)
            logger.info(f"Recorded price history: 1 AC = ₦{current_rate}")
            return {'status': 'recorded', 'rate': float(current_rate)}
        
        return {'status': 'already_recorded'}
    
    except Exception as e:
        logger.error(f"Error recording price history: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def cleanup_old_transactions():
    """
    Archive or clean up very old transaction records
    Runs monthly for database optimization
    """
    try:
        from blockchain.models import Transaction
        
        # Archive transactions older than 1 year
        one_year_ago = timezone.now() - timedelta(days=365)
        
        old_txs = Transaction.objects.filter(
            created_at__lt=one_year_ago,
            status__in=['confirmed', 'failed', 'cancelled']
        )
        
        count = old_txs.count()
        
        for tx in old_txs:
            if tx.metadata is None:
                tx.metadata = {}
            tx.metadata['archived'] = True
            tx.save(update_fields=['metadata'])
        
        logger.info(f"Archived {count} old transactions")
        return {'archived': count}
    
    except Exception as e:
        logger.error(f"Error cleaning up old transactions: {str(e)}")
        return {'status': 'error', 'error': str(e)}