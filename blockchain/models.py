from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

class Wallet(models.Model):
    """
    User's Ethereum wallet for AgroCoin (ERC-20) transactions
    Each user has one wallet automatically created on registration
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    
    # Ethereum wallet address (public key)
    public_key = models.CharField(
        max_length=42,  # Ethereum addresses are 42 chars (0x + 40 hex)
        unique=True,
        db_index=True,
        help_text="Ethereum wallet address"
    )
    
    # Encrypted private key (stored securely)
    # In production, use HSM or secure key management service like AWS KMS
    encrypted_private_key = models.TextField(
        help_text="Encrypted with user's PIN/password"
    )
    
    # AgroCoin (ERC-20 token) balance
    agrocoin_balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="AgroCoin token balance"
    )
    
    # Naira equivalent (cached for quick display)
    naira_equivalent = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Cached value: AC balance * conversion rate"
    )
    
    # ETH balance (for gas fees)
    eth_balance = models.DecimalField(
        max_digits=20,
        decimal_places=18,  # ETH has 18 decimals
        default=Decimal('0.00'),
        help_text="Ether balance for transaction fees"
    )
    
    # Wallet status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'wallets'
        verbose_name = 'Wallet'
        verbose_name_plural = 'Wallets'
        indexes = [
            models.Index(fields=['public_key']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"Wallet: {self.user.get_full_name()} - {self.agrocoin_balance} AC"
    
    def update_naira_equivalent(self):
        """
        Update cached naira equivalent based on current conversion rate
        """
        rate = Decimal(settings.ETHEREUM_CONFIG['AGROCOIN_TO_NAIRA_RATE'])
        self.naira_equivalent = self.agrocoin_balance * rate
        self.save(update_fields=['naira_equivalent', 'updated_at'])
    
    def has_sufficient_balance(self, amount):
        """
        Check if wallet has sufficient AgroCoin balance
        """
        return self.agrocoin_balance >= Decimal(str(amount))
    
    def add_balance(self, amount):
        """
        Add AgroCoin to wallet balance
        """
        self.agrocoin_balance += Decimal(str(amount))
        self.update_naira_equivalent()
    
    def deduct_balance(self, amount):
        """
        Deduct AgroCoin from wallet balance
        """
        if not self.has_sufficient_balance(amount):
            raise ValueError("Insufficient balance")
        self.agrocoin_balance -= Decimal(str(amount))
        self.update_naira_equivalent()


class Transaction(models.Model):
    """
    Record of all AgroCoin (ERC-20) transactions on Ethereum
    """
    
    TRANSACTION_TYPE_CHOICES = [
        ('purchase', 'Token Purchase'),
        ('transfer', 'Transfer'),
        ('payment', 'Payment'),
        ('reward', 'Reward'),
        ('refund', 'Refund'),
        ('investment', 'Investment'),
        ('investment_return', 'Investment Return'),
        ('expert_payment', 'Expert Payment'),
        ('marketplace_purchase', 'Marketplace Purchase'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Transaction parties
    from_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='outgoing_transactions',
        null=True,
        blank=True
    )
    to_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='incoming_transactions',
        null=True,
        blank=True
    )
    
    # Transaction details
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Naira value at time of transaction
    naira_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Amount in NGN at conversion rate during transaction"
    )
    
    # Ethereum blockchain data
    ethereum_tx_hash = models.CharField(
        max_length=66,  # 0x + 64 hex characters
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text="Ethereum transaction hash"
    )
    block_number = models.BigIntegerField(null=True, blank=True)
    gas_used = models.BigIntegerField(null=True, blank=True)
    gas_price_gwei = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Gas price in Gwei"
    )
    
    # Transaction status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Metadata
    description = models.TextField(help_text="Transaction description")
    metadata = models.JSONField(
        default=dict,
        help_text="Additional transaction data"
    )
    
    # Platform fee (5% commission)
    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'transactions'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['from_wallet', 'created_at']),
            models.Index(fields=['to_wallet', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['ethereum_tx_hash']),
        ]
    
    def __str__(self):
        return f"{self.transaction_type}: {self.amount} AC - {self.status}"
    
    def calculate_platform_fee(self):
        """
        Calculate 5% platform commission
        """
        if self.transaction_type in ['payment', 'expert_payment', 'marketplace_purchase']:
            self.platform_fee = self.amount * Decimal(str(settings.PLATFORM_COMMISSION_RATE))
        return self.platform_fee
    
    def get_net_amount(self):
        """
        Get amount after platform fee deduction
        """
        return self.amount - self.platform_fee


class TokenPurchase(models.Model):
    """
    Records of AgroCoin (ERC-20) purchases with Naira
    """
    
    PAYMENT_METHOD_CHOICES = [
        ('paystack', 'Paystack'),
        ('flutterwave', 'Flutterwave'),
        ('bank_transfer', 'Bank Transfer'),
        ('ussd', 'USSD Payment'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='token_purchases'
    )
    
    # Purchase details
    naira_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('100.00'))],
        help_text="Amount paid in NGN"
    )
    agrocoin_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="AgroCoin tokens purchased"
    )
    conversion_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="1 AC = X NGN at time of purchase"
    )
    
    # Payment information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_reference = models.CharField(max_length=200, unique=True, db_index=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Related transaction
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_record'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'token_purchases'
        verbose_name = 'Token Purchase'
        verbose_name_plural = 'Token Purchases'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Purchase: ₦{self.naira_amount} -> {self.agrocoin_amount} AC"


class PriceHistory(models.Model):
    """
    Track AgroCoin to Naira conversion rate over time
    """
    rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="1 AC = X NGN"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'price_history'
        verbose_name = 'Price History'
        verbose_name_plural = 'Price History'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"1 AC = ₦{self.rate} at {self.timestamp}"


class GasFeeRecord(models.Model):
    """
    Track Ethereum gas fees for transactions
    """
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name='gas_fee_record'
    )
    
    # Gas details
    gas_limit = models.BigIntegerField(help_text="Gas limit set for transaction")
    gas_used = models.BigIntegerField(help_text="Actual gas used")
    gas_price_gwei = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Gas price in Gwei"
    )
    
    # Total fee
    total_fee_eth = models.DecimalField(
        max_digits=20,
        decimal_places=18,
        help_text="Total gas fee in ETH"
    )
    total_fee_naira = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Gas fee converted to Naira"
    )
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'gas_fee_records'
        verbose_name = 'Gas Fee Record'
        verbose_name_plural = 'Gas Fee Records'
    
    def __str__(self):
        return f"Gas fee: {self.total_fee_eth} ETH (₦{self.total_fee_naira})"