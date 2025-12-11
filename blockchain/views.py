from rest_framework import status, viewsets
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction as db_transaction
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum
from .models import Wallet, Transaction, TokenPurchase, PriceHistory
from .ethereum_service import ethereum_service
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet(request):
    """
    Get user's Ethereum wallet information with AC and Naira balances
    
    GET /api/v1/blockchain/wallet/
    """
    try:
        wallet = request.user.wallet
        
        # Get current conversion rate
        conversion_rate = Decimal(str(settings.ETHEREUM_CONFIG['AGROCOIN_TO_NAIRA_RATE']))
        
        # Sync blockchain balance if enabled
        if settings.ENABLE_WEB3 and not settings.DEMO_MODE:
            try:
                blockchain_balance = ethereum_service.get_token_balance(wallet.public_key)
                wallet.agrocoin_balance = blockchain_balance
                wallet.update_naira_equivalent()
                
                eth_balance = ethereum_service.get_eth_balance(wallet.public_key)
                wallet.eth_balance = eth_balance
                wallet.last_sync = timezone.now()
                wallet.save()
            except Exception as e:
                logger.warning(f"Failed to sync blockchain balance: {str(e)}")
        
        return Response({
            'wallet_address': wallet.public_key,
            'agrocoin_balance': float(wallet.agrocoin_balance),
            'naira_equivalent': float(wallet.naira_equivalent),
            'eth_balance': float(wallet.eth_balance),
            'conversion_rate': float(conversion_rate),
            'rate_display': f'1 AC = ₦{conversion_rate}',
            'is_verified': wallet.is_verified,
            'last_sync': wallet.last_sync,
            'network': settings.ETHEREUM_CONFIG['NETWORK']
        }, status=status.HTTP_200_OK)
    
    except Wallet.DoesNotExist:
        return Response({
            'error': 'Wallet not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_tokens(request):
    """
    Purchase AgroCoin (ERC-20) tokens with Naira
    
    POST /api/v1/blockchain/purchase-tokens/
    Body: {
        "naira_amount": 5000,
        "payment_method": "paystack"
    }
    """
    try:
        naira_amount = Decimal(str(request.data.get('naira_amount', 0)))
        payment_method = request.data.get('payment_method', 'paystack')
        
        # Validate minimum purchase
        if naira_amount < 100:
            return Response({
                'error': 'Minimum purchase amount is ₦100'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate AgroCoin amount
        conversion_rate = Decimal(str(settings.ETHEREUM_CONFIG['AGROCOIN_TO_NAIRA_RATE']))
        agrocoin_amount = naira_amount / conversion_rate
        
        # Generate payment reference
        import uuid
        payment_reference = f'AGM-{uuid.uuid4().hex[:12].upper()}'
        
        # Create token purchase record
        purchase = TokenPurchase.objects.create(
            user=request.user,
            naira_amount=naira_amount,
            agrocoin_amount=agrocoin_amount,
            conversion_rate=conversion_rate,
            payment_method=payment_method,
            payment_reference=payment_reference,
            status='pending'
        )
        
        # In production, integrate with Paystack/Flutterwave here
        # For hackathon demo, simulate successful payment
        if settings.DEMO_MODE:
            with db_transaction.atomic():
                purchase.status = 'completed'
                purchase.completed_at = timezone.now()
                purchase.save()
                
                # Credit user's wallet
                wallet = request.user.wallet
                wallet.add_balance(agrocoin_amount)
                
                # Create transaction record
                txn = Transaction.objects.create(
                    to_wallet=wallet,
                    transaction_type='purchase',
                    amount=agrocoin_amount,
                    naira_value=naira_amount,
                    status='confirmed',
                    description=f'Token purchase: ₦{naira_amount} → {agrocoin_amount} AC',
                    confirmed_at=timezone.now(),
                    ethereum_tx_hash=f'0xdemo{uuid.uuid4().hex[:60]}',  # Demo hash
                    metadata={
                        'payment_method': payment_method,
                        'payment_reference': payment_reference
                    }
                )
                purchase.transaction = txn
                purchase.save()
            
            return Response({
                'success': True,
                'message': 'Token purchase successful',
                'purchase_id': str(purchase.id),
                'agrocoin_purchased': float(agrocoin_amount),
                'naira_paid': float(naira_amount),
                'conversion_rate': float(conversion_rate),
                'new_balance': float(wallet.agrocoin_balance),
                'new_balance_naira': float(wallet.naira_equivalent),
                'transaction_hash': txn.ethereum_tx_hash
            }, status=status.HTTP_201_CREATED)
        
        else:
            # Real payment integration
            return Response({
                'payment_reference': payment_reference,
                'payment_url': f'https://payment-gateway.com/pay/{payment_reference}',
                'amount': float(naira_amount),
                'currency': 'NGN'
            }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Token purchase error: {str(e)}")
        return Response({
            'error': 'Token purchase failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer_tokens(request):
    """
    Transfer AgroCoin (ERC-20) to another user
    
    POST /api/v1/blockchain/transfer/
    Body: {
        "recipient_phone": "+2348012345678",
        "amount": 50,
        "description": "Payment for tomatoes"
    }
    """
    try:
        recipient_phone = request.data.get('recipient_phone')
        amount = Decimal(str(request.data.get('amount', 0)))
        description = request.data.get('description', 'Token transfer')
        
        # Validate amount
        if amount <= 0:
            return Response({
                'error': 'Invalid amount'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get sender's wallet
        sender_wallet = request.user.wallet
        
        # Check sufficient balance
        if not sender_wallet.has_sufficient_balance(amount):
            return Response({
                'error': 'Insufficient balance',
                'your_balance': float(sender_wallet.agrocoin_balance),
                'required': float(amount)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find recipient
        from accounts.models import User
        try:
            recipient = User.objects.get(phone_number=recipient_phone)
            recipient_wallet = Wallet.objects.get(user=recipient)
        except User.DoesNotExist:
            return Response({
                'error': f'User with phone {recipient_phone} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Cannot transfer to self
        if recipient == request.user:
            return Response({
                'error': 'Cannot transfer to yourself'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Execute transfer
        with db_transaction.atomic():
            # Perform blockchain transfer
            transfer_result = ethereum_service.transfer_tokens(
                from_wallet=sender_wallet,
                to_wallet=recipient_wallet,
                amount=amount,
                description=description
            )
            
            # Calculate Naira value
            conversion_rate = Decimal(str(settings.ETHEREUM_CONFIG['AGROCOIN_TO_NAIRA_RATE']))
            naira_value = amount * conversion_rate
            
            # Create transaction record
            txn = Transaction.objects.create(
                from_wallet=sender_wallet,
                to_wallet=recipient_wallet,
                transaction_type='transfer',
                amount=amount,
                naira_value=naira_value,
                ethereum_tx_hash=transfer_result['transaction_hash'],
                status='confirmed',
                description=description,
                confirmed_at=timezone.now()
            )
            
            logger.info(f"Transfer: {amount} AC from {request.user.phone_number} to {recipient_phone}")
        
        return Response({
            'success': True,
            'message': 'Transfer successful',
            'transaction_id': str(txn.id),
            'amount': float(amount),
            'naira_value': float(naira_value),
            'recipient': recipient.get_full_name(),
            'recipient_phone': recipient_phone,
            'transaction_hash': transfer_result['transaction_hash'],
            'new_balance': float(sender_wallet.agrocoin_balance),
            'new_balance_naira': float(sender_wallet.naira_equivalent),
            'network': settings.ETHEREUM_CONFIG['NETWORK']
        }, status=status.HTTP_201_CREATED)
    
    except ValueError as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Transfer error: {str(e)}")
        return Response({
            'error': 'Transfer failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_history(request):
    """
    Get user's transaction history
    
    GET /api/v1/blockchain/transactions/?page=1&limit=20&type=all
    """
    try:
        wallet = request.user.wallet
        
        # Query parameters
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('limit', 20))
        txn_type = request.query_params.get('type', 'all')
        
        # Get transactions
        outgoing = Transaction.objects.filter(from_wallet=wallet)
        incoming = Transaction.objects.filter(to_wallet=wallet)
        
        if txn_type != 'all':
            outgoing = outgoing.filter(transaction_type=txn_type)
            incoming = incoming.filter(transaction_type=txn_type)
        
        # Combine and order
        from itertools import chain
        all_txns = sorted(
            chain(outgoing, incoming),
            key=lambda x: x.created_at,
            reverse=True
        )
        
        # Pagination
        start = (page - 1) * limit
        end = start + limit
        paginated_txns = all_txns[start:end]
        
        # Format response
        transactions = []
        for txn in paginated_txns:
            is_incoming = txn.to_wallet == wallet
            
            transactions.append({
                'id': str(txn.id),
                'type': txn.transaction_type,
                'amount': float(txn.amount),
                'naira_value': float(txn.naira_value),
                'direction': 'incoming' if is_incoming else 'outgoing',
                'from': txn.from_wallet.user.get_full_name() if txn.from_wallet else 'System',
                'to': txn.to_wallet.user.get_full_name() if txn.to_wallet else 'System',
                'description': txn.description,
                'status': txn.status,
                'transaction_hash': txn.ethereum_tx_hash,
                'block_number': txn.block_number,
                'gas_used': txn.gas_used,
                'created_at': txn.created_at.isoformat(),
                'confirmed_at': txn.confirmed_at.isoformat() if txn.confirmed_at else None
            })
        
        return Response({
            'transactions': transactions,
            'page': page,
            'limit': limit,
            'total': len(all_txns),
            'has_more': end < len(all_txns)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Transaction history error: {str(e)}")
        return Response({
            'error': 'Failed to fetch transaction history'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_conversion_rate(request):
    """
    Get current AgroCoin to Naira conversion rate
    
    GET /api/v1/blockchain/conversion-rate/
    """
    conversion_rate = Decimal(str(settings.ETHEREUM_CONFIG['AGROCOIN_TO_NAIRA_RATE']))
    
    # Get recent rate history
    history = PriceHistory.objects.all()[:10]
    
    return Response({
        'current_rate': float(conversion_rate),
        'display': f'1 AC = ₦{conversion_rate}',
        'reverse': f'₦1 = {1/conversion_rate:.4f} AC',
        'last_updated': timezone.now().isoformat(),
        'blockchain': 'Ethereum',
        'token_standard': 'ERC-20',
        'history': [
            {
                'rate': float(h.rate),
                'timestamp': h.timestamp.isoformat()
            }
            for h in history
        ]
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_transaction(request):
    """
    Verify a blockchain transaction on Ethereum
    
    POST /api/v1/blockchain/verify/
    Body: {"transaction_hash": "0x..."}
    """
    try:
        tx_hash = request.data.get('transaction_hash')
        
        if not tx_hash:
            return Response({
                'error': 'Transaction hash required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify on blockchain
        verification = ethereum_service.verify_transaction(tx_hash)
        
        # Check local database
        try:
            txn = Transaction.objects.get(ethereum_tx_hash=tx_hash)
            verification['database_status'] = txn.status
            verification['amount'] = float(txn.amount)
            verification['type'] = txn.transaction_type
        except Transaction.DoesNotExist:
            verification['database_status'] = 'not_found'
        
        return Response(verification, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Verification error: {str(e)}")
        return Response({
            'error': 'Verification failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estimate_gas_fee(request):
    """
    Estimate gas fees for Ethereum transactions
    
    GET /api/v1/blockchain/estimate-gas/?type=token_transfer
    """
    try:
        tx_type = request.query_params.get('type', 'token_transfer')
        
        gas_estimate = ethereum_service.estimate_gas_fee(tx_type)
        
        return Response({
            'transaction_type': tx_type,
            'gas_estimate': gas_estimate,
            'network': settings.ETHEREUM_CONFIG['NETWORK']
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Gas estimation error: {str(e)}")
        return Response({
            'error': 'Failed to estimate gas',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wallet_stats(request):
    """
    Get wallet statistics and insights
    
    GET /api/v1/blockchain/stats/
    """
    try:
        wallet = request.user.wallet
        
        # Calculate stats
        total_received = Transaction.objects.filter(
            to_wallet=wallet,
            status='confirmed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        total_sent = Transaction.objects.filter(
            from_wallet=wallet,
            status='confirmed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        total_purchases = TokenPurchase.objects.filter(
            user=request.user,
            status='completed'
        ).aggregate(
            total_ngn=Sum('naira_amount'),
            total_ac=Sum('agrocoin_amount')
        )
        
        return Response({
            'current_balance': {
                'agrocoin': float(wallet.agrocoin_balance),
                'naira': float(wallet.naira_equivalent),
                'eth': float(wallet.eth_balance)
            },
            'lifetime_stats': {
                'total_received': float(total_received),
                'total_sent': float(total_sent),
                'total_purchased_ngn': float(total_purchases['total_ngn'] or 0),
                'total_purchased_ac': float(total_purchases['total_ac'] or 0)
            },
            'wallet_info': {
                'address': wallet.public_key,
                'created_at': wallet.created_at.isoformat(),
                'is_verified': wallet.is_verified,
                'network': settings.ETHEREUM_CONFIG['NETWORK']
            },
            'blockchain': {
                'network': settings.ETHEREUM_CONFIG['NETWORK'],
                'token_standard': 'ERC-20',
                'contract_address': settings.ETHEREUM_CONFIG.get('AGROCOIN_CONTRACT_ADDRESS', 'Not deployed')
            }
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Wallet stats error: {str(e)}")
        return Response({
            'error': 'Failed to fetch wallet stats'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)