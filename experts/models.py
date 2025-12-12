"""
AgroMentor 360 - Expert Models
Expert profiles and consultation management
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

class Expert(models.Model):
    """
    Agricultural expert profile for providing consultations
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expert_profile'
    )
    
    # Professional Details
    specializations = models.JSONField(
        default=list, 
        help_text="List of agricultural specializations (e.g., ['Crop Science', 'Livestock'])"
    )
    bio = models.TextField()
    years_of_experience = models.PositiveIntegerField(default=0)
    certifications = models.JSONField(
        default=list, 
        help_text="List of certifications held by the expert"
    )
    
    # Service Details
    consultation_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Fee per consultation session"
    )
    
    # Metrics
    rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    is_verified = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-rating', '-years_of_experience']
        verbose_name = "Expert"
        verbose_name_plural = "Experts"

    def __str__(self):
        return f"Expert: {self.user.get_full_name() or self.user.username}"

class ExpertProfile(models.Model):
    """
    Extended profile for expert users
    """
    
    SPECIALIZATION_CHOICES = [
        ('soil_science', 'Soil Science'),
        ('veterinary', 'Veterinary Medicine'),
        ('agronomy', 'Agronomy'),
        ('crop_science', 'Crop Science'),
        ('farm_management', 'Farm Management'),
        ('irrigation', 'Irrigation'),
        ('pest_control', 'Pest Control'),
        ('organic_farming', 'Organic Farming'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expert_profile'
    )
    
    # Specialization
    specialization = models.CharField(max_length=50, choices=SPECIALIZATION_CHOICES)
    years_of_experience = models.IntegerField(validators=[MinValueValidator(0)])
    
    # Credentials
    certifications = models.JSONField(default=list, help_text="List of certifications")
    education = models.TextField()
    
    # Availability
    is_available = models.BooleanField(default=True)
    consultation_fee_ac = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Consultation fee in AgroCoin"
    )
    consultation_fee_naira = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Consultation fee in Naira (auto-calculated)"
    )
    
    # Ratings
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_consultations = models.IntegerField(default=0)
    
    # Bio
    bio = models.TextField()
    profile_image = models.ImageField(upload_to='experts/profiles/', null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'expert_profiles'
        verbose_name = 'Expert Profile'
        verbose_name_plural = 'Expert Profiles'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_specialization_display()}"  # type: ignore
    
    def save(self, *args, **kwargs):
        """Auto-calculate Naira fee"""
        conversion_rate = Decimal(str(settings.ETHEREUM_CONFIG['AGROCOIN_TO_NAIRA_RATE']))
        self.consultation_fee_naira = self.consultation_fee_ac * conversion_rate
        super().save(*args, **kwargs)


class Consultation(models.Model):
    """
    Consultation booking between farmer and expert
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Parties
    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='consultations_as_farmer'
    )
    expert = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='consultations_as_expert'
    )
    
    # Details
    topic = models.CharField(max_length=200)
    description = models.TextField()
    scheduled_time = models.DateTimeField()
    duration_minutes = models.IntegerField(default=30)
    
    # Payment
    fee_ac = models.DecimalField(max_digits=10, decimal_places=2)
    fee_naira = models.DecimalField(max_digits=15, decimal_places=2)
    payment_transaction = models.OneToOneField(
        'blockchain.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consultation_payment'
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reminder_sent = models.BooleanField(default=False)
    
    # Notes
    farmer_notes = models.TextField(null=True, blank=True)
    expert_notes = models.TextField(null=True, blank=True)
    
    # Rating
    rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    review = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'consultations'
        verbose_name = 'Consultation'
        verbose_name_plural = 'Consultations'
        ordering = ['-scheduled_time']
    
    def __str__(self):
        return f"{self.farmer.get_full_name()} → {self.expert.get_full_name()}: {self.topic}"


class ConsultationMessage(models.Model):
    """
    Messages exchanged during a consultation
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='consultation_messages'
    )
    
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    
    # Optional: Read status
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['sent_at']

    def __str__(self):
        return f"Message by {self.sender} at {self.sent_at}"