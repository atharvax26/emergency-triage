"""Authentication request/response schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginCredentials(BaseModel):
    """Login credentials schema."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class TokenPair(BaseModel):
    """Token pair response schema."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")


class AuthResult(BaseModel):
    """Authentication result schema."""
    
    user_id: UUID = Field(..., description="User unique identifier")
    email: str = Field(..., description="User email address")
    roles: List[str] = Field(..., description="User roles")
    tokens: TokenPair = Field(..., description="Access and refresh tokens")


class TokenValidation(BaseModel):
    """Token validation result schema."""
    
    is_valid: bool = Field(..., description="Whether token is valid")
    user_id: Optional[UUID] = Field(None, description="User ID if token is valid")
    email: Optional[str] = Field(None, description="User email if token is valid")
    roles: Optional[List[str]] = Field(None, description="User roles if token is valid")
    error: Optional[str] = Field(None, description="Error message if token is invalid")


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    
    refresh_token: str = Field(..., description="JWT refresh token")


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""
    
    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=12, description="New password")
