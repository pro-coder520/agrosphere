from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid


class Farm(models.Model):
    """
    Represents a farm (can be traditional farm or urban mini-farm)
    """
    
    FARM_TYPE_CHOICES = [
        ('traditional', 'Traditional Farm'),
        ('urban', 'Urban/Mini Farm'),
        ('hydroponic', 'Hydroponic'),
        ('greenhouse', 'Greenhouse'),
        ('rooftop', 'Rooftop Farm'),
        ('balcony', 'Balcony Garden'),
        ('container', 'Container Farm'),
    ]
    
    SIZE_CHOICES = [
        ('mini', 'Mini (<0.5 acres)'),
        ('small', 'Small (0.5-2 acres)'),
        ('medium', 'Medium (2-10 acres)'),
        ('large', 'Large (10-50 acres)'),
        ('xlarge', 'Extra Large (50+ acres)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='farms'
    )
    
    # Farm details
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    farm_type = models.CharField(max_length=20, choices=FARM_TYPE_CHOICES)
    size = models.CharField(max_length=20, choices=SIZE_CHOICES)
    size_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Size in acres",
        validators=[MinValueValidator(0.01)]
    )
    crops = models.TextField(max_length=30)
    
    # Location
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Soil information
    soil_type = models.CharField(
        max_length=50,
        choices=[
            ('loamy', 'Loamy'),
            ('sandy', 'Sandy'),
            ('clay', 'Clay'),
            ('silt', 'Silt'),
            ('peaty', 'Peaty'),
            ('chalky', 'Chalky'),
            ('unknown', 'Unknown'),
        ],
        default='unknown'
    )
    soil_ph = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(14)],
        help_text="Soil pH level (0-14)"
    )
    
    # Farm images
    cover_image = models.ImageField(upload_to='farms/covers/', null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)  # Verified by platform
    
    # Investment-related (for farm co-ownership feature)
    open_for_investment = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'farms'
        verbose_name = 'Farm'
        verbose_name_plural = 'Farms'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['city', 'state']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.owner.get_full_name()}"
    
    @property
    def total_crops(self):
        return self.crops.exclude(status__in=['failed', 'harvested']).count()


