from django.shortcuts import get_object_or_404
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from typing import Dict, Any  # Added for type hinting

from .models import User, PhoneVerification
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer,
    UserSerializer,
    ProfileUpdateSerializer
)

# Helper function to generate tokens
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

# ----------------------------------------------------------------
# Authentication Views
# ----------------------------------------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user, create their profile, and generate an ETH wallet.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Ensure user is a single User instance
        if isinstance(user, list):
            user = user[0]
        
        # Generate tokens
        tokens = get_tokens_for_user(user)
        
        # Send OTP (Simulation)
        otp = "123456" 
        PhoneVerification.objects.update_or_create(
            phone_number=user.phone_number,
            defaults={'otp_code': otp, 'is_verified': False}
        )
        
        # Safe wallet access
        wallet_address = None
        if hasattr(user, 'wallet'):
            wallet_address = user.wallet.public_key

        return Response({
            'message': 'Registration successful. Please verify your phone.',
            'user': UserSerializer(user).data,
            'tokens': tokens,
            'wallet_address': wallet_address
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Authenticate user via phone number and password.
    """
    serializer = UserLoginSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        # FIX: The editor thinks validated_data is "empty". 
        # We access it as a dict and ignore the type error.
        validated_data: Dict[str, Any] = serializer.validated_data # type: ignore
        user = validated_data.get('user')
        
        if not user:
            return Response({'error': 'User not found'}, status=status.HTTP_401_UNAUTHORIZED)
        
        tokens = get_tokens_for_user(user)
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Safe wallet access
        wallet_address = None
        if hasattr(user, 'wallet'):
            wallet_address = user.wallet.public_key

        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': tokens,
            'wallet_address': wallet_address
        })
    
    return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Blacklist the refresh token to logout.
    """
    try:
        refresh_token = request.data.get("refresh")
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"message": "Successfully logged out"}, status=status.HTTP_205_RESET_CONTENT)
    except Exception as e:
        return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    Manually refresh access token
    """
    from rest_framework_simplejwt.views import TokenRefreshView
    return TokenRefreshView.as_view()(request._request)


# ----------------------------------------------------------------
# Phone Verification
# ----------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_phone(request):
    """
    Verify the user's phone number with OTP.
    """
    otp_input = request.data.get('otp_code')
    user = request.user
    
    try:
        verification = PhoneVerification.objects.get(phone_number=user.phone_number)
        
        if verification.otp_code == otp_input:
            user.is_verified = True
            user.save()
            
            verification.is_verified = True
            verification.save()
            
            return Response({'message': 'Phone number verified successfully'})
        else:
            return Response({'error': 'Invalid OTP code'}, status=status.HTTP_400_BAD_REQUEST)
            
    except PhoneVerification.DoesNotExist:
        return Response({'error': 'No verification pending for this number'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resend_verification_code(request):
    """
    Resend OTP to the user's phone.
    """
    user = request.user
    new_otp = "123456" 
    
    PhoneVerification.objects.update_or_create(
        phone_number=user.phone_number,
        defaults={'otp_code': new_otp, 'is_verified': False}
    )
    
    return Response({'message': 'Verification code sent'})


# ----------------------------------------------------------------
# Profile Management
# ----------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    """
    Get current user profile details.
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Update profile fields.
    """
    # Safe profile access
    if hasattr(request.user, 'profile'):
        profile = request.user.profile
    else:
        from .models import UserProfile
        profile = UserProfile.objects.create(user=request.user)

    serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        
        # Update User model fields if present
        user_changed = False
        if 'first_name' in request.data:
            request.user.first_name = request.data['first_name']
            user_changed = True
        if 'last_name' in request.data:
            request.user.last_name = request.data['last_name']
            user_changed = True
            
        if user_changed:
            request.user.save()
            
        return Response({
            'message': 'Profile updated successfully',
            'user': UserSerializer(request.user).data
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change user password.
    """
    user = request.user
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not user.check_password(old_password):
        return Response({'error': 'Incorrect old password'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not new_password or len(new_password) < 6:
        return Response({'error': 'New password must be at least 6 characters'}, status=status.HTTP_400_BAD_REQUEST)
    
    user.set_password(new_password)
    user.save()
    update_session_auth_hash(request, user)
    
    return Response({'message': 'Password changed successfully'})


# ----------------------------------------------------------------
# Password Reset
# ----------------------------------------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """
    Request password reset.
    """
    # Just return success for MVP
    return Response({
        'message': 'If an account exists, a reset code has been sent.'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    """
    Reset password with code.
    """
    code = request.data.get('code')
    new_password = request.data.get('new_password')
    phone = request.data.get('phone_number')
    
    if code == "123456":
        try:
            user = User.objects.get(phone_number=phone)
            user.set_password(new_password)
            user.save()
            return Response({'message': 'Password reset successfully. Please login.'})
        except User.DoesNotExist:
            pass
            
    return Response({'error': 'Invalid code or user'}, status=status.HTTP_400_BAD_REQUEST)


# ----------------------------------------------------------------
# User Stats
# ----------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_stats(request):
    """
    Quick user stats.
    """
    user = request.user
    
    # Safe profile access
    if hasattr(user, 'profile'):
        profile = user.profile
        points = profile.total_points
        level = profile.level
        badges = len(profile.badges) if profile.badges else 0
        co2 = profile.co2_offset
    else:
        # Defaults if profile is missing
        points = 0
        level = 'Beginner'
        badges = 0
        co2 = 0.0
    
    data = {
        'joined': user.date_joined,
        'points': points,
        'level': level,
        'badges_count': badges,
        'co2_offset': co2,
        'wallet_balance_eth': '0.00', 
        'wallet_balance_agro': '0.00'
    }
    return Response(data)