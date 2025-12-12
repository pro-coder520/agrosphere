"""
AgroMentor 360 - Custom Exception Handler
Provides consistent error responses across the API
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # If response is None, handle it as an unhandled exception
    if response is None:
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        
        return Response({
            'error': 'Internal server error',
            'detail': str(exc) if settings.DEBUG else 'An unexpected error occurred',
            'status_code': 500
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Customize the response data structure
    custom_response_data = {
        'error': True,
        'status_code': response.status_code,
    }
    
    # Handle different types of errors
    if isinstance(response.data, dict):
        if 'detail' in response.data:
            custom_response_data['message'] = response.data['detail']
        else:
            custom_response_data['errors'] = response.data
    elif isinstance(response.data, list):
        custom_response_data['errors'] = response.data
    else:
        custom_response_data['message'] = str(response.data)
    
    # Log the error
    logger.warning(
        f"API Error: {response.status_code} - {custom_response_data.get('message', 'Unknown error')}"
    )
    
    response.data = custom_response_data
    return response


class InsufficientBalanceError(Exception):
    """Raised when wallet has insufficient balance"""
    pass


class BlockchainError(Exception):
    """Raised when blockchain operation fails"""
    pass


class InvalidTransactionError(Exception):
    """Raised when transaction is invalid"""
    pass


class WalletNotFoundError(Exception):
    """Raised when wallet is not found"""
    pass