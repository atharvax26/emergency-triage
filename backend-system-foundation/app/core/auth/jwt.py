"""JWT token generation and validation module using RS256 algorithm."""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from jose import JWTError, jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from app.config import settings


# RSA key pair for JWT signing (RS256)
# In production, these should be loaded from secure storage or environment variables
_private_key: Optional[str] = None
_public_key: Optional[str] = None


def _generate_rsa_keys() -> tuple[str, str]:
    """
    Generate RSA key pair for JWT signing.
    
    Returns:
        Tuple of (private_key_pem, public_key_pem)
        
    Note:
        In production, keys should be pre-generated and stored securely.
        This function is for development/testing purposes.
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Serialize private key to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Get public key and serialize to PEM format
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return private_pem, public_pem


def _get_keys() -> tuple[str, str]:
    """
    Get or generate RSA keys for JWT signing.
    
    Returns:
        Tuple of (private_key, public_key)
    """
    global _private_key, _public_key
    
    if _private_key is None or _public_key is None:
        # In production, load from environment or secure storage
        # For now, generate keys (they will persist for the application lifetime)
        _private_key, _public_key = _generate_rsa_keys()
    
    return _private_key, _public_key


def generate_access_token(
    user_id: str,
    email: str,
    roles: List[str]
) -> str:
    """
    Generate JWT access token with 15-minute expiry.
    
    Args:
        user_id: User's unique identifier
        email: User's email address
        roles: List of role names assigned to the user
        
    Returns:
        Encoded JWT access token
        
    Token Structure:
        {
            "sub": "user_id",
            "email": "user@example.com",
            "roles": ["doctor"],
            "exp": timestamp,
            "iat": timestamp,
            "type": "access"
        }
    """
    now = datetime.utcnow()
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    claims = {
        "sub": user_id,
        "email": email,
        "roles": roles,
        "exp": now + expires_delta,
        "iat": now,
        "type": "access"
    }
    
    private_key, _ = _get_keys()
    return jwt.encode(claims, private_key, algorithm=settings.JWT_ALGORITHM)


def generate_refresh_token(user_id: str) -> tuple[str, str]:
    """
    Generate JWT refresh token with 7-day expiry.
    
    Args:
        user_id: User's unique identifier
        
    Returns:
        Tuple of (encoded_token, token_id)
        - encoded_token: The JWT refresh token
        - token_id: Unique token identifier (jti) for revocation tracking
        
    Token Structure:
        {
            "sub": "user_id",
            "exp": timestamp,
            "iat": timestamp,
            "type": "refresh",
            "jti": "unique_token_id"
        }
    """
    now = datetime.utcnow()
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token_id = str(uuid.uuid4())
    
    claims = {
        "sub": user_id,
        "exp": now + expires_delta,
        "iat": now,
        "type": "refresh",
        "jti": token_id
    }
    
    private_key, _ = _get_keys()
    encoded_token = jwt.encode(claims, private_key, algorithm=settings.JWT_ALGORITHM)
    
    return encoded_token, token_id


def validate_token(token: str) -> Optional[Dict]:
    """
    Validate JWT token and extract claims.
    
    Args:
        token: JWT token to validate
        
    Returns:
        Dict of token claims if valid, None if invalid or expired
        
    Validation checks:
        - Token signature is valid
        - Token has not expired
        - Token algorithm matches expected (RS256)
    """
    try:
        _, public_key = _get_keys()
        
        # Decode and validate token
        claims = jwt.decode(
            token,
            public_key,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        return claims
        
    except JWTError:
        # Token is invalid, expired, or signature doesn't match
        return None


def extract_user_id(token: str) -> Optional[str]:
    """
    Extract user ID from JWT token.
    
    Args:
        token: JWT token
        
    Returns:
        User ID if token is valid, None otherwise
    """
    claims = validate_token(token)
    if claims:
        return claims.get("sub")
    return None


def extract_roles(token: str) -> List[str]:
    """
    Extract roles from JWT access token.
    
    Args:
        token: JWT access token
        
    Returns:
        List of role names, empty list if token is invalid or has no roles
    """
    claims = validate_token(token)
    if claims and claims.get("type") == "access":
        return claims.get("roles", [])
    return []


def is_token_expired(token: str) -> bool:
    """
    Check if token has expired.
    
    Args:
        token: JWT token
        
    Returns:
        True if token is expired or invalid, False if still valid
    """
    claims = validate_token(token)
    if not claims:
        return True
    
    exp = claims.get("exp")
    if not exp:
        return True
    
    # Check if current time is past expiration
    return datetime.utcnow().timestamp() >= exp


def get_token_type(token: str) -> Optional[str]:
    """
    Get token type (access or refresh).
    
    Args:
        token: JWT token
        
    Returns:
        Token type ("access" or "refresh") if valid, None otherwise
    """
    claims = validate_token(token)
    if claims:
        return claims.get("type")
    return None


def get_token_jti(token: str) -> Optional[str]:
    """
    Get token JTI (unique token identifier) for refresh tokens.
    
    Args:
        token: JWT refresh token
        
    Returns:
        Token JTI if valid refresh token, None otherwise
    """
    claims = validate_token(token)
    if claims and claims.get("type") == "refresh":
        return claims.get("jti")
    return None
