"""Tests for database seed scripts."""

import pytest
from datetime import date, datetime
from sqlalchemy.exc import IntegrityError

from app.models.user import User, Role, Permission, UserRole
from app.models.patient import Patient
from app.models.queue import QueueEntry
from app.database.seeds import (
    seed_roles,
    seed_permissions,
    seed_users,
    seed_patients,
    seed_queue_entries,
)


class TestSeedRoles:
    """Test role seeding."""
    
    def test_seed_roles_creates_all_roles(self, db_session):
        """Test that seed_roles creates all three roles."""
        roles = seed_roles(db_session)
        
        assert len(roles) == 3
        assert "nurse" in roles
        assert "doctor" in roles
        assert "admin" in roles
        
        # Verify roles in database
        db_roles = db_session.query(Role).all()
        assert len(db_roles) == 3
        
        role_names = {role.name for role in db_roles}
        assert role_names == {"nurse", "doctor", "admin"}
    
    def test_seed_roles_is_idempotent(self, db_session):
        """Test that seed_roles can be run multiple times."""
        # First run
        roles1 = seed_roles(db_session)
        assert len(roles1) == 3
        
        # Second run
        roles2 = seed_roles(db_session)
        assert len(roles2) == 3
        
        # Should still have only 3 roles
        db_roles = db_session.query(Role).all()
        assert len(db_roles) == 3
        
        # IDs should match
        assert roles1["nurse"].id == roles2["nurse"].id
        assert roles1["doctor"].id == roles2["doctor"].id
        assert roles1["admin"].id == roles2["admin"].id
    
    def test_seed_roles_descriptions(self, db_session):
        """Test that roles have proper descriptions."""
        roles = seed_roles(db_session)
        
        assert "patient intake" in roles["nurse"].description.lower()
        assert "queue access" in roles["doctor"].description.lower()
        assert "administrator" in roles["admin"].description.lower()


class TestSeedPermissions:
    """Test permission seeding."""
    
    def test_seed_permissions_creates_all_permissions(self, db_session):
        """Test that seed_permissions creates all permissions."""
        roles = seed_roles(db_session)
        seed_permissions(db_session, roles)
        
        # Count permissions per role
        nurse_perms = db_session.query(Permission).filter(
            Permission.role_id == roles["nurse"].id
        ).all()
        doctor_perms = db_session.query(Permission).filter(
            Permission.role_id == roles["doctor"].id
        ).all()
        admin_perms = db_session.query(Permission).filter(
            Permission.role_id == roles["admin"].id
        ).all()
        
        # Nurse: 5 permissions (patient: create/read/update, queue: create/read)
        assert len(nurse_perms) == 5
        
        # Doctor: 8 permissions (all nurse + queue: update/assign/delete)
        assert len(doctor_perms) == 8
        
        # Admin: 16 permissions (all resources)
        assert len(admin_perms) == 16
    
    def test_seed_permissions_is_idempotent(self, db_session):
        """Test that seed_permissions can be run multiple times."""
        roles = seed_roles(db_session)
        
        # First run
        seed_permissions(db_session, roles)
        count1 = db_session.query(Permission).count()
        
        # Second run
        seed_permissions(db_session, roles)
        count2 = db_session.query(Permission).count()
        
        # Should have same count
        assert count1 == count2
    
    def test_seed_permissions_rbac_matrix(self, db_session):
        """Test that permissions match RBAC matrix."""
        roles = seed_roles(db_session)
        seed_permissions(db_session, roles)
        
        # Nurse cannot assign patients
        nurse_assign = db_session.query(Permission).filter(
            Permission.role_id == roles["nurse"].id,
            Permission.resource == "queue",
            Permission.action == "assign"
        ).first()
        assert nurse_assign is None
        
        # Doctor can assign patients
        doctor_assign = db_session.query(Permission).filter(
            Permission.role_id == roles["doctor"].id,
            Permission.resource == "queue",
            Permission.action == "assign"
        ).first()
        assert doctor_assign is not None
        
        # Admin can access audit logs
        admin_audit = db_session.query(Permission).filter(
            Permission.role_id == roles["admin"].id,
            Permission.resource == "audit",
            Permission.action == "read"
        ).first()
        assert admin_audit is not None
        
        # Nurse cannot access audit logs
        nurse_audit = db_session.query(Permission).filter(
            Permission.role_id == roles["nurse"].id,
            Permission.resource == "audit"
        ).first()
        assert nurse_audit is None


