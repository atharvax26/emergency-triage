"""Seed script for permissions (RBAC matrix)."""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user import Role, Permission


def seed_permissions(db: Session, roles: dict[str, Role]) -> None:
    """
    Seed permissions into the database based on RBAC matrix (idempotent).
    
    Implements the complete RBAC matrix from the design document:
    
    | Resource | Action | Nurse | Doctor | Admin |
    |----------|--------|-------|--------|-------|
    | Patient  | Create | ✓     | ✓      | ✓     |
    | Patient  | Read   | ✓     | ✓      | ✓     |
    | Patient  | Update | ✓     | ✓      | ✓     |
    | Patient  | Delete | ✗     | ✗      | ✓     |
    | Queue    | Create | ✓     | ✓      | ✓     |
    | Queue    | Read   | ✓     | ✓      | ✓     |
    | Queue    | Update | ✗     | ✓      | ✓     |
    | Queue    | Assign | ✗     | ✓      | ✓     |
    | Queue    | Delete | ✗     | ✓      | ✓     |
    | User     | Create | ✗     | ✗      | ✓     |
    | User     | Read   | ✗     | ✗      | ✓     |
    | User     | Update | ✗     | ✗      | ✓     |
    | User     | Delete | ✗     | ✗      | ✓     |
    | Audit    | Read   | ✗     | ✗      | ✓     |
    | Audit    | Export | ✗     | ✗      | ✓     |
    
    Args:
        db: Database session
        roles: Dictionary mapping role names to Role objects
        
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
    """
    # Define permissions for each role based on RBAC matrix
    permissions_data = [
        # Nurse permissions
        {"role": "nurse", "resource": "patient", "action": "create"},
        {"role": "nurse", "resource": "patient", "action": "read"},
        {"role": "nurse", "resource": "patient", "action": "update"},
        {"role": "nurse", "resource": "queue", "action": "create"},
        {"role": "nurse", "resource": "queue", "action": "read"},
        
        # Doctor permissions (includes all nurse permissions plus more)
        {"role": "doctor", "resource": "patient", "action": "create"},
        {"role": "doctor", "resource": "patient", "action": "read"},
        {"role": "doctor", "resource": "patient", "action": "update"},
        {"role": "doctor", "resource": "queue", "action": "create"},
        {"role": "doctor", "resource": "queue", "action": "read"},
        {"role": "doctor", "resource": "queue", "action": "update"},
        {"role": "doctor", "resource": "queue", "action": "assign"},
        {"role": "doctor", "resource": "queue", "action": "delete"},
        
        # Admin permissions (full access to all resources)
        {"role": "admin", "resource": "patient", "action": "create"},
        {"role": "admin", "resource": "patient", "action": "read"},
        {"role": "admin", "resource": "patient", "action": "update"},
        {"role": "admin", "resource": "patient", "action": "delete"},
        {"role": "admin", "resource": "queue", "action": "create"},
        {"role": "admin", "resource": "queue", "action": "read"},
        {"role": "admin", "resource": "queue", "action": "update"},
        {"role": "admin", "resource": "queue", "action": "assign"},
        {"role": "admin", "resource": "queue", "action": "delete"},
        {"role": "admin", "resource": "user", "action": "create"},
        {"role": "admin", "resource": "user", "action": "read"},
        {"role": "admin", "resource": "user", "action": "update"},
        {"role": "admin", "resource": "user", "action": "delete"},
        {"role": "admin", "resource": "audit", "action": "read"},
        {"role": "admin", "resource": "audit", "action": "export"},
    ]
    
    created_count = 0
    existing_count = 0
    
    for perm_data in permissions_data:
        role_name = perm_data["role"]
        role = roles.get(role_name)
        
        if not role:
            print(f"⚠ Warning: Role '{role_name}' not found, skipping permission")
            continue
        
        # Check if permission already exists
        existing_perm = db.query(Permission).filter(
            Permission.role_id == role.id,
            Permission.resource == perm_data["resource"],
            Permission.action == perm_data["action"]
        ).first()
        
        if existing_perm:
            existing_count += 1
        else:
            # Create new permission
            permission = Permission(
                role_id=role.id,
                resource=perm_data["resource"],
                action=perm_data["action"]
            )
            db.add(permission)
            try:
                db.commit()
                created_count += 1
            except IntegrityError:
                db.rollback()
                existing_count += 1
    
    print(f"✓ Permissions: {created_count} created, {existing_count} already existed")
