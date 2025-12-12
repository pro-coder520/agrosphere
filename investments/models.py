from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.utils import timezone
import uuid

class FarmInvestment(models.Model):
    """
    Tracks financial investments made by users into farms or specific crop cycles.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('active', 'Active'),
        ('matured', 'Matured/Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    investor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='investments' # Matches: user.investments.all()
    )
    farm = models.ForeignKey(
        'farming.Farm',
        on_delete=models.CASCADE,
        related_name='investments'
    )
    # Optional: Link to specific crop cycle if investment is crop-specific
    crop = models.ForeignKey(
        'farming.Crop',
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='investors'
    )

    # Financials
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Amount invested in base currency"
    )
    expected_roi = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        help_text="Expected Return on Investment percentage (e.g. 15.00 for 15%)",
        default=Decimal(0.00)
    )
    projected_returns = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        null=True, 
        blank=True,
        help_text="Calculated payout amount"
    )
    expected_return_ac = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_return_ac = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Status & Dates
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        db_index=True
    )
    start_date = models.DateField(null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Farm Investment"
        verbose_name_plural = "Farm Investments"
        indexes = [
            models.Index(fields=['investor', 'status']),
        ]

    def __str__(self):
        return f"{self.investor} - {self.farm.name} ({self.amount})"

    def save(self, *args, **kwargs):
        """Auto-calculate projected returns if ROI is set"""
        if self.amount and self.expected_roi and not self.projected_returns:
            multiplier = 1 + (self.expected_roi / 100)
            self.projected_returns = self.amount * multiplier
        super().save(*args, **kwargs)

class InvestmentReturn(models.Model):
    """
    Tracks financial returns distributed to investors.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    investment = models.ForeignKey(
        FarmInvestment,
        on_delete=models.CASCADE,
        related_name='returns'  # Matches the serializer's source='returns'
    )
    
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Amount distributed in AC"
    )
    
    distribution_date = models.DateField(default=timezone.now)
    
    # Optional: Transaction reference if paid on-chain
    transaction_hash = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-distribution_date']
        verbose_name = "Investment Return"
        verbose_name_plural = "Investment Returns"

    def __str__(self):
        return f"{self.amount} AC return for {self.investment}"

class InvestmentOpportunity(models.Model):
    """
    Farm investment opportunities open to investors
    """
    
    STATUS_CHOICES = [
        ('open', 'Open for Investment'),
        ('funded', 'Fully Funded'),
        ('active', 'Active'),
        ('matured', 'Matured'),
        ('closed', 'Closed'),
    ]
    
    FARM_CATEGORY_CHOICES = [
        ('poultry', 'Poultry Farming'),
        ('fishery', 'Fish Farming'),
        ('crops', 'Crop Farming'),
        ('livestock', 'Livestock'),
        ('mixed', 'Mixed Farming'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(
        'farming.Farm',
        on_delete=models.CASCADE,
        related_name='investment_opportunities'
    )
    farm_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_investment_opportunities'
    )
    
    # Investment details
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=FARM_CATEGORY_CHOICES)
    
    # Financial details (in AgroCoin)
    target_amount_ac = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('50'))],
        help_text="Target investment amount in AgroCoin"
    )
    target_amount_naira = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Target amount in Naira (for display)"
    )
    
    minimum_investment_ac = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('50'),  # ₦5,000 at 1 AC = ₦100
        help_text="Minimum investment per investor"
    )
    minimum_investment_naira = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('5000'),
        help_text="Minimum in Naira (for display)"
    )
    
    current_amount_ac = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0'),
        help_text="Amount raised so far"
    )
    
    # Returns
    expected_roi_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Expected return on investment percentage"
    )
    
    # Duration
    duration_months = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Investment duration in months"
    )
    maturity_date = models.DateField(help_text="Expected maturity date")
    
    # Images and documents
    cover_image = models.ImageField(upload_to='investments/covers/')
    gallery = models.JSONField(default=list, help_text="Additional images")
    
    # Blockchain verification
    smart_contract_address = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Ethereum smart contract for investment"
    )
    
    # Stats
    total_investors = models.IntegerField(default=0)
    funding_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0'),
        help_text="Percentage of target funded"
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # SDG Impact
    co2_offset_potential = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        help_text="Estimated CO2 offset in kg"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    funded_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'investment_opportunities'
        verbose_name = 'Investment Opportunity'
        verbose_name_plural = 'Investment Opportunities'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.funding_percentage}% funded"
    
    def save(self, *args, **kwargs):
        """Auto-calculate Naira values and funding percentage"""
        conversion_rate = Decimal(str(settings.ETHEREUM_CONFIG['AGROCOIN_TO_NAIRA_RATE']))
        self.target_amount_naira = self.target_amount_ac * conversion_rate
        self.minimum_investment_naira = self.minimum_investment_ac * conversion_rate
        
        # Calculate funding percentage
        if self.target_amount_ac > 0:
            self.funding_percentage = (self.current_amount_ac / self.target_amount_ac) * 100
        
        # Update status based on funding
        if self.funding_percentage >= 100 and self.status == 'open':
            self.status = 'funded'
            self.funded_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def is_fully_funded(self):
        return self.funding_percentage >= 100
    
    @property
    def remaining_amount_ac(self):
        return max(Decimal('0'), self.target_amount_ac - self.current_amount_ac)
    
    @property
    def days_until_maturity(self):
        if self.status in ['matured', 'closed']:
            return 0
        delta = self.maturity_date - timezone.now().date()
        return max(0, delta.days)


