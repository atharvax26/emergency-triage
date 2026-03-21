"""User, Role, Permission, UserRole, and Session models."""

from datetime import datetime
from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.queue import Assignment


class User(BaseModel):
    """
    User model representing system users (nurses, doctors, admins).
    
    Attributes:
        email: Unique email address for authentication
        password_hash: Bcrypt hashed password
        first_name: User's first name
        last_name: User's last name
        is_active: Whether the user account is active
        roles: List of roles assigned to this user
        sessions: List of active sessions for this user
        assignments: List of patient assignments (for doctors)
    
    Validation Rules:
        - Email must be valid format and unique
        - Password must meet complexity requirements (min 12 chars, uppercase, lowercase, number, special char)
        - first_name and last_name are required, max 100 chars each
        - is_active defaults to True
    """
    
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique email address for authentication"
    )
    
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Bcrypt hashed password"
    )
    
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="User's first name"
    )
    
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="User's last name"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the user account is active"
    )
    
    # Relationships
    user_roles: Mapped[List["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="Association records linking user to roles"
    )
    
    sessions: Mapped[List["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="Active sessions for this user"
    )
    
    assignments: Mapped[List["Assignment"]] = relationship(
        "Assignment",
        back_populates="doctor",
        cascade="all, delete-orphan",
        doc="Patient assignments for this user (for doctors)"
    )
    
    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<User(id={self.id}, email={self.email}, active={self.is_active})>"


class Role(BaseModel):
    """
    Role model representing user roles (nurse, doctor, admin).
    
    Attributes:
        name: Unique role name ('nurse', 'doctor', 'admin')
        description: Description of the role's purpose
        user_roles: List of user-role associations
        permissions: List of permissions granted to this role
    
    Validation Rules:
        - name must be one of: 'nurse', 'doctor', 'admin'
        - name is unique and indexed
        - description is required
    """
    
    __tablename__ = "roles"
    
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique role name: 'nurse', 'doctor', 'admin'"
    )
    
    description: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Description of the role's purpose"
    )
    
    # Relationships
    user_roles: Mapped[List["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
        doc="Association records linking role to users"
    )
    
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        back_populates="role",
        cascade="all, delete-orphan",
        doc="Permissions granted to this role"
    )
    
    def __repr__(self) -> str:
        """String representation of the role."""
        return f"<Role(id={self.id}, name={self.name})>"


class Permission(BaseModel):
    """
    Permission model representing role-based access control permissions.
    
    Attributes:
        role_id: Foreign key to the role this permission belongs to
        resource: Resource type (e.g., 'patient', 'queue', 'user')
        action: Action allowed (e.g., 'create', 'read', 'update', 'delete')
        role: The role this permission belongs to
    
    Validation Rules:
        - resource must be one of: 'patient', 'queue', 'user', 'audit', 'system'
        - action must be one of: 'create', 'read', 'update', 'delete', 'assign'
        - Composite unique constraint on (role_id, resource, action)
    """
    
    __tablename__ = "permissions"
    
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the role this permission belongs to"
    )
    
    resource: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Resource type: 'patient', 'queue', 'user', 'audit', 'system'"
    )
    
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Action allowed: 'create', 'read', 'update', 'delete', 'assign'"
    )
    
    # Relationships
    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="permissions",
        doc="The role this permission belongs to"
    )
    
    # Composite unique constraint on (role_id, resource, action)
    __table_args__ = (
        UniqueConstraint("role_id", "resource", "action", name="uq_role_resource_action"),
        Index("ix_permissions_role_resource", "role_id", "resource"),
    )
    
    def __repr__(self) -> str:
        """String representation of the permission."""
        return f"<Permission(id={self.id}, resource={self.resource}, action={self.action})>"


class UserRole(BaseModel):
    """
    UserRole association model linking users to roles.
    
    Attributes:
        user_id: Foreign key to the user
        role_id: Foreign key to the role
        assigned_at: Timestamp when the role was assigned
        user: The user this association belongs to
        role: The role this association belongs to
    """
    
    __tablename__ = "user_roles"
    
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the user"
    )
    
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the role"
    )
    
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="Timestamp when the role was assigned"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="user_roles",
        doc="The user this association belongs to"
    )
    
    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="user_roles",
        doc="The role this association belongs to"
    )
    
    # Composite unique constraint on (user_id, role_id)
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        Index("ix_user_roles_user_role", "user_id", "role_id"),
    )
    
    def __repr__(self) -> str:
        """String representation of the user-role association."""
        return f"<UserRole(id={self.id}, user_id={self.user_id}, role_id={self.role_id})>"


class Session(BaseModel):
    """
    Session model representing user authentication sessions.
    
    Attributes:
        user_id: Foreign key to the user this session belongs to
        token_hash: Hashed JWT token for revocation checking
        expires_at: Timestamp when the session expires
        user: The user this session belongs to
    
    Validation Rules:
        - token_hash is unique and indexed
        - expires_at must be in the future at creation
        - Sessions are automatically cleaned up after expiration
    """
    
    __tablename__ = "sessions"
    
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the user this session belongs to"
    )
    
    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Hashed JWT token for revocation checking"
    )
    
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Timestamp when the session expires"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions",
        doc="The user this session belongs to"
    )
    
    # Additional indexes for performance
    __table_args__ = (
        Index("ix_sessions_expires_at", "expires_at"),
        Index("ix_sessions_user_expires", "user_id", "expires_at"),
    )
    
    def __repr__(self) -> str:
        """String representation of the session."""
        return f"<Session(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.utcnow() >= self.expires_at