class TestSeedUsers:
    """Test user seeding."""
    
    def test_seed_users_creates_all_users(self, db_session):
        """Test that seed_users creates one user per role."""
        roles = seed_roles(db_session)
        users = seed_users(db_session, roles)
        
        assert len(users) == 3
        assert "nurse" in users
        assert "doctor" in users
        assert "admin" in users
        
        # Verify users in database
        db_users = db_session.query(User).all()
        assert len(db_users) == 3
    
    def test_seed_users_is_idempotent(self, db_session):
        """Test that seed_users can be run multiple times."""
        roles = seed_roles(db_session)
        
        # First run
        users1 = seed_users(db_session, roles)
        assert len(users1) == 3
        
        # Second run
        users2 = seed_users(db_session, roles)
        assert len(users2) == 3
        
        # Should still have only 3 users
        db_users = db_session.query(User).all()
        assert len(db_users) == 3
        
        # IDs should match
        assert users1["nurse"].id == users2["nurse"].id
    
    def test_seed_users_credentials(self, db_session):
        """Test that users have correct credentials."""
        roles = seed_roles(db_session)
        users = seed_users(db_session, roles)
        
        assert users["nurse"].email == "nurse@example.com"
        assert users["doctor"].email == "doctor@example.com"
        assert users["admin"].email == "admin@example.com"
        
        # Verify passwords are hashed
        assert users["nurse"].password_hash != "NursePassword123!"
        assert len(users["nurse"].password_hash) > 50  # Bcrypt hashes are long
    
    def test_seed_users_role_assignments(self, db_session):
        """Test that users are assigned correct roles."""
        roles = seed_roles(db_session)
        users = seed_users(db_session, roles)
        
        # Check nurse role
        nurse_role = db_session.query(UserRole).filter(
            UserRole.user_id == users["nurse"].id,
            UserRole.role_id == roles["nurse"].id
        ).first()
        assert nurse_role is not None
        
        # Check doctor role
        doctor_role = db_session.query(UserRole).filter(
            UserRole.user_id == users["doctor"].id,
            UserRole.role_id == roles["doctor"].id
        ).first()
        assert doctor_role is not None
        
        # Check admin role
        admin_role = db_session.query(UserRole).filter(
            UserRole.user_id == users["admin"].id,
            UserRole.role_id == roles["admin"].id
        ).first()
        assert admin_role is not None


class TestSeedPatients:
    """Test patient seeding."""
    
    def test_seed_patients_creates_patients(self, db_session):
        """Test that seed_patients creates sample patients."""
        patients = seed_patients(db_session)
        
        assert len(patients) == 10
        
        # Verify patients in database
        db_patients = db_session.query(Patient).all()
        assert len(db_patients) == 10
    
    def test_seed_patients_is_idempotent(self, db_session):
        """Test that seed_patients can be run multiple times."""
        # First run
        patients1 = seed_patients(db_session)
        assert len(patients1) == 10
        
        # Second run
        patients2 = seed_patients(db_session)
        assert len(patients2) == 10
        
        # Should still have only 10 patients
        db_patients = db_session.query(Patient).all()
        assert len(db_patients) == 10
    
    def test_seed_patients_mrn_format(self, db_session):
        """Test that patients have valid MRN format."""
        patients = seed_patients(db_session)
        
        today = date.today()
        expected_prefix = f"MRN-{today.strftime('%Y%m%d')}-"
        
        for patient in patients:
            assert patient.mrn.startswith(expected_prefix)
            assert len(patient.mrn) == 20  # MRN-YYYYMMDD-XXXX
    
    def test_seed_patients_data_validity(self, db_session):
        """Test that patients have valid data."""
        patients = seed_patients(db_session)
        
        for patient in patients:
            # Check required fields
            assert patient.first_name
            assert patient.last_name
            assert patient.date_of_birth
            assert patient.gender in ["male", "female", "other", "unknown"]
            
            # Check date of birth is in the past
            assert patient.date_of_birth < date.today()
            
            # Check contact info
            assert isinstance(patient.contact_info, dict)
            assert "phone" in patient.contact_info or "email" in patient.contact_info
            
            # Check medical history (if present)
            if patient.medical_history:
                assert isinstance(patient.medical_history, dict)


