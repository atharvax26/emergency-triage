"""Patient request/response schemas (DTOs)."""

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PatientCreateDTO(BaseModel):
    """Patient creation schema."""
    
    first_name: str = Field(..., min_length=1, max_length=100, description="Patient's first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Patient's last name")
    date_of_birth: date = Field(..., description="Patient's date of birth (must be in past)")
    gender: str = Field(..., description="Patient's gender (male, female, other, unknown)")
    contact_info: Dict[str, Any] = Field(..., description="Contact information (phone, email, address)")
    medical_history: Optional[Dict[str, Any]] = Field(None, description="Medical history (allergies, conditions, medications)")
    
    @field_validator('gender')
    @classmethod
    def validate_gender(cls, v: str) -> str:
        """Validate gender is one of allowed values."""
        allowed = {'male', 'female', 'other', 'unknown'}
        if v.lower() not in allowed:
            raise ValueError(f"Gender must be one of: {', '.join(allowed)}")
        return v.lower()
    
    @field_validator('date_of_birth')
    @classmethod
    def validate_dob(cls, v: date) -> date:
        """Validate date of birth is in the past."""
        if v >= date.today():
            raise ValueError("Date of birth must be in the past")
        return v
    
    @field_validator('contact_info')
    @classmethod
    def validate_contact_info(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate contact info contains at least one contact method."""
        valid_methods = {'phone', 'email', 'address'}
        has_contact = any(key in v and v[key] for key in valid_methods)
        if not has_contact:
            raise ValueError("Contact info must contain at least one contact method (phone, email, or address)")
        return v


class PatientUpdateDTO(BaseModel):
    """Patient update schema."""
    
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Patient's first name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Patient's last name")
    date_of_birth: Optional[date] = Field(None, description="Patient's date of birth (must be in past)")
    gender: Optional[str] = Field(None, description="Patient's gender (male, female, other, unknown)")
    contact_info: Optional[Dict[str, Any]] = Field(None, description="Contact information (phone, email, address)")
    medical_history: Optional[Dict[str, Any]] = Field(None, description="Medical history (allergies, conditions, medications)")
    
    @field_validator('gender')
    @classmethod
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        """Validate gender is one of allowed values."""
        if v is None:
            return v
        allowed = {'male', 'female', 'other', 'unknown'}
        if v.lower() not in allowed:
            raise ValueError(f"Gender must be one of: {', '.join(allowed)}")
        return v.lower()
    
    @field_validator('date_of_birth')
    @classmethod
    def validate_dob(cls, v: Optional[date]) -> Optional[date]:
        """Validate date of birth is in the past."""
        if v is not None and v >= date.today():
            raise ValueError("Date of birth must be in the past")
        return v
    
    @field_validator('contact_info')
    @classmethod
    def validate_contact_info(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate contact info contains at least one contact method."""
        if v is None:
            return v
        valid_methods = {'phone', 'email', 'address'}
        has_contact = any(key in v and v[key] for key in valid_methods)
        if not has_contact:
            raise ValueError("Contact info must contain at least one contact method (phone, email, or address)")
        return v


class PatientResponse(BaseModel):
    """Patient response schema."""
    
    id: UUID = Field(..., description="Patient unique identifier")
    mrn: str = Field(..., description="Medical Record Number")
    first_name: str = Field(..., description="Patient's first name")
    last_name: str = Field(..., description="Patient's last name")
    date_of_birth: date = Field(..., description="Patient's date of birth")
    gender: str = Field(..., description="Patient's gender")
    contact_info: Dict[str, Any] = Field(..., description="Contact information")
    medical_history: Optional[Dict[str, Any]] = Field(None, description="Medical history")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class SearchCriteria(BaseModel):
    """Patient search criteria schema."""
    
    mrn: Optional[str] = Field(None, description="Medical Record Number")
    first_name: Optional[str] = Field(None, description="First name (case-insensitive)")
    last_name: Optional[str] = Field(None, description="Last name (case-insensitive)")
    date_of_birth: Optional[date] = Field(None, description="Date of birth")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Page size (max 100)")


class PatientListResponse(BaseModel):
    """Paginated patient list response."""
    
    patients: List[PatientResponse] = Field(..., description="List of patients")
    total_count: int = Field(..., description="Total number of patients matching criteria")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")


class ValidationResult(BaseModel):
    """Validation result schema."""
    
    is_valid: bool = Field(..., description="Whether validation passed")
    errors: Optional[List[Dict[str, str]]] = Field(None, description="List of validation errors")
