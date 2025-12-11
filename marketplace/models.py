from django.db import models
from django.db.models import Avg, Count
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid


class Product(models.Model):
    """
    Farm produce listed for sale in marketplace
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('available', 'Available'),
        ('sold_out', 'Sold Out'),
        ('suspended', 'Suspended'),
    ]
    
    UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('ton', 'Ton'),
        ('bag', 'Bag'),
        ('basket', 'Basket'),
        ('bunch', 'Bunch'),
        ('unit', 'Unit'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='products'
    )
    farm = models.ForeignKey(
        'farming.Farm',
        on_delete=models.CASCADE,
        related_name='products',
        null=True,
        blank=True
    )
    
    # Product details
    name = models.CharField(max_length=200)
    category = models.CharField(
        max_length=50,
        choices=[
            ('vegetables', 'Vegetables'),
            ('fruits', 'Fruits'),
            ('grains', 'Grains'),
            ('legumes', 'Legumes'),
            ('tubers', 'Tubers'),
            ('herbs', 'Herbs'),
            ('processed', 'Processed Foods'),
        ]
    )
    description = models.TextField()
    
    # Pricing - Display both AgroCoin and Naira
    price_agrocoin = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Price in AgroCoin (AC)"
    )
    price_naira = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Price in Naira (auto-calculated from AC)"
    )
    
    # Quantity
    quantity_available = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    minimum_order = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.0'),
        help_text="Minimum order quantity"
    )
    
    # Product images
    primary_image = models.ImageField(upload_to='marketplace/products/')
    additional_images = models.JSONField(
        default=list,
        help_text="Additional product images"
    )
    
    # Quality and certification
    organic_certified = models.BooleanField(default=False)
    quality_grade = models.CharField(
        max_length=10,
        choices=[
            ('A', 'Grade A'),
            ('B', 'Grade B'),
            ('C', 'Grade C'),
        ],
        null=True,
        blank=True
    )
    
    # Blockchain traceability
    harvest_date = models.DateField()
    blockchain_traceability_id = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Solana transaction hash for traceability"
    )
    
    # Location
    location_city = models.CharField(max_length=100)
    location_state = models.CharField(max_length=100)
    
    # Delivery options
    delivery_available = models.BooleanField(default=True)
    pickup_available = models.BooleanField(default=True)
    delivery_fee_naira = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Ratings
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_reviews = models.IntegerField(default=0)
    
    # Stats
    total_sold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    view_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'marketplace_products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['location_city']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.price_agrocoin} AC (₦{self.price_naira})"
    
    def save(self, *args, **kwargs):
        """Auto-calculate Naira price from AgroCoin price"""
        conversion_rate = Decimal(str(settings.SOLANA_CONFIG['AGROCOIN_TO_NAIRA_RATE']))
        self.price_naira = self.price_agrocoin * conversion_rate
        super().save(*args, **kwargs)

    reviews: models.Manager['Review']

    def update_rating(self):
        """Recalculate average rating efficiently using DB aggregation"""
        # This runs 1 fast SQL query instead of loading 1000s of objects
        stats = self.reviews.aggregate(
            average=Avg('rating'), 
            count=Count('id')
        )
        
        # Safe handling if there are no reviews yet
        self.average_rating = stats['average'] or Decimal('0.00')
        self.total_reviews = stats['count'] or 0
        
        # Update only the specific fields to avoid overwriting other changes
        self.save(update_fields=['average_rating', 'total_reviews'])
    
    @property
    def is_available(self):
        """Check if product has stock"""
        return self.status == 'available' and self.quantity_available > 0


class Order(models.Model):
    """
    Customer orders from marketplace paid with AgroCoin
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    DELIVERY_METHOD_CHOICES = [
        ('delivery', 'Home Delivery'),
        ('pickup', 'Pickup from Farm'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, db_index=True)
    
    # Parties
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sales'
    )
    
    # Order items (stored as JSON for simplicity in MVP)
    items = models.JSONField(
        help_text="List of items: [{product_id, name, quantity, price_ac, price_ngn}]"
    )
    
    # Pricing breakdown (AgroCoin and Naira for display)
    subtotal_ac = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Subtotal in AgroCoin"
    )
    subtotal_naira = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Subtotal in Naira (for display)"
    )
    
    delivery_fee_ac = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    delivery_fee_naira = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    platform_fee_ac = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="5% platform commission"
    )
    
    total_ac = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total amount paid in AgroCoin"
    )
    total_naira = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total amount in Naira (for display)"
    )
    
    # Payment
    payment_transaction = models.OneToOneField(
        'blockchain.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marketplace_order'
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_METHOD_CHOICES,
        default='delivery'
    )
    delivery_address = models.TextField()
    delivery_city = models.CharField(max_length=100)
    delivery_state = models.CharField(max_length=100)
    delivery_phone = models.CharField(max_length=17)
    
    # Tracking
    tracking_number = models.CharField(max_length=100, null=True, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    actual_delivery = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Notes
    buyer_notes = models.TextField(null=True, blank=True)
    seller_notes = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'marketplace_orders'
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['order_number']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.total_ac} AC (₦{self.total_naira})"
    
    def save(self, *args, **kwargs):
        """Generate order number if not exists"""
        if not self.order_number:
            import random
            import string
            timestamp = self.created_at.strftime('%Y%m%d') if self.created_at else ''
            random_str = ''.join(random.choices(string.digits, k=6))
            self.order_number = f'AGM{timestamp}{random_str}'
        super().save(*args, **kwargs)
    
    def calculate_totals(self):
        """Calculate order totals in AC and Naira"""
        conversion_rate = Decimal(str(settings.SOLANA_CONFIG['AGROCOIN_TO_NAIRA_RATE']))
        
        # Calculate subtotal
        self.subtotal_ac = sum(Decimal(str(item['price_ac'])) * Decimal(str(item['quantity'])) 
                               for item in self.items)
        self.subtotal_naira = self.subtotal_ac * conversion_rate
        
        # Platform fee (5%)
        self.platform_fee_ac = self.subtotal_ac * Decimal(str(settings.PLATFORM_COMMISSION_RATE))
        
        # Total
        self.total_ac = self.subtotal_ac + self.delivery_fee_ac
        self.total_naira = self.total_ac * conversion_rate
        
        self.save()


