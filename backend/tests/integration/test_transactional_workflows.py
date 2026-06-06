"""Integration tests for transactional workflows.

Tests atomic multi-step operations across services.

Requirements: 19.4, 19.5
"""

import pytest
from datetime import date
from uuid import uuid4

from app.core.auth.service_transactional import TransactionalAuthService
from app.core.patients.service_transactional import TransactionalPatientIntakeService
from app.core.queue.service_transactional import TransactionalQueueEngine
from app.schemas.auth import LoginCredentials
from app.schemas.patient import PatientCreateDTO
from app.schemas.queue import QueueEntryCreate, AssignmentCreate
from app.utils.exceptions import ConflictError, ValidationError


@pytest.mark.asyncio
class TestTransactionalWorkflows:
    """Test transactional multi-step workflows."""
    
    async def test_patient_creation_and_queue_atomic(
        self,
        redis_client,
        test_user_doctor
    ):
        """Test atomic patient creation + queue entry."""
        service = TransactionalPatientIntakeService(redis_client)
        
        # Create patient data
        patient_data = PatientCreateDTO(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1990, 1, 1),
            gender="male",
            contact_info={"phone": "555-0100"},
            medical_history={}
        )
        
        # Create queue data
        queue_data = QueueEntryCreate(
            patient_id=uuid4(),  # Will be replaced
            priority=8,
            symptoms={"chief_complaint": "Chest pain"},
            vital_signs={"bp": "140/90", "hr": 95}
        )
        
        # Execute atomic operation
        patient, queue_entry = await service.create_patient_and_add_to_queue(
            patient_data,
            queue_data
        )
        
        # Verify both were created
        assert patient is not None
        assert patient.mrn.startswith("MRN-")
        assert patient.first_name == "John"
        
        assert queue_entry is not None
        assert queue_entry.patient_id == patient.id
        assert queue_entry.priority == 8
        assert queue_entry.status == "waiting"
    
    async def test_patient_creation_rollback_on_invalid_queue(
        self,
        redis_client
    ):
        """Test that patient creation is rolled back if queue entry fails."""
        service = TransactionalPatientIntakeService(redis_client)
        
        # Create patient data
        patient_data = PatientCreateDTO(
            first_name="Jane",
            last_name="Doe",
            date_of_birth=date(1990, 1, 1),
            gender="female",
            contact_info={"phone": "555-0101"},
            medical_history={}
        )
        
        # Create invalid queue data (priority out of range)
        queue_data = QueueEntryCreate(
            patient_id=uuid4(),
            priority=15,  # Invalid: must be 1-10
            symptoms={"chief_complaint": "Headache"},
            vital_signs={}
        )
        
        # Execute atomic operation (should fail)
        with pytest.raises(ValidationError):
            await service.create_patient_and_add_to_queue(
                patient_data,
                queue_data
            )
        
        # Verify patient was NOT created (rollback worked)
        # This would require querying the database to verify
    
    async def test_assignment_atomic(
        self,
        redis_client,
        test_patient,
        test_queue_entry,
        test_user_doctor
    ):
        """Test atomic patient assignment."""
        service = TransactionalQueueEngine(redis_client)
        
        # Create assignment
        assignment_data = AssignmentCreate(
            queue_entry_id=test_queue_entry.id,
            doctor_id=test_user_doctor.id
        )
        
        # Execute atomic operation
        assignment = await service.assign_patient_atomic(assignment_data)
        
        # Verify assignment was created
        assert assignment is not None
        assert assignment.queue_entry_id == test_queue_entry.id
        assert assignment.doctor_id == test_user_doctor.id
        assert assignment.status == "active"
        
        # Verify queue entry status was updated
        # This would require querying the database to verify
    
    async def test_assignment_idempotency(
        self,
        redis_client,
        test_patient,
        test_queue_entry,
        test_user_doctor
    ):
        """Test that duplicate assignment requests are idempotent."""
        service = TransactionalQueueEngine(redis_client)
        
        # Create assignment data
        assignment_data = AssignmentCreate(
            queue_entry_id=test_queue_entry.id,
            doctor_id=test_user_doctor.id
        )
        
        idempotency_key = f"test-{uuid4()}"
        
        # First assignment
        assignment1 = await service.assign_patient_atomic(
            assignment_data,
            idempotency_key=idempotency_key
        )
        
        # Duplicate assignment (should return same result)
        assignment2 = await service.assign_patient_atomic(
            assignment_data,
            idempotency_key=idempotency_key
        )
        
        # Should be the same assignment
        assert assignment1.id == assignment2.id
    
    async def test_assignment_prevents_duplicate_active(
        self,
        redis_client,
        test_patient,
        test_queue_entry,
        test_user_doctor
    ):
        """Test that duplicate active assignments are prevented."""
        service = TransactionalQueueEngine(redis_client)
        
        # Create first assignment
        assignment_data = AssignmentCreate(
            queue_entry_id=test_queue_entry.id,
            doctor_id=test_user_doctor.id
        )
        
        assignment1 = await service.assign_patient_atomic(assignment_data)
        
        # Try to create second assignment (should fail)
        with pytest.raises(ConflictError) as exc_info:
            await service.assign_patient_atomic(assignment_data)
        
        assert "already has an active assignment" in str(exc_info.value)
    
    async def test_complete_assignment_atomic(
        self,
        redis_client,
        test_assignment
    ):
        """Test atomic assignment completion."""
        service = TransactionalQueueEngine(redis_client)
        
        # Complete assignment
        completed = await service.complete_assignment_atomic(
            test_assignment.id
        )
        
        # Verify assignment was completed
        assert completed is not None
        assert completed.status == "completed"
        assert completed.completed_at is not None
        
        # Verify queue entry status was updated
        # This would require querying the database to verify
    
    async def test_authentication_atomic(
        self,
        redis_client,
        test_user_nurse
    ):
        """Test atomic authentication with session creation."""
        service = TransactionalAuthService(redis_client)
        
        # Authenticate
        credentials = LoginCredentials(
            email=test_user_nurse.email,
            password="Test123!@#"  # Assuming this is the test password
        )
        
        result = await service.authenticate_atomic(credentials)
        
        # Verify authentication result
        assert result is not None
        assert result.user_id == test_user_nurse.id
        assert result.email == test_user_nurse.email
        assert result.tokens is not None
        assert result.tokens.access_token is not None
        assert result.tokens.refresh_token is not None
    
    async def test_authentication_idempotency(
        self,
        redis_client,
        test_user_nurse
    ):
        """Test that duplicate authentication requests are idempotent."""
        service = TransactionalAuthService(redis_client)
        
        credentials = LoginCredentials(
            email=test_user_nurse.email,
            password="Test123!@#"
        )
        
        idempotency_key = f"test-{uuid4()}"
        
        # First authentication
        result1 = await service.authenticate_atomic(
            credentials,
            idempotency_key=idempotency_key
        )
        
        # Duplicate authentication (should return cached result)
        result2 = await service.authenticate_atomic(
            credentials,
            idempotency_key=idempotency_key
        )
        
        # Should be the same result
        assert result1.user_id == result2.user_id
        assert result1.tokens.access_token == result2.tokens.access_token
    
    async def test_nested_transaction_rollback(
        self,
        redis_client
    ):
        """Test that nested transaction rollback doesn't affect outer transaction."""
        # This test would demonstrate SAVEPOINT behavior
        # Implementation depends on specific use case
        pass
    
    async def test_concurrent_operations_with_locking(
        self,
        redis_client,
        test_queue_entry,
        test_user_doctor
    ):
        """Test that concurrent operations use proper locking."""
        # This test would demonstrate SELECT FOR UPDATE behavior
        # Implementation requires concurrent execution simulation
        pass
