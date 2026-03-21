"""Patient model for emergency triage system."""

from datetime import date
from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlalchemy import Date, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.queue import QueueEntry


class Patient(BaseModel):
    """
    Patient model representing individuals receiving emergency care.
    
    Attributes:
        mrn: Medical Record Number, unique identifier in format MRN-YYYYMMDD-XXXX
        first_name: Patient's first name
        last_name: Patient's last name
        date_of_birth: Patient's date of birth
        gender: Patient's gender ('male', 'female', 'other', 'unknown')
        contact_info: JSONB field containing contact information (phone, email, address)
        medical_history: JSONB field containing medical history (allergies, conditions, medications)
        queue_entries: List of queue entries for this patient
    
    Validation Rules:
        - mrn must be unique and follow format: MRN-YYYYMMDD-XXXX
        - first_name and last_name are required, max 100 chars each
        - date_of_birth must be in the past
        - gender must be one of: 'male', 'female', 'other', 'unknown'
        - contact_info must contain at least one contact method
        - medical_history is optional but validated for structure if provided
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.7, 13.2, 13.3
    """
    
    __tablename__ = "patients"
    
    mrn: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        doc="Medical Record Number in format MRN-YYYYMMDD-XXXX"
    )
    
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Patient's first name"
    )
    
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Patient's last name"
    )
    
    date_of_birth: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="Patient's date of birth (must be in the past)"
    )
    
    gender: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Patient's gender: 'male', 'female', 'other', 'unknown'"
    )
    
    contact_info: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="Contact information (phone, email, address) - must contain at least one contact method"
    )
    
    medical_history: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        doc="Medical history (allergies, conditions, medications) - optional but validated if provided"
    )
    
    # Relationships
    queue_entries: Mapped[List["QueueEntry"]] = relationship(
        "QueueEntry",
        back_populates="patient",
        cascade="all, delete-orphan",
        doc="Queue entries for this patient"
    )
    
    # Additional indexes for search performance
    __table_args__ = (
        Index("ix_patients_first_name", "first_name"),
        Index("ix_patients_last_name", "last_name"),
        Index("ix_patients_date_of_birth", "date_of_birth"),
        Index("ix_patients_name_dob", "first_name", "last_name", "date_of_birth"),
    )
    
    def __repr__(self) -> str:
        """String representation of the patient."""
        return f"<Patient(id={self.id}, mrn={self.mrn}, name={self.first_name} {self.last_name})>"
    
    @property
    def full_name(self) -> str:
        """Get patient's full name."""
        return f"{self.first_name} {self.last_name}"