class Review(models.Model):
    """
    Product reviews and ratings
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='reviews')
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    
    # Review content
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    title = models.CharField(max_length=200)
    comment = models.TextField()
    
    # Media
    images = models.JSONField(default=list, help_text="Review images")
    
    # Verification
    verified_purchase = models.BooleanField(default=False)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'marketplace_reviews'
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        ordering = ['-created_at']
        unique_together = ['product', 'reviewer']  # One review per product per user
    
    def __str__(self):
        return f"{self.rating}★ review for {self.product.name}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update product rating
        self.product.update_rating()


class Cart(models.Model):
    """
    Shopping cart for buyers (temporary storage before checkout)
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    
    # Cart items stored as JSON
    items = models.JSONField(
        default=list,
        help_text="[{product_id, quantity, price_ac, price_ngn}]"
    )
    
    # Calculated totals (AC and Naira)
    total_ac = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_naira = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'marketplace_carts'
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
    
    def __str__(self):
        return f"Cart for {self.user.get_full_name()}"
    
    def calculate_total(self):
        """Calculate cart total in AC and Naira"""
        conversion_rate = Decimal(str(settings.SOLANA_CONFIG['AGROCOIN_TO_NAIRA_RATE']))
        
        self.total_ac = sum(
            Decimal(str(item['price_ac'])) * Decimal(str(item['quantity']))
            for item in self.items
        )
        self.total_naira = self.total_ac * conversion_rate
        self.save()
    
    def add_item(self, product, quantity):
        """Add product to cart"""
        # Check if item already in cart
        for item in self.items:
            if item['product_id'] == str(product.id):
                item['quantity'] += quantity
                self.calculate_total()
                return
        
        # Add new item
        self.items.append({
            'product_id': str(product.id),
            'name': product.name,
            'quantity': float(quantity),
            'price_ac': float(product.price_agrocoin),
            'price_ngn': float(product.price_naira),
            'image': product.primary_image.url if product.primary_image else None
        })
        self.calculate_total()
    
    def remove_item(self, product_id):
        """Remove item from cart"""
        self.items = [item for item in self.items if item['product_id'] != product_id]
        self.calculate_total()
    
    def clear(self):
        """Clear all items from cart"""
        self.items = []
        self.total_ac = Decimal('0.00')
        self.total_naira = Decimal('0.00')
        self.save()