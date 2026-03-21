"""Seed roles and permissions

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:00:01.000000

Seeds the database with initial roles and permissions based on the RBAC matrix:

Roles:
- nurse: Nurse role for patient intake and basic queue viewing
- doctor: Doctor role for full queue access, patient assignment, and triage decisions
- admin: Administrator role for user management, system configuration, and audit access

Permissions (based on RBAC matrix from design.md):

Nurse permissions:
- patient: create, read, update
- queue: create, read

Doctor permissions:
- patient: create, read, update
- queue: create, read, update, assign, delete

Admin permissions:
- patient: create, read, update, delete
- queue: create, read, update, assign, delete
- user: create, read, update, delete
- audit: read

Requirements: 2.1, 13.1, 13.2
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed roles and permissions."""
    
    # Define table structures for bulk insert
    roles_table = table(
        'roles',
        column('id', postgresql.UUID),
        column('name', sa.String),
        column('description', sa.String),
    )
    
    permissions_table = table(
        'permissions',
        column('id', postgresql.UUID),
        column('role_id', postgresql.UUID),
        column('resource', sa.String),
        column('action', sa.String),
    )
    
    # Generate UUIDs for roles
    nurse_id = uuid.uuid4()
    doctor_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    
    # Insert roles
    op.bulk_insert(
        roles_table,
        [
            {
                'id': nurse_id,
                'name': 'nurse',
                'description': 'Nurse role for patient intake and basic queue viewing',
            },
            {
                'id': doctor_id,
                'name': 'doctor',
                'description': 'Doctor role for full queue access, patient assignment, and triage decisions',
            },
            {
                'id': admin_id,
                'name': 'admin',
                'description': 'Administrator role for user management, system configuration, and audit access',
            },
        ]
    )
    
    # Insert permissions
    permissions = []
    
    # Nurse permissions
    nurse_permissions = [
        ('patient', 'create'),
        ('patient', 'read'),
        ('patient', 'update'),
        ('queue', 'create'),
        ('queue', 'read'),
    ]
    for resource, action in nurse_permissions:
        permissions.append({
            'id': uuid.uuid4(),
            'role_id': nurse_id,
            'resource': resource,
            'action': action,
        })
    
    # Doctor permissions
    doctor_permissions = [
        ('patient', 'create'),
        ('patient', 'read'),
        ('patient', 'update'),
        ('queue', 'create'),
        ('queue', 'read'),
        ('queue', 'update'),
        ('queue', 'assign'),
        ('queue', 'delete'),
    ]
    for resource, action in doctor_permissions:
        permissions.append({
            'id': uuid.uuid4(),
            'role_id': doctor_id,
            'resource': resource,
            'action': action,
        })
    
    # Admin permissions
    admin_permissions = [
        ('patient', 'create'),
        ('patient', 'read'),
        ('patient', 'update'),
        ('patient', 'delete'),
        ('queue', 'create'),
        ('queue', 'read'),
        ('queue', 'update'),
        ('queue', 'assign'),
        ('queue', 'delete'),
        ('user', 'create'),
        ('user', 'read'),
        ('user', 'update'),
        ('user', 'delete'),
        ('audit', 'read'),
    ]
    for resource, action in admin_permissions:
        permissions.append({
            'id': uuid.uuid4(),
            'role_id': admin_id,
            'resource': resource,
            'action': action,
        })
    
    # Bulk insert all permissions
    op.bulk_insert(permissions_table, permissions)


def downgrade() -> None:
    """Remove seeded roles and permissions."""
    # Delete permissions first (due to foreign key constraint)
    op.execute(
        """
        DELETE FROM permissions 
        WHERE role_id IN (
            SELECT id FROM roles WHERE name IN ('nurse', 'doctor', 'admin')
        )
        """
    )
    
    # Delete roles
    op.execute("DELETE FROM roles WHERE name IN ('nurse', 'doctor', 'admin')")
