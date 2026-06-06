"""AuditLog model for comprehensive system action logging."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base):
    """
    AuditLog model representing immutable audit trail records.
    
    This model tracks all system actions for compliance and security auditing.
    Audit logs are IMMUTABLE - they cannot be updated or deleted once created.
    This immutability is enforced at the service layer.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to users table (nullable for system events)
        action: Action performed (e.g., 'login', 'create_patient', 'update_queue')
        resource_type: Type of resource affected (e.g., 'user', 'patient', 'queue_entry')
        resource_id: ID of the affected resource (nullable)
        metadata: Additional context stored as JSONB (request_id, endpoint, method, status_code)
        ip_address: IP address of the request origin
        created_at: Timestamp when the audit log was created
        user: Relationship to the User who performed the action
    
    Validation Rules:
        - action is required and indexed for fast querying
        - resource_type must be one of: 'user', 'patient', 'queue_entry', 'assignment', 'session', 'system'
        - metadata should contain: request_id, endpoint, method, status_code
        - ip_address is required for user actions
        - Audit logs are immutable (no updates or deletes)
    
    Indexes:
        - user_id: For querying logs by user
        - action: For querying logs by action type
        - resource_type: For querying logs by resource
        - created_at: For time-based queries
        - Composite indexes for common query patterns
    
    Note: This model does NOT include updated_at since audit logs are immutable.
    """
    
    __tablename__ = "audit_logs"
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=lambda: __import__('uuid').uuid4(),
        index=True,
        doc="Unique identifier"
    )
    
    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Foreign key to the user who performed the action (nullable for system events)"
    )
    
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Action performed: 'login', 'create_patient', 'update_queue', etc."
    )
    
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Resource type: 'user', 'patient', 'queue_entry', 'assignment', 'session', 'system'"
    )
    
    resource_id: Mapped[Optional[UUID]] = mapped_column(
        nullable=True,
        doc="ID of the affected resource (nullable)"
    )
    
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        doc="Additional context: request_id, endpoint, method, status_code, changes, etc."
    )
    
    ip_address: Mapped[str] = mapped_column(
        String(45),  # IPv6 max length
        nullable=False,
        doc="IP address of the request origin"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="Timestamp when the audit log was created"
    )
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        doc="The user who performed the action (None for system events)"
    )
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
        Index("ix_audit_logs_resource_type_created", "resource_type", "created_at"),
        Index("ix_audit_logs_user_action", "user_id", "action"),
    )
    
    def __repr__(self) -> str:
        """String representation of the audit log."""
        return (
            f"<AuditLog(id={self.id}, user_id={self.user_id}, "
            f"action={self.action}, resource_type={self.resource_type})>"
        )
