"""Unit tests for authentication modules (password and JWT)."""

import pytest
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime, timedelta

from app.core.auth.password import (
    hash_password,
    verify_password,
    validate_password_complexity,
    is_password_valid,
)
from app.core.auth.jwt import (
    generate_access_token,
    generate_refresh_token,
    validate_token,
    extract_user_id,
    extract_roles,
    is_token_expired,
    get_token_type,
    get_token_jti,
)


class TestPasswordModule:
    """Test password hashing and verification."""
    
    def test_hash_password_produces_different_hashes(self):
        """Test that hashing the same password twice produces different hashes."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2, "Hashes should be different due to different salts"
    
    def test_verify_password_with_correct_password(self):
        """Test password verification with correct password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_with_incorrect_password(self):
        """Test password verification with incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_validate_password_complexity_valid(self):
        """Test password complexity validation with valid password."""
        valid_password = "ValidPass123!"
        is_valid, error = validate_password_complexity(valid_password)
        
        assert is_valid is True
        assert error == ""
    
    def test_validate_password_complexity_too_short(self):
        """Test password complexity validation with too short password."""
        short_password = "Short1!"
        is_valid, error = validate_password_complexity(short_password)
        
        assert is_valid is False
        assert "at least 12 characters" in error
    
    def test_validate_password_complexity_no_uppercase(self):
        """Test password complexity validation without uppercase letter."""
        no_upper = "validpass123!"
        is_valid, error = validate_password_complexity(no_upper)
        
        assert is_valid is False
        assert "uppercase letter" in error
    
    def test_validate_password_complexity_no_lowercase(self):
        """Test password complexity validation without lowercase letter."""
        no_lower = "VALIDPASS123!"
        is_valid, error = validate_password_complexity(no_lower)
        
        assert is_valid is False
        assert "lowercase letter" in error
    
    def test_validate_password_complexity_no_number(self):
        """Test password complexity validation without number."""
        no_number = "ValidPassword!"
        is_valid, error = validate_password_complexity(no_number)
        
        assert is_valid is False
        assert "number" in error
    
    def test_validate_password_complexity_no_special_char(self):
        """Test password complexity validation without special character."""
        no_special = "ValidPassword123"
        is_valid, error = validate_password_complexity(no_special)
        
        assert is_valid is False
        assert "special character" in error
    
    def test_is_password_valid(self):
        """Test is_password_valid convenience function."""
        assert is_password_valid("ValidPass123!") is True
        assert is_password_valid("short") is False


class TestJWTModule:
    """Test JWT token generation and validation."""
    
    def test_generate_access_token(self):
        """Test access token generation."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        roles = ["doctor"]
        
        token = generate_access_token(user_id, email, roles)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_generate_refresh_token(self):
        """Test refresh token generation."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        
        token, token_id = generate_refresh_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        assert token_id is not None
        assert isinstance(token_id, str)
    
    def test_validate_token_valid(self):
        """Test token validation with valid token."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        roles = ["doctor"]
        
        token = generate_access_token(user_id, email, roles)
        claims = validate_token(token)
        
        assert claims is not None
        assert claims["sub"] == user_id
        assert claims["email"] == email
        assert claims["roles"] == roles
        assert claims["type"] == "access"
    
    def test_validate_token_invalid(self):
        """Test token validation with invalid token."""
        invalid_token = "invalid.token.here"
        claims = validate_token(invalid_token)
        
        assert claims is None
    
    def test_extract_user_id(self):
        """Test extracting user ID from token."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        roles = ["doctor"]
        
        token = generate_access_token(user_id, email, roles)
        extracted_id = extract_user_id(token)
        
        assert extracted_id == user_id
    
    def test_extract_roles(self):
        """Test extracting roles from token."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        roles = ["doctor", "admin"]
        
        token = generate_access_token(user_id, email, roles)
        extracted_roles = extract_roles(token)
        
        assert extracted_roles == roles
    
    def test_is_token_expired_not_expired(self):
        """Test token expiration check with non-expired token."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        roles = ["doctor"]
        
        token = generate_access_token(user_id, email, roles)
        
        assert is_token_expired(token) is False
    
    def test_get_token_type_access(self):
        """Test getting token type for access token."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        roles = ["doctor"]
        
        token = generate_access_token(user_id, email, roles)
        token_type = get_token_type(token)
        
        assert token_type == "access"
    
    def test_get_token_type_refresh(self):
        """Test getting token type for refresh token."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        
        token, _ = generate_refresh_token(user_id)
        token_type = get_token_type(token)
        
        assert token_type == "refresh"
    
    def test_get_token_jti(self):
        """Test getting JTI from refresh token."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        
        token, expected_jti = generate_refresh_token(user_id)
        jti = get_token_jti(token)
        
        assert jti == expected_jti
