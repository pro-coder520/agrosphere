"""
AgroMentor 360 - Account Serializers
Serializers for user authentication and profile management
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, UserProfile, PhoneVerification
from blockchain.ethereum_service import ethereum_service
from blockchain.models import Wallet


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    class Meta: #type:ignore
        model = UserProfile
        fields = [
            'avatar', 'city', 'state', 'address', 'latitude', 'longitude',
            'experience_level', 'farm_size', 'farming_type', 'bio', 'interests',
            'total_points', 'badges', 'level', 'co2_offset',
            'email_notifications', 'sms_notifications', 'push_notifications'
        ]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user model"""
    profile = UserProfileSerializer(read_only=True)
    
    class Meta: #type:ignore
        model = User
        fields = [
            'id', 'phone_number', 'email', 'first_name', 'last_name',
            'role', 'is_verified', 'preferred_language', 'profile',
            'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'is_verified']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    city = serializers.CharField(required=True)
    state = serializers.CharField(required=True)
    
    class Meta: # type: ignore
        model = User
        fields = [
            'phone_number', 'email', 'first_name', 'last_name',
            'password', 'password_confirm', 'role', 'preferred_language',
            'city', 'state'
        ]
    
    def validate_phone_number(self, value):
        """Validate phone number format"""
        from utils.validators import validate_nigerian_phone
        return validate_nigerian_phone(value)
    
    def validate(self, attrs):
        """Validate passwords match"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        return attrs
    
    def create(self, validated_data):
        """Create user with profile and wallet"""
        # Remove password_confirm and profile data
        validated_data.pop('password_confirm')
        city = validated_data.pop('city')
        state = validated_data.pop('state')
        
        # Create user
        user = User.objects.create(
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            email=validated_data.get('email'),
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            role=validated_data.get('role', 'farmer'),
            preferred_language=validated_data.get('preferred_language', 'en')
        )
        
        # Create profile
        UserProfile.objects.create(
            user=user,
            city=city,
            state=state
        )
        
        # Create Ethereum wallet
        try:
            wallet_data = ethereum_service.create_wallet()
            Wallet.objects.create(
                user=user,
                public_key=wallet_data['address'],
                encrypted_private_key=wallet_data['encrypted_private_key']
            )
        except Exception as e:
            # Log error but don't fail registration
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create wallet for user {user.id}: {str(e)}")
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validate credentials"""
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')
        
        if phone_number and password:
            user = authenticate(
                request=self.context.get('request'),
                phone_number=phone_number,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            
            if not user.is_active:
                raise serializers.ValidationError('Account is disabled')
            
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include phone_number and password')
        
        return attrs


class PhoneVerificationSerializer(serializers.ModelSerializer):
    """Serializer for phone verification"""
    
    class Meta: #type:ignore
        model = PhoneVerification
        fields = ['phone_number', 'otp_code']
        read_only_fields = ['otp_code']


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta: #type:ignore
        model = UserProfile
        fields = [
            'avatar', 'city', 'state', 'address',
            'experience_level', 'farm_size', 'farming_type',
            'bio', 'interests',
            'email_notifications', 'sms_notifications', 'push_notifications'
        ]