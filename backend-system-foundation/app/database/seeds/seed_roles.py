"""Seed script for roles (nurse, doctor, admin)."""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user import Role


def seed_roles(db: Session) -> dict[str, Role]:
    """
    Seed roles into the database (idempotent).
    
    Creates three roles: nurse, doctor, admin.
    If roles already exist, returns existing roles.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary mapping role names to Role objects
        
    Requirements: 2.1
    """
    roles_data = [
        {
            "name": "nurse",
            "description": "Nurse role with patient intake and basic queue viewing permissions"
        },
        {
            "name": "doctor",
            "description": "Doctor role with full queue access, patient assignment, and triage decisions"
        },
        {
            "name": "admin",
            "description": "Administrator role with full system access including user management and audit logs"
        }
    ]
    
    roles = {}
    
    for role_data in roles_data:
        # Check if role already exists
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        
        if existing_role:
            roles[role_data["name"]] = existing_role
            print(f"✓ Role '{role_data['name']}' already exists")
        else:
            # Create new role
            role = Role(**role_data)
            db.add(role)
            try:
                db.commit()
                db.refresh(role)
                roles[role_data["name"]] = role
                print(f"✓ Created role '{role_data['name']}'")
            except IntegrityError:
                db.rollback()
                # Race condition: another process created it
                existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
                roles[role_data["name"]] = existing_role
                print(f"✓ Role '{role_data['name']}' already exists (race condition)")
    
    return roles
