"""
AgroMentor 360 - Blockchain Serializers
Serializers for wallet, transactions, and token operations
"""

from rest_framework import serializers
from .models import Wallet, Transaction, TokenPurchase, PriceHistory
from django.conf import settings
from decimal import Decimal


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for wallet"""
    conversion_rate = serializers.SerializerMethodField()
    network = serializers.SerializerMethodField()
    
    class Meta: #type:ignore
        model = Wallet
        fields = [
            'id', 'public_key', 'agrocoin_balance', 'naira_equivalent',
            'eth_balance', 'is_active', 'is_verified', 'conversion_rate',
            'network', 'created_at', 'last_sync'
        ]
        read_only_fields = ['id', 'public_key', 'created_at']
    
    def get_conversion_rate(self, obj):
        return float(settings.ETHEREUM_CONFIG['AGROCOIN_TO_NAIRA_RATE'])
    
    def get_network(self, obj):
        return settings.ETHEREUM_CONFIG['NETWORK']


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for transactions"""
    from_address = serializers.SerializerMethodField()
    to_address = serializers.SerializerMethodField()
    direction = serializers.SerializerMethodField()
    
    class Meta: #type:ignore
        model = Transaction
        fields = [
            'id', 'transaction_type', 'amount', 'naira_value',
            'from_address', 'to_address', 'direction',
            'ethereum_tx_hash', 'block_number', 'gas_used', 'gas_price_gwei',
            'status', 'description', 'platform_fee', 'metadata',
            'created_at', 'confirmed_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_from_address(self, obj):
        return obj.from_wallet.public_key if obj.from_wallet else None
    
    def get_to_address(self, obj):
        return obj.to_wallet.public_key if obj.to_wallet else None
    
    def get_direction(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            return None
        
        user_wallet = getattr(request.user, 'wallet', None)
        if not user_wallet:
            return None
        
        if obj.to_wallet == user_wallet:
            return 'incoming'
        elif obj.from_wallet == user_wallet:
            return 'outgoing'
        return None


class TokenPurchaseSerializer(serializers.ModelSerializer):
    """Serializer for token purchases"""
    
    class Meta: #type:ignore
        model = TokenPurchase
        fields = [
            'id', 'naira_amount', 'agrocoin_amount', 'conversion_rate',
            'payment_method', 'payment_reference', 'status',
            'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'agrocoin_amount', 'conversion_rate', 'payment_reference', 'created_at']


class PriceHistorySerializer(serializers.ModelSerializer):
    """Serializer for price history"""
    
    class Meta: #type:ignore
        model = PriceHistory
        fields = ['rate', 'timestamp']


class TokenTransferSerializer(serializers.Serializer):
    """Serializer for token transfers"""
    recipient_phone = serializers.CharField()
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, min_value=Decimal('0.01'))
    description = serializers.CharField(required=False, allow_blank=True)
    
    def validate_amount(self, value):
        """Validate transfer amount"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        
        max_transfer = Decimal(str(settings.ETHEREUM_CONFIG.get('MAX_TRANSFER_AMOUNT', 10000)))
        if value > max_transfer:
            raise serializers.ValidationError(f"Amount exceeds maximum transfer limit of {max_transfer} AC")
        
        return value