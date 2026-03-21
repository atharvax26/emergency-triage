"""Authentication module exports."""

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
from app.core.auth.password import (
    hash_password,
    verify_password,
    validate_password_complexity,
    is_password_valid,
)
from app.core.auth.service import AuthService

__all__ = [
    # JWT functions
    "generate_access_token",
    "generate_refresh_token",
    "validate_token",
    "extract_user_id",
    "extract_roles",
    "is_token_expired",
    "get_token_type",
    "get_token_jti",
    # Password functions
    "hash_password",
    "verify_password",
    "validate_password_complexity",
    "is_password_valid",
    # Service
    "AuthService",
]
