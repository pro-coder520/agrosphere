import re
import os
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_nigerian_phone(value):
    """
    Validates that a phone number is a valid Nigerian mobile number.
    
    Accepts formats:
    - +2348012345678 (International)
    - 2348012345678 (International no plus)
    - 08012345678 (Local)
    
    Returns the normalized international format: +2348012345678
    """
    if not value:
        raise ValidationError(_('Phone number is required'))

    # 1. Sanitize: Remove spaces, hyphens, and parentheses
    # e.g., "(080) 123-4567" -> "0801234567"
    clean_number = re.sub(r'[\s\-\(\)]', '', str(value))

    # 2. Regex Pattern for Nigerian Mobile Numbers
    # ^                 : Start of string
    # (?:\+?234|0)?     : Optional prefix (+234, 234, or 0)
    # ([789][01]\d{8})  : Captures the 10-digit mobile number (starts with 7, 8, or 9)
    # $                 : End of string
    pattern = r'^(?:\+?234|0)?([789][01]\d{8})$'
    
    match = re.match(pattern, clean_number)
    
    if not match:
        raise ValidationError(
            _('Enter a valid Nigerian mobile number (e.g., 08012345678 or +2348012345678).')
        )

    # 3. Normalize: Return strictly +234 format
    # match.group(1) is the last 10 digits (e.g., 8012345678)
    normalized_number = f"+234{match.group(1)}"
    
    return normalized_number


def validate_file_size(value):
    """
    Validates that an uploaded file is not larger than 5MB.
    Usage: validators=[validate_file_size] on FileField/ImageField
    """
    limit_mb = 5
    if value.size > limit_mb * 1024 * 1024:
        raise ValidationError(_(f'File too large. Size should not exceed {limit_mb} MB.'))


def validate_image_extension(value):
    """
    Validates that the uploaded file is an image (jpg, jpeg, png, webp).
    Usage: validators=[validate_image_extension] on ImageField
    """
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    if not ext.lower() in valid_extensions:
        raise ValidationError(_('Unsupported file extension. Allowed: jpg, jpeg, png, webp.'))