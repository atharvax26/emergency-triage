"""Unit tests for Unit of Work pattern.

Tests transaction management, rollback behavior, and nested transactions.

Requirements: 19.4, 19.5
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.unit_of_work import UnitOfWork, transactional_session
from app.models.patient import Patient
from app.models.user import User
from app.utils.exceptions import DatabaseError


@pytest.mark.asyncio
class TestUnitOfWork:
    """Test Unit of Work pattern implementation."""
    
    async def test_successful_commit(self):
        """Test that successful operations are committed."""
        # Create patient within UnitOfWork
        async with UnitOfWork() as uow:
            patient = Patient(
                mrn="MRN-20240101-0001",
                first_name="John",
                last_name="Doe",
                date_of_birth="1990-01-01",
                gender="male",
                contact_info={"phone": "555-0100"},
                medical_history={}
            )
            uow.session.add(patient)
            await uow.session.flush()
            patient_id = patient.id
        
        # Verify patient was committed
        async with UnitOfWork() as uow:
            stmt = select(Patient).where(Patient.id == patient_id)
            result = await uow.session.execute(stmt)
            saved_patient = result.scalar_one_or_none()
            
            assert saved_patient is not None
            assert saved_patient.mrn == "MRN-20240101-0001"
            assert saved_patient.first_name == "John"
    
    async def test_automatic_rollback_on_exception(self):
        """Test that exceptions trigger automatic rollback."""
        patient_id = None
        
        try:
            async with UnitOfWork() as uow:
                patient = Patient(
                    mrn="MRN-20240101-0002",
                    first_name="Jane",
                    last_name="Doe",
                    date_of_birth="1990-01-01",
                    gender="female",
                    contact_info={"phone": "555-0101"},
                    medical_history={}
                )
                uow.session.add(patient)
                await uow.session.flush()
                patient_id = patient.id
                
                # Trigger exception
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Verify patient was NOT committed
        async with UnitOfWork() as uow:
            stmt = select(Patient).where(Patient.id == patient_id)
            result = await uow.session.execute(stmt)
            saved_patient = result.scalar_one_or_none()
            
            assert saved_patient is None
    
    async def test_explicit_rollback(self):
        """Test explicit rollback method."""
        async with UnitOfWork() as uow:
            patient = Patient(
                mrn="MRN-20240101-0003",
                first_name="Bob",
                last_name="Smith",
                date_of_birth="1990-01-01",
                gender="male",
                contact_info={"phone": "555-0102"},
                medical_history={}
            )
            uow.session.add(patient)
            await uow.session.flush()
            patient_id = patient.id
            
            # Explicit rollback
            await uow.rollback()
        
        # Verify patient was NOT committed
        async with UnitOfWork() as uow:
            stmt = select(Patient).where(Patient.id == patient_id)
            result = await uow.session.execute(stmt)
            saved_patient = result.scalar_one_or_none()
            
            assert saved_patient is None
    
    async def test_flush_before_commit(self):
        """Test flush to get auto-generated IDs before commit."""
        async with UnitOfWork() as uow:
            patient = Patient(
                mrn="MRN-20240101-0004",
                first_name="Alice",
                last_name="Johnson",
                date_of_birth="1990-01-01",
                gender="female",
                contact_info={"phone": "555-0103"},
                medical_history={}
            )
            uow.session.add(patient)
            
            # Flush to get ID
            await uow.flush()
            
            # ID should be available
            assert patient.id is not None
            patient_id = patient.id
        
        # Verify patient was committed
        async with UnitOfWork() as uow:
            stmt = select(Patient).where(Patient.id == patient_id)
            result = await uow.session.execute(stmt)
            saved_patient = result.scalar_one_or_none()
            
            assert saved_patient is not None
    
    async def test_nested_transactions(self):
        """Test nested transaction support via SAVEPOINT."""
        async with UnitOfWork() as outer_uow:
            # Create first patient in outer transaction
            patient1 = Patient(
                mrn="MRN-20240101-0005",
                first_name="Outer",
                last_name="Patient",
                date_of_birth="1990-01-01",
                gender="male",
                contact_info={"phone": "555-0104"},
                medical_history={}
            )
            outer_uow.session.add(patient1)
            await outer_uow.flush()
            patient1_id = patient1.id
            
            # Nested transaction
            try:
                async with UnitOfWork(outer_uow.session) as inner_uow:
                    patient2 = Patient(
                        mrn="MRN-20240101-0006",
                        first_name="Inner",
                        last_name="Patient",
                        date_of_birth="1990-01-01",
                        gender="female",
                        contact_info={"phone": "555-0105"},
                        medical_history={}
                    )
                    inner_uow.session.add(patient2)
                    await inner_uow.flush()
                    
                    # Trigger exception in nested transaction
                    raise ValueError("Nested exception")
            except ValueError:
                pass
            
            # Outer transaction should still be valid
        
        # Verify first patient was committed
        async with UnitOfWork() as uow:
            stmt = select(Patient).where(Patient.id == patient1_id)
            result = await uow.session.execute(stmt)
            saved_patient = result.scalar_one_or_none()
            
            assert saved_patient is not None
            assert saved_patient.first_name == "Outer"
    
    async def test_multiple_operations_atomic(self):
        """Test that multiple operations are atomic."""
        patient_id = None
        
        try:
            async with UnitOfWork() as uow:
                # Create patient
                patient = Patient(
                    mrn="MRN-20240101-0007",
                    first_name="Multi",
                    last_name="Op",
                    date_of_birth="1990-01-01",
                    gender="male",
                    contact_info={"phone": "555-0106"},
                    medical_history={}
                )
                uow.session.add(patient)
                await uow.session.flush()
                patient_id = patient.id
                
                # Update patient
                patient.first_name = "Updated"
                
                # Trigger exception
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Verify neither create nor update was committed
        async with UnitOfWork() as uow:
            stmt = select(Patient).where(Patient.id == patient_id)
            result = await uow.session.execute(stmt)
            saved_patient = result.scalar_one_or_none()
            
            assert saved_patient is None
    
    async def test_transactional_session_context_manager(self):
        """Test transactional_session context manager."""
        async with transactional_session() as session:
            patient = Patient(
                mrn="MRN-20240101-0008",
                first_name="Context",
                last_name="Manager",
                date_of_birth="1990-01-01",
                gender="female",
                contact_info={"phone": "555-0107"},
                medical_history={}
            )
            session.add(patient)
            await session.flush()
            patient_id = patient.id
        
        # Verify patient was committed
        async with UnitOfWork() as uow:
            stmt = select(Patient).where(Patient.id == patient_id)
            result = await uow.session.execute(stmt)
            saved_patient = result.scalar_one_or_none()
            
            assert saved_patient is not None
            assert saved_patient.first_name == "Context"
    
    async def test_constraint_violation_rollback(self):
        """Test that constraint violations trigger rollback."""
        # Create first patient
        async with UnitOfWork() as uow:
            patient1 = Patient(
                mrn="MRN-20240101-0009",
                first_name="First",
                last_name="Patient",
                date_of_birth="1990-01-01",
                gender="male",
                contact_info={"phone": "555-0108"},
                medical_history={}
            )
            uow.session.add(patient1)
        
        # Try to create duplicate MRN
        try:
            async with UnitOfWork() as uow:
                patient2 = Patient(
                    mrn="MRN-20240101-0009",  # Duplicate MRN
                    first_name="Second",
                    last_name="Patient",
                    date_of_birth="1990-01-01",
                    gender="female",
                    contact_info={"phone": "555-0109"},
                    medical_history={}
                )
                uow.session.add(patient2)
                await uow.session.flush()
        except IntegrityError:
            pass
        
        # Verify only first patient exists
        async with UnitOfWork() as uow:
            stmt = select(Patient).where(Patient.mrn == "MRN-20240101-0009")
            result = await uow.session.execute(stmt)
            patients = result.scalars().all()
            
            assert len(patients) == 1
            assert patients[0].first_name == "First"