class TestSeedQueueEntries:
    """Test queue entry seeding."""
    
    def test_seed_queue_entries_creates_entries(self, db_session):
        """Test that seed_queue_entries creates sample queue entries."""
        patients = seed_patients(db_session)
        queue_entries = seed_queue_entries(db_session, patients)
        
        assert len(queue_entries) > 0
        assert len(queue_entries) <= len(patients)
    
    def test_seed_queue_entries_is_idempotent(self, db_session):
        """Test that seed_queue_entries can be run multiple times."""
        patients = seed_patients(db_session)
        
        # First run
        entries1 = seed_queue_entries(db_session, patients)
        count1 = len(entries1)
        
        # Second run
        entries2 = seed_queue_entries(db_session, patients)
        count2 = len(entries2)
        
        # Should have same count (idempotent)
        assert count1 == count2
    
    def test_seed_queue_entries_data_validity(self, db_session):
        """Test that queue entries have valid data."""
        patients = seed_patients(db_session)
        queue_entries = seed_queue_entries(db_session, patients)
        
        for entry in queue_entries:
            # Check priority bounds
            assert 1 <= entry.priority <= 10
            
            # Check status
            assert entry.status in ["waiting", "assigned", "in_progress", "completed", "cancelled"]
            
            # Check symptoms
            assert isinstance(entry.symptoms, dict)
            assert "chief_complaint" in entry.symptoms
            
            # Check vital signs (if present)
            if entry.vital_signs:
                assert isinstance(entry.vital_signs, dict)
            
            # Check arrival time
            assert entry.arrival_time <= datetime.utcnow()
    
    def test_seed_queue_entries_one_active_per_patient(self, db_session):
        """Test that each patient has at most one active queue entry."""
        patients = seed_patients(db_session)
        queue_entries = seed_queue_entries(db_session, patients)
        
        active_statuses = ["waiting", "assigned", "in_progress"]
        
        for patient in patients:
            active_entries = db_session.query(QueueEntry).filter(
                QueueEntry.patient_id == patient.id,
                QueueEntry.status.in_(active_statuses)
            ).all()
            
            # Should have at most one active entry
            assert len(active_entries) <= 1


class TestFullSeedWorkflow:
    """Test complete seed workflow."""
    
    def test_full_seed_workflow(self, db_session):
        """Test running all seed scripts in sequence."""
        # Step 1: Seed roles
        roles = seed_roles(db_session)
        assert len(roles) == 3
        
        # Step 2: Seed permissions
        seed_permissions(db_session, roles)
        perms = db_session.query(Permission).all()
        assert len(perms) > 0
        
        # Step 3: Seed users
        users = seed_users(db_session, roles)
        assert len(users) == 3
        
        # Step 4: Seed patients
        patients = seed_patients(db_session)
        assert len(patients) == 10
        
        # Step 5: Seed queue entries
        queue_entries = seed_queue_entries(db_session, patients)
        assert len(queue_entries) > 0
        
        # Verify all data is in database
        assert db_session.query(Role).count() == 3
        assert db_session.query(User).count() == 3
        assert db_session.query(Patient).count() == 10
        assert db_session.query(QueueEntry).count() > 0
    
    def test_full_seed_workflow_idempotent(self, db_session):
        """Test that full workflow can be run multiple times."""
        # First run
        roles1 = seed_roles(db_session)
        seed_permissions(db_session, roles1)
        users1 = seed_users(db_session, roles1)
        patients1 = seed_patients(db_session)
        queue1 = seed_queue_entries(db_session, patients1)
        
        count1 = {
            "roles": db_session.query(Role).count(),
            "users": db_session.query(User).count(),
            "patients": db_session.query(Patient).count(),
            "queue": db_session.query(QueueEntry).count(),
        }
        
        # Second run
        roles2 = seed_roles(db_session)
        seed_permissions(db_session, roles2)
        users2 = seed_users(db_session, roles2)
        patients2 = seed_patients(db_session)
        queue2 = seed_queue_entries(db_session, patients2)
        
        count2 = {
            "roles": db_session.query(Role).count(),
            "users": db_session.query(User).count(),
            "patients": db_session.query(Patient).count(),
            "queue": db_session.query(QueueEntry).count(),
        }
        
        # Counts should be identical
        assert count1 == count2
