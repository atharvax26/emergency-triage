"""Password hashing and verification module using bcrypt."""

import re
from typing import Tuple

from passlib.context import CryptContext

from app.config import settings


# Password hashing context with bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_COST_FACTOR
)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with configured cost factor.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
        
    Note:
        Each call produces a different hash due to unique salt generation.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_complexity(password: str) -> Tuple[bool, str]:
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
        - (True, "") if password is valid
        - (False, error_message) if password is invalid
    """
    min_length = settings.PASSWORD_MIN_LENGTH
    
    # Check minimum length
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long"
    
    # Check for uppercase letter
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for lowercase letter
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for digit
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    
    # Check for special character
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\\/;'`~]", password):
        return False, "Password must contain at least one special character"
    
    return True, ""


def is_password_valid(password: str) -> bool:
    """
    Check if password meets complexity requirements.
    
    Args:
        password: Password to validate
        
    Returns:
        True if password is valid, False otherwise
    """
    is_valid, _ = validate_password_complexity(password)
    return is_valid
