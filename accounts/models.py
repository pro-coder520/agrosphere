from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from decimal import Decimal
import uuid

from agrosphere import settings

class UserManager(BaseUserManager):
    """
    Custom user manager to handle user creation with phone or email
    """
    
    def create_user(self, phone_number, password=None, **extra_fields):
        """
        Create and save a regular user
        """
        if not phone_number:
            raise ValueError('Users must have a phone number')
        
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone_number, password=None, **extra_fields):
        """
        Create and save a superuser with admin privileges
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with phone-based authentication
    Supports multiple user roles: Farmer, Expert, Investor, Admin
    """
    
    USER_ROLE_CHOICES = [
        ('farmer', 'Farmer'),
        ('expert', 'Expert'),
        ('investor', 'Investor'),
        ('admin', 'Administrator'),
    ]
    
    # Unique identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Phone validator for Nigerian numbers (+234)
    phone_regex = RegexValidator(
        regex=r'^\+?234?\d{10,13}$',
        message="Phone number must be in format: '+2348012345678'"
    )
    
    # Authentication fields
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        unique=True,
        db_index=True,
        help_text="Primary authentication identifier"
    )
    email = models.EmailField(unique=True, null=True, blank=True)
    
    # User information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=USER_ROLE_CHOICES, default='farmer')
    
    # Account status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)  # Phone/email verification
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # User preferences
    preferred_language = models.CharField(
        max_length=10,
        choices=[
            ('en', 'English'),
            ('yo', 'Yoruba'),
            ('ig', 'Igbo'),
            ('ha', 'Hausa'),
            ('pid', 'Pidgin'),
        ],
        default='en'
    )
    
    # USSD access
    ussd_enabled = models.BooleanField(default=True)
    ussd_pin = models.CharField(max_length=4, null=True, blank=True)  # For USSD authentication
    
    objects = UserManager()
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.phone_number})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_short_name(self):
        return self.first_name
    
    @property
    def is_farmer(self):
        return self.role == 'farmer'
    
    @property
    def is_expert(self):
        return self.role == 'expert'
    
    @property
    def is_investor(self):
        return self.role == 'investor'


class UserProfile(models.Model):
    """
    Extended user profile with additional information
    """
    
    EXPERIENCE_CHOICES = [
        ('beginner', 'Beginner (0-1 year)'),
        ('intermediate', 'Intermediate (1-3 years)'),
        ('advanced', 'Advanced (3-5 years)'),
        ('expert', 'Expert (5+ years)'),
    ]
    
    FARM_SIZE_CHOICES = [
        ('mini', 'Mini/Urban (<0.5 acres)'),
        ('small', 'Small (0.5-2 acres)'),
        ('medium', 'Medium (2-10 acres)'),
        ('large', 'Large (10+ acres)'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    
    # Profile image
    avatar = models.ImageField(upload_to='profiles/avatars/', null=True, blank=True)
    
    # Location information
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    address = models.TextField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Farming information (for farmers)
    experience_level = models.CharField(
        max_length=20,
        choices=EXPERIENCE_CHOICES,
        default='beginner'
    )
    farm_size = models.CharField(
        max_length=20,
        choices=FARM_SIZE_CHOICES,
        null=True,
        blank=True
    )
    farming_type = models.CharField(
        max_length=50,
        choices=[
            ('traditional', 'Traditional Farming'),
            ('urban', 'Urban/Mini Farming'),
            ('hydroponic', 'Hydroponic'),
            ('organic', 'Organic Farming'),
            ('mixed', 'Mixed Farming'),
        ],
        null=True,
        blank=True
    )
    
    # Bio and interests
    bio = models.TextField(max_length=500, null=True, blank=True)
    interests = models.JSONField(default=list, help_text="List of farming interests")
    
    # Gamification & achievements
    total_points = models.IntegerField(default=0)
    badges = models.JSONField(default=list, help_text="Achievement badges earned")
    level = models.IntegerField(default=1)
    # SDG Impact tracking
    co2_offset = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Estimated CO2 offset in kg"
    )
    
    # Notifications
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"Profile: {self.user.get_full_name()}"
    
    def add_badge(self, badge_name):
        """
        Add an achievement badge to user profile
        """
        if badge_name not in self.badges:
            self.badges.append(badge_name)
            self.save()
    
    def add_points(self, points):
        """
        Add points and check for level up
        """
        self.total_points += points
        # Level up every 1000 points
        new_level = (self.total_points // 1000) + 1
        if new_level > self.level:
            self.level = new_level
            self.add_badge(f'Level {new_level} Achiever')
        self.save()


class PhoneVerification(models.Model):
    """
    Model to handle phone number verification via OTP
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verifications')
    phone_number = models.CharField(max_length=17)
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'phone_verifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Verification for {self.phone_number}"
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @classmethod
    def generate_otp(cls):
        """
        Generate a 6-digit OTP code
        """
        import random
        return str(random.randint(100000, 999999))