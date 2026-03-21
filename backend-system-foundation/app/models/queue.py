"""QueueEntry and Assignment models for emergency triage queue management."""

from datetime import datetime
from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.patient import Patient
    from app.models.user import User


class QueueEntry(BaseModel):
    """
    QueueEntry model representing a patient's position in the emergency triage queue.
    
    Attributes:
        patient_id: Foreign key to the patient
        priority: Priority level (1-10, higher = more urgent) - foundation for ML scoring
        status: Current status of the queue entry
        symptoms: JSONB field containing symptom information
        vital_signs: JSONB field containing vital signs measurements
        arrival_time: Timestamp when patient arrived
        patient: The patient this queue entry belongs to
        assignments: List of assignments for this queue entry
    
    Validation Rules:
        - priority must be between 1 and 10
        - status must be one of: 'waiting', 'assigned', 'in_progress', 'completed', 'cancelled'
        - symptoms must contain 'chief_complaint' field
        - vital_signs are optional but validated for medical ranges if provided
        - arrival_time defaults to current timestamp
        - Only one active (non-completed/cancelled) queue entry per patient
    
    Requirements: 6.1, 6.2, 6.4, 6.5, 13.3
    """
    
    __tablename__ = "queue_entries"
    
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the patient"
    )
    
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        doc="Priority level (1-10, higher = more urgent) - foundation for ML scoring"
    )
    
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Current status: 'waiting', 'assigned', 'in_progress', 'completed', 'cancelled'"
    )
    
    symptoms: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="Symptom information (chief_complaint, symptom_list, duration) - must contain 'chief_complaint'"
    )
    
    vital_signs: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        doc="Vital signs (bp, hr, temp, spo2, resp_rate) - optional but validated if provided"
    )
    
    arrival_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="Timestamp when patient arrived"
    )
    
    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="queue_entries",
        doc="The patient this queue entry belongs to"
    )
    
    assignments: Mapped[List["Assignment"]] = relationship(
        "Assignment",
        back_populates="queue_entry",
        cascade="all, delete-orphan",
        doc="Assignments for this queue entry"
    )
    
    # Additional indexes for performance
    __table_args__ = (
        Index("ix_queue_entries_status_priority", "status", "priority"),
        Index("ix_queue_entries_arrival_time", "arrival_time"),
        Index("ix_queue_entries_patient_status", "patient_id", "status"),
    )
    
    def __repr__(self) -> str:
        """String representation of the queue entry."""
        return f"<QueueEntry(id={self.id}, patient_id={self.patient_id}, priority={self.priority}, status={self.status})>"


class Assignment(BaseModel):
    """
    Assignment model representing the association between a queue entry and a doctor.
    
    Attributes:
        queue_entry_id: Foreign key to the queue entry
        doctor_id: Foreign key to the user (must have 'doctor' role)
        assigned_at: Timestamp when the assignment was created
        completed_at: Timestamp when the assignment was completed (nullable)
        status: Current status of the assignment
        queue_entry: The queue entry this assignment belongs to
        doctor: The doctor (user) assigned to this queue entry
    
    Validation Rules:
        - doctor_id must reference a user with 'doctor' role
        - status must be one of: 'active', 'completed', 'cancelled'
        - completed_at must be after assigned_at if set
        - Only one active assignment per queue entry
    
    Requirements: 7.1, 7.2, 7.3, 7.5, 13.3
    """
    
    __tablename__ = "assignments"
    
    queue_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("queue_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the queue entry"
    )
    
    doctor_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the user (must have 'doctor' role)"
    )
    
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="Timestamp when the assignment was created"
    )
    
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when the assignment was completed (nullable)"
    )
    
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Current status: 'active', 'completed', 'cancelled'"
    )
    
    # Relationships
    queue_entry: Mapped["QueueEntry"] = relationship(
        "QueueEntry",
        back_populates="assignments",
        doc="The queue entry this assignment belongs to"
    )
    
    doctor: Mapped["User"] = relationship(
        "User",
        back_populates="assignments",
        doc="The doctor (user) assigned to this queue entry"
    )
    
    # Additional indexes for performance
    __table_args__ = (
        Index("ix_assignments_doctor_status", "doctor_id", "status"),
        Index("ix_assignments_queue_status", "queue_entry_id", "status"),
        Index("ix_assignments_assigned_at", "assigned_at"),
    )
    
    def __repr__(self) -> str:
        """String representation of the assignment."""
        return f"<Assignment(id={self.id}, queue_entry_id={self.queue_entry_id}, doctor_id={self.doctor_id}, status={self.status})>"
