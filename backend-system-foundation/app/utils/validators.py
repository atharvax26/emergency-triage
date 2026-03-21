"""Common validation utilities."""

import re
from datetime import date, datetime
from typing import Optional
from uuid import UUID


def validate_email(email: str) -> bool:
    """
    Validate email format (RFC 5322 simplified).
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_uuid(value: str) -> bool:
    """
    Validate UUID format (RFC 4122).
    
    Args:
        value: UUID string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def validate_password_complexity(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password meets complexity requirements.
    
    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, None


def validate_mrn_format(mrn: str) -> bool:
    """
    Validate MRN format: MRN-YYYYMMDD-XXXX.
    
    Args:
        mrn: Medical Record Number to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^MRN-\d{8}-\d{4}$'
    if not re.match(pattern, mrn):
        return False
    
    # Validate date portion
    try:
        date_str = mrn.split('-')[1]
        datetime.strptime(date_str, '%Y%m%d')
        return True
    except (ValueError, IndexError):
        return False


def validate_date_in_past(date_value: date) -> bool:
    """
    Validate that date is in the past.
    
    Args:
        date_value: Date to validate
        
    Returns:
        True if in past, False otherwise
    """
    return date_value < date.today()


def validate_gender(gender: str) -> bool:
    """
    Validate gender value.
    
    Args:
        gender: Gender value to validate
        
    Returns:
        True if valid, False otherwise
    """
    valid_genders = ['male', 'female', 'other', 'unknown']
    return gender.lower() in valid_genders


def validate_priority(priority: int) -> bool:
    """
    Validate queue priority is between 1 and 10.
    
    Args:
        priority: Priority value to validate
        
    Returns:
        True if valid, False otherwise
    """
    return 1 <= priority <= 10


def validate_queue_status(status: str) -> bool:
    """
    Validate queue entry status.
    
    Args:
        status: Status value to validate
        
    Returns:
        True if valid, False otherwise
    """
    valid_statuses = ['waiting', 'assigned', 'in_progress', 'completed', 'cancelled']
    return status.lower() in valid_statuses


def validate_assignment_status(status: str) -> bool:
    """
    Validate assignment status.
    
    Args:
        status: Status value to validate
        
    Returns:
        True if valid, False otherwise
    """
    valid_statuses = ['active', 'completed', 'cancelled']
    return status.lower() in valid_statuses


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize string input by trimming whitespace and limiting length.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    sanitized = value.strip()
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized


def mask_email(email: str) -> str:
    """
    Mask email address for logging (show first 2 chars and domain).
    
    Args:
        email: Email address to mask
        
    Returns:
        Masked email
    """
    if '@' not in email:
        return email[:2] + '***'
    
    local, domain = email.split('@')
    if len(local) <= 2:
        return local[0] + '***@' + domain
    return local[:2] + '***@' + domain


def mask_mrn(mrn: str) -> str:
    """
    Mask MRN for logging (show only prefix and last 2 digits).
    
    Args:
        mrn: MRN to mask
        
    Returns:
        Masked MRN
    """
    if len(mrn) <= 4:
        return mrn[:2] + '***'
    return mrn[:4] + '***' + mrn[-2:]
