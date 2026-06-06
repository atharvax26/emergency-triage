"""Initial schema migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

Creates all tables for the Backend System Foundation:
- users: System users (nurses, doctors, admins)
- roles: User roles (nurse, doctor, admin)
- permissions: Role-based permissions
- user_roles: User-role associations
- sessions: Authentication sessions
- patients: Patient records
- queue_entries: Emergency triage queue
- assignments: Patient-doctor assignments
- audit_logs: Audit trail records

Requirements: 2.1, 13.1, 13.2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables with proper constraints and indexes."""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_roles_id', 'roles', ['id'])
    op.create_index('ix_roles_name', 'roles', ['name'])
    
    # Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource', sa.String(50), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('role_id', 'resource', 'action', name='uq_role_resource_action'),
    )
    op.create_index('ix_permissions_id', 'permissions', ['id'])
    op.create_index('ix_permissions_role_id', 'permissions', ['role_id'])
    op.create_index('ix_permissions_role_resource', 'permissions', ['role_id', 'resource'])
    
    # Create user_roles table
    op.create_table(
        'user_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )
    op.create_index('ix_user_roles_id', 'user_roles', ['id'])
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'])
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'])
    op.create_index('ix_user_roles_user_role', 'user_roles', ['user_id', 'role_id'])
    
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_sessions_id', 'sessions', ['id'])
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('ix_sessions_token_hash', 'sessions', ['token_hash'])
    op.create_index('ix_sessions_expires_at', 'sessions', ['expires_at'])
    op.create_index('ix_sessions_user_expires', 'sessions', ['user_id', 'expires_at'])
    
    # Create patients table
    op.create_table(
        'patients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('mrn', sa.String(20), nullable=False, unique=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=False),
        sa.Column('gender', sa.String(20), nullable=False),
        sa.Column('contact_info', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('medical_history', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_patients_id', 'patients', ['id'])
    op.create_index('ix_patients_mrn', 'patients', ['mrn'])
    op.create_index('ix_patients_first_name', 'patients', ['first_name'])
    op.create_index('ix_patients_last_name', 'patients', ['last_name'])
    op.create_index('ix_patients_date_of_birth', 'patients', ['date_of_birth'])
    op.create_index('ix_patients_name_dob', 'patients', ['first_name', 'last_name', 'date_of_birth'])
    
    # Create queue_entries table
    op.create_table(
        'queue_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('symptoms', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('vital_signs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('arrival_time', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_queue_entries_id', 'queue_entries', ['id'])
    op.create_index('ix_queue_entries_patient_id', 'queue_entries', ['patient_id'])
    op.create_index('ix_queue_entries_priority', 'queue_entries', ['priority'])
    op.create_index('ix_queue_entries_status', 'queue_entries', ['status'])
    op.create_index('ix_queue_entries_status_priority', 'queue_entries', ['status', 'priority'])
    op.create_index('ix_queue_entries_arrival_time', 'queue_entries', ['arrival_time'])
    op.create_index('ix_queue_entries_patient_status', 'queue_entries', ['patient_id', 'status'])
    
    # Create assignments table
    op.create_table(
        'assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('queue_entry_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['queue_entry_id'], ['queue_entries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_assignments_id', 'assignments', ['id'])
    op.create_index('ix_assignments_queue_entry_id', 'assignments', ['queue_entry_id'])
    op.create_index('ix_assignments_doctor_id', 'assignments', ['doctor_id'])
    op.create_index('ix_assignments_status', 'assignments', ['status'])
    op.create_index('ix_assignments_doctor_status', 'assignments', ['doctor_id', 'status'])
    op.create_index('ix_assignments_queue_status', 'assignments', ['queue_entry_id', 'status'])
    op.create_index('ix_assignments_assigned_at', 'assignments', ['assigned_at'])
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_user_created', 'audit_logs', ['user_id', 'created_at'])
    op.create_index('ix_audit_logs_action_created', 'audit_logs', ['action', 'created_at'])
    op.create_index('ix_audit_logs_resource_type_created', 'audit_logs', ['resource_type', 'created_at'])
    op.create_index('ix_audit_logs_user_action', 'audit_logs', ['user_id', 'action'])


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_table('audit_logs')
    op.drop_table('assignments')
    op.drop_table('queue_entries')
    op.drop_table('patients')
    op.drop_table('sessions')
    op.drop_table('user_roles')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('users')