class Investment(models.Model):
    """
    Individual investment by a user
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('matured', 'Matured'),
        ('paid_out', 'Paid Out'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(
        InvestmentOpportunity,
        on_delete=models.CASCADE,
        related_name='investments'
    )
    investor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='investments'
    )
    
    # Investment amount
    amount_ac = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Investment amount in AgroCoin"
    )
    amount_naira = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Investment amount in Naira"
    )
    
    # Expected returns
    expected_return_ac = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Expected return in AgroCoin"
    )
    expected_return_naira = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Expected return in Naira"
    )
    
    # Actual returns (filled at maturity)
    actual_return_ac = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    actual_return_naira = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Payment transaction
    payment_transaction = models.OneToOneField(
        'blockchain.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='investment_payment'
    )
    
    # Payout transaction
    payout_transaction = models.OneToOneField(
        'blockchain.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='investment_payout'
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    invested_at = models.DateTimeField(auto_now_add=True)
    maturity_date = models.DateField()
    paid_out_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'investments'
        verbose_name = 'Investment'
        verbose_name_plural = 'Investments'
        ordering = ['-invested_at']
        indexes = [
            models.Index(fields=['investor', 'status']),
            models.Index(fields=['opportunity', 'status']),
        ]
    
    def __str__(self):
        return f"{self.investor.get_full_name()} - {self.amount_ac} AC in {self.opportunity.title}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate Naira values"""
        conversion_rate = Decimal(str(settings.ETHEREUM_CONFIG['AGROCOIN_TO_NAIRA_RATE']))
        self.amount_naira = self.amount_ac * conversion_rate
        self.expected_return_naira = self.expected_return_ac * conversion_rate
        
        if self.actual_return_ac:
            self.actual_return_naira = self.actual_return_ac * conversion_rate
        
        # Set maturity date from opportunity
        if not self.maturity_date:
            self.maturity_date = self.opportunity.maturity_date
        
        super().save(*args, **kwargs)
    
    def calculate_expected_return(self):
        """Calculate expected return based on ROI percentage"""
        roi = self.opportunity.expected_roi_percentage / Decimal('100')
        self.expected_return_ac = self.amount_ac * (Decimal('1') + roi)
        self.save()
    
    @property
    def profit_ac(self):
        """Calculate profit (return - principal)"""
        if self.actual_return_ac:
            return self.actual_return_ac - self.amount_ac
        return self.expected_return_ac - self.amount_ac
    
    @property
    def profit_naira(self):
        """Calculate profit in Naira"""
        conversion_rate = Decimal(str(settings.ETHEREUM_CONFIG['AGROCOIN_TO_NAIRA_RATE']))
        return self.profit_ac * conversion_rate
    
    @property
    def is_matured(self):
        """Check if investment has matured"""
        return timezone.now().date() >= self.maturity_date


class InvestmentUpdate(models.Model):
    """
    Progress updates on investment opportunities
    """
    
    UPDATE_TYPE_CHOICES = [
        ('milestone', 'Milestone Achieved'),
        ('progress', 'Progress Update'),
        ('financial', 'Financial Report'),
        ('harvest', 'Harvest Update'),
        ('challenge', 'Challenge/Issue'),
        ('general', 'General Update'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(
        InvestmentOpportunity,
        on_delete=models.CASCADE,
        related_name='updates'
    )
    
    # Update content
    update_type = models.CharField(max_length=20, choices=UPDATE_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # Media
    images = models.JSONField(default=list, help_text="Update images")
    
    # Metrics
    progress_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'investment_updates'
        verbose_name = 'Investment Update'
        verbose_name_plural = 'Investment Updates'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.opportunity.title}"


class Portfolio(models.Model):
    """
    Investor's portfolio summary
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='investment_portfolio'
    )
    
    # Portfolio stats
    total_invested_ac = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0')
    )
    total_invested_naira = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0')
    )
    
    total_returns_ac = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0')
    )
    total_returns_naira = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0')
    )
    
    active_investments_count = models.IntegerField(default=0)
    matured_investments_count = models.IntegerField(default=0)
    
    # SDG Impact
    total_co2_offset = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'investment_portfolios'
        verbose_name = 'Portfolio'
        verbose_name_plural = 'Portfolios'
    
    def __str__(self):
        return f"Portfolio: {self.user.get_full_name()}"
    
    def update_stats(self):
        """Recalculate portfolio statistics"""
        from django.db.models import Sum, Count
        
        investments = Investment.objects.filter(investor=self.user)
        
        # Calculate totals
        stats = investments.aggregate(
            total_invested=Sum('amount_ac'),
            total_returns=Sum('actual_return_ac'),
            active_count=Count('id', filter=models.Q(status='active')),
            matured_count=Count('id', filter=models.Q(status__in=['matured', 'paid_out']))
        )
        
        self.total_invested_ac = stats['total_invested'] or Decimal('0')
        self.total_returns_ac = stats['total_returns'] or Decimal('0')
        self.active_investments_count = stats['active_count'] or 0
        self.matured_investments_count = stats['matured_count'] or 0
        
        # Calculate Naira equivalents
        conversion_rate = Decimal(str(settings.ETHEREUM_CONFIG['AGROCOIN_TO_NAIRA_RATE']))
        self.total_invested_naira = self.total_invested_ac * conversion_rate
        self.total_returns_naira = self.total_returns_ac * conversion_rate
        
        self.save()
    
    @property
    def total_profit_ac(self):
        return self.total_returns_ac - self.total_invested_ac
    
    @property
    def total_profit_naira(self):
        return self.total_returns_naira - self.total_invested_naira