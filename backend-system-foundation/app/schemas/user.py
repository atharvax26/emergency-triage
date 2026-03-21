"""User management request/response schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """User creation schema."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=12, description="User password (minimum 12 characters)")
    first_name: str = Field(..., min_length=1, max_length=100, description="User's first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="User's last name")


class UserUpdate(BaseModel):
    """User update schema."""
    
    email: Optional[EmailStr] = Field(None, description="User email address")
    password: Optional[str] = Field(None, min_length=12, description="User password (minimum 12 characters)")
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="User's first name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="User's last name")
    is_active: Optional[bool] = Field(None, description="Whether user account is active")


class UserResponse(BaseModel):
    """User response schema."""
    
    id: UUID = Field(..., description="User unique identifier")
    email: str = Field(..., description="User email address")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    is_active: bool = Field(..., description="Whether user account is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class UserWithRoles(UserResponse):
    """User response with roles."""
    
    roles: List[str] = Field(..., description="List of user roles")


class UserListResponse(BaseModel):
    """Paginated user list response."""
    
    users: List[UserWithRoles] = Field(..., description="List of users")
    total_count: int = Field(..., description="Total number of users matching criteria")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")


class RoleAssignment(BaseModel):
    """Role assignment schema."""
    
    role_name: str = Field(..., description="Role name to assign")
