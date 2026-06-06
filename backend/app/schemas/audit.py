"""Pydantic schemas for audit logging."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AuditQuery(BaseModel):
    """Schema for querying audit logs."""
    
    user_id: Optional[UUID] = Field(None, description="Filter by user ID")
    action: Optional[str] = Field(None, description="Filter by action")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_id: Optional[UUID] = Field(None, description="Filter by resource ID")
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(100, ge=1, le=1000, description="Items per page")
    
    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Ensure end_date is after start_date if both are provided."""
        if v and 'start_date' in info.data and info.data['start_date']:
            if v < info.data['start_date']:
                raise ValueError("end_date must be after start_date")
        return v


class AuditRecordResponse(BaseModel):
    """Schema for audit log record response."""
    
    id: UUID = Field(..., description="Audit log ID")
    user_id: Optional[UUID] = Field(None, description="User who performed the action")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[UUID] = Field(None, description="ID of affected resource")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    ip_address: str = Field(..., description="IP address of request origin")
    created_at: datetime = Field(..., description="When the action occurred")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "action": "patient.create",
                "resource_type": "patient",
                "resource_id": "123e4567-e89b-12d3-a456-426614174002",
                "metadata": {
                    "request_id": "123e4567-e89b-12d3-a456-426614174003",
                    "endpoint": "/api/v1/patients",
                    "method": "POST",
                    "status_code": 201
                },
                "ip_address": "192.168.1.1",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    }


class AuditExportRequest(BaseModel):
    """Schema for audit log export request."""
    
    start_date: datetime = Field(..., description="Start date for export")
    end_date: datetime = Field(..., description="End date for export")
    format: str = Field("json", description="Export format: 'json' or 'csv'")
    user_id: Optional[UUID] = Field(None, description="Filter by user ID")
    action: Optional[str] = Field(None, description="Filter by action")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Ensure format is either 'json' or 'csv'."""
        if v.lower() not in ['json', 'csv']:
            raise ValueError("format must be 'json' or 'csv'")
        return v.lower()
    
    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: datetime, info) -> datetime:
        """Ensure end_date is after start_date."""
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError("end_date must be after start_date")
        return v


class AuditLogListResponse(BaseModel):
    """Schema for paginated audit log list response."""
    
    items: List[AuditRecordResponse] = Field(..., description="List of audit records")
    total_count: int = Field(..., description="Total number of records")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [],
                "total_count": 150,
                "page": 1,
                "page_size": 100,
                "total_pages": 2
            }
        }
    }