class Crop(models.Model):
    """
    Represents a crop planted on a farm
    """
    
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('planted', 'Planted'),
        ('growing', 'Growing'),
        ('flowering', 'Flowering'),
        ('harvesting', 'Ready for Harvest'),
        ('harvested', 'Harvested'),
        ('failed', 'Failed'),
    ]
    
    SEASON_CHOICES = [
        ('dry', 'Dry Season'),
        ('rainy', 'Rainy Season'),
        ('all_year', 'All Year Round'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='crops')
    
    # Crop information
    name = models.CharField(max_length=200, help_text="e.g., Tomatoes, Maize, Pepper")
    category = models.CharField(
        max_length=50,
        choices=[
            ('vegetables', 'Vegetables'),
            ('fruits', 'Fruits'),
            ('grains', 'Grains'),
            ('legumes', 'Legumes'),
            ('tubers', 'Tubers'),
            ('herbs', 'Herbs'),
            ('cash_crops', 'Cash Crops'),
        ]
    )
    variety = models.CharField(max_length=200, null=True, blank=True)
    
    # Planting details
    plant_date = models.DateField()
    expected_harvest_date = models.DateField()
    actual_harvest_date = models.DateField(null=True, blank=True)
    
    # Area and quantity
    area_planted = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Area in square meters"
    )
    quantity_planted = models.IntegerField(help_text="Number of seeds/seedlings")
    expected_yield = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Expected yield in kg"
    )
    actual_yield = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual yield in kg"
    )
    
    # Growing conditions
    season = models.CharField(max_length=20, choices=SEASON_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    
    # Crop images
    images = models.JSONField(default=list, help_text="List of image URLs")
    
    # AI-generated insights
    ai_recommendations = models.JSONField(
        default=dict,
        help_text="AI-generated growing tips and recommendations"
    )
    disease_alerts = models.JSONField(default=list, help_text="Disease detection alerts")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crops'
        verbose_name = 'Crop'
        verbose_name_plural = 'Crops'
        ordering = ['-plant_date']
        indexes = [
            models.Index(fields=['farm', 'status']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.name} on {self.farm.name}"
    
    @property
    def days_to_harvest(self):
        """Calculate days remaining until expected harvest"""
        if self.status in ['harvested', 'failed']:
            return 0
        delta = self.expected_harvest_date - timezone.now().date()
        return max(0, delta.days)
    
    @property
    def days_since_planting(self):
        """Calculate days since crop was planted"""
        delta = timezone.now().date() - self.plant_date
        return delta.days


class FarmTask(models.Model):
    """
    Tasks and activities for farm management
    """
    
    TASK_TYPE_CHOICES = [
        ('watering', 'Watering'),
        ('fertilizing', 'Fertilizing'),
        ('weeding', 'Weeding'),
        ('spraying', 'Pest Control/Spraying'),
        ('pruning', 'Pruning'),
        ('harvesting', 'Harvesting'),
        ('planting', 'Planting'),
        ('soil_prep', 'Soil Preparation'),
        ('inspection', 'Inspection'),
        ('other', 'Other'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='tasks')
    crop = models.ForeignKey(
        Crop,
        on_delete=models.CASCADE,
        related_name='tasks',
        null=True,
        blank=True
    )
    
    # Task details
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Scheduling
    due_date = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Reminder sent status
    reminder_sent = models.BooleanField(default=False)
    
    # Notes and attachments
    notes = models.TextField(null=True, blank=True)
    attachments = models.JSONField(default=list, help_text="List of attachment URLs")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'farm_tasks'
        verbose_name = 'Farm Task'
        verbose_name_plural = 'Farm Tasks'
        ordering = ['due_date', '-priority']
        indexes = [
            models.Index(fields=['farm', 'status']),
            models.Index(fields=['due_date']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.farm.name}"
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if self.status in ['completed', 'cancelled']:
            return False
        return timezone.now() > self.due_date


class DiseaseDetection(models.Model):
    """
    AI-powered disease detection from crop images
    """
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='disease_detections')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Image analysis
    image = models.ImageField(upload_to='disease_detection/')
    
    # AI Detection results
    disease_name = models.CharField(max_length=200, null=True, blank=True)
    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="AI confidence percentage (0-100)"
    )
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, null=True, blank=True)
    
    # AI recommendations
    ai_analysis = models.TextField(help_text="Full AI analysis from Gemini")
    treatment_recommendations = models.JSONField(
        default=list,
        help_text="List of recommended treatments"
    )
    preventive_measures = models.JSONField(
        default=list,
        help_text="Preventive measures for future"
    )
    
    # Expert verification (optional)
    verified_by_expert = models.BooleanField(default=False)
    expert_notes = models.TextField(null=True, blank=True)
    
    # Timestamps
    detected_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'disease_detections'
        verbose_name = 'Disease Detection'
        verbose_name_plural = 'Disease Detections'
        ordering = ['-detected_at']
    
    def __str__(self):
        return f"Disease detection for {self.crop.name} - {self.disease_name or 'Analyzing'}"


class WeatherAlert(models.Model):
    """
    Weather-based alerts for farms
    """
    
    ALERT_TYPE_CHOICES = [
        ('rain', 'Heavy Rain'),
        ('drought', 'Drought Warning'),
        ('heat', 'Extreme Heat'),
        ('cold', 'Cold Weather'),
        ('storm', 'Storm Warning'),
        ('frost', 'Frost Warning'),
    ]
    
    SEVERITY_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('alert', 'Alert'),
        ('emergency', 'Emergency'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='weather_alerts')
    
    # Alert details
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Weather data
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    humidity = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rainfall = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    wind_speed = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Recommendations
    action_required = models.TextField(help_text="Recommended actions for farmer")
    
    # Status
    is_active = models.BooleanField(default=True)
    acknowledged = models.BooleanField(default=False)
    
    # Timestamps
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'weather_alerts'
        verbose_name = 'Weather Alert'
        verbose_name_plural = 'Weather Alerts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.alert_type} alert for {self.farm.name}"