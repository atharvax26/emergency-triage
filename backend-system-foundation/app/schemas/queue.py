"""Queue request/response schemas (DTOs)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class QueueEntryCreate(BaseModel):
    """Queue entry creation schema."""
    
    patient_id: UUID = Field(..., description="Patient unique identifier")
    priority: int = Field(..., ge=1, le=10, description="Priority level (1-10, higher = more urgent)")
    symptoms: Dict[str, Any] = Field(..., description="Symptom information (must contain 'chief_complaint')")
    vital_signs: Optional[Dict[str, Any]] = Field(None, description="Vital signs (bp, hr, temp, spo2, resp_rate)")
    
    @field_validator('symptoms')
    @classmethod
    def validate_symptoms(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate symptoms contains chief_complaint."""
        if "chief_complaint" not in v:
            raise ValueError("Symptoms must contain 'chief_complaint' field")
        if not v["chief_complaint"]:
            raise ValueError("Chief complaint cannot be empty")
        return v


class QueueEntryUpdate(BaseModel):
    """Queue entry update schema."""
    
    priority: Optional[int] = Field(None, ge=1, le=10, description="Priority level (1-10)")
    status: Optional[str] = Field(None, description="Status (waiting, assigned, in_progress, completed, cancelled)")
    symptoms: Optional[Dict[str, Any]] = Field(None, description="Symptom information")
    vital_signs: Optional[Dict[str, Any]] = Field(None, description="Vital signs")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status is one of allowed values."""
        if v is None:
            return v
        allowed = {'waiting', 'assigned', 'in_progress', 'completed', 'cancelled'}
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(sorted(allowed))}")
        return v
    
    @field_validator('symptoms')
    @classmethod
    def validate_symptoms(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate symptoms contains chief_complaint if provided."""
        if v is None:
            return v
        if "chief_complaint" not in v:
            raise ValueError("Symptoms must contain 'chief_complaint' field")
        if not v["chief_complaint"]:
            raise ValueError("Chief complaint cannot be empty")
        return v


class QueueEntryResponse(BaseModel):
    """Queue entry response schema."""
    
    id: UUID = Field(..., description="Queue entry unique identifier")
    patient_id: UUID = Field(..., description="Patient unique identifier")
    priority: int = Field(..., description="Priority level (1-10)")
    status: str = Field(..., description="Current status")
    symptoms: Dict[str, Any] = Field(..., description="Symptom information")
    vital_signs: Optional[Dict[str, Any]] = Field(None, description="Vital signs")
    arrival_time: datetime = Field(..., description="Arrival timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class QueueFilters(BaseModel):
    """Queue filtering and pagination schema."""
    
    status: Optional[str] = Field(None, description="Filter by status")
    min_priority: Optional[int] = Field(None, ge=1, le=10, description="Minimum priority")
    max_priority: Optional[int] = Field(None, ge=1, le=10, description="Maximum priority")
    from_date: Optional[datetime] = Field(None, description="Filter from date")
    to_date: Optional[datetime] = Field(None, description="Filter to date")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Page size (max 100)")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status is one of allowed values."""
        if v is None:
            return v
        allowed = {'waiting', 'assigned', 'in_progress', 'completed', 'cancelled'}
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(sorted(allowed))}")
        return v


class QueueStats(BaseModel):
    """Queue statistics schema."""
    
    total_entries: int = Field(..., description="Total number of queue entries")
    waiting: int = Field(..., description="Number of waiting entries")
    assigned: int = Field(..., description="Number of assigned entries")
    in_progress: int = Field(..., description="Number of in-progress entries")
    completed: int = Field(..., description="Number of completed entries")
    cancelled: int = Field(..., description="Number of cancelled entries")
    avg_priority: float = Field(..., description="Average priority")
    critical_count: int = Field(..., description="Number of critical priority entries (9-10)")
    high_count: int = Field(..., description="Number of high priority entries (7-8)")
    medium_count: int = Field(..., description="Number of medium priority entries (4-6)")
    low_count: int = Field(..., description="Number of low priority entries (1-3)")


class AssignmentCreate(BaseModel):
    """Assignment creation schema."""
    
    queue_entry_id: UUID = Field(..., description="Queue entry unique identifier")
    doctor_id: UUID = Field(..., description="Doctor (user) unique identifier")


class AssignmentResponse(BaseModel):
    """Assignment response schema."""
    
    id: UUID = Field(..., description="Assignment unique identifier")
    queue_entry_id: UUID = Field(..., description="Queue entry unique identifier")
    doctor_id: UUID = Field(..., description="Doctor unique identifier")
    assigned_at: datetime = Field(..., description="Assignment timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    status: str = Field(..., description="Assignment status (active, completed, cancelled)")
    
    class Config:
        from_attributes = True


class QueueListResponse(BaseModel):
    """Paginated queue list response."""
    
    entries: List[QueueEntryResponse] = Field(..., description="List of queue entries")
    total_count: int = Field(..., description="Total number of entries matching criteria")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")
