"""Seed script for test users (one per role)."""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user import User, Role, UserRole
from app.core.auth.password import hash_password


def seed_users(db: Session, roles: dict[str, Role]) -> dict[str, User]:
    """
    Seed test users into the database (idempotent).
    
    Creates one user per role with known credentials for testing:
    - Nurse: nurse@example.com / NursePassword123!
    - Doctor: doctor@example.com / DoctorPassword123!
    - Admin: admin@example.com / AdminPassword123!
    
    All passwords meet complexity requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    
    Args:
        db: Database session
        roles: Dictionary mapping role names to Role objects
        
    Returns:
        Dictionary mapping role names to User objects
        
    Requirements: 1.6, 14.1
    """
    users_data = [
        {
            "email": "nurse@example.com",
            "password": "NursePassword123!",
            "first_name": "Jane",
            "last_name": "Nurse",
            "role": "nurse"
        },
        {
            "email": "doctor@example.com",
            "password": "DoctorPassword123!",
            "first_name": "John",
            "last_name": "Doctor",
            "role": "doctor"
        },
        {
            "email": "admin@example.com",
            "password": "AdminPassword123!",
            "first_name": "Alice",
            "last_name": "Admin",
            "role": "admin"
        }
    ]
    
    users = {}
    
    for user_data in users_data:
        role_name = user_data["role"]
        role = roles.get(role_name)
        
        if not role:
            print(f"⚠ Warning: Role '{role_name}' not found, skipping user")
            continue
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()
        
        if existing_user:
            users[role_name] = existing_user
            print(f"✓ User '{user_data['email']}' already exists")
            
            # Ensure user has the correct role
            existing_user_role = db.query(UserRole).filter(
                UserRole.user_id == existing_user.id,
                UserRole.role_id == role.id
            ).first()
            
            if not existing_user_role:
                user_role = UserRole(user_id=existing_user.id, role_id=role.id)
                db.add(user_role)
                try:
                    db.commit()
                    print(f"  ✓ Assigned role '{role_name}' to existing user")
                except IntegrityError:
                    db.rollback()
        else:
            # Create new user
            user = User(
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                is_active=True
            )
            db.add(user)
            try:
                db.commit()
                db.refresh(user)
                
                # Assign role to user
                user_role = UserRole(user_id=user.id, role_id=role.id)
                db.add(user_role)
                db.commit()
                
                users[role_name] = user
                print(f"✓ Created user '{user_data['email']}' with role '{role_name}'")
            except IntegrityError:
                db.rollback()
                # Race condition: another process created it
                existing_user = db.query(User).filter(User.email == user_data["email"]).first()
                users[role_name] = existing_user
                print(f"✓ User '{user_data['email']}' already exists (race condition)")
    
    return users
