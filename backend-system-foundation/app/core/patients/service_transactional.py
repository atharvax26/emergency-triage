"""Transactional patient intake service methods.

This module demonstrates how to refactor patient intake operations
to use the Unit of Work pattern for atomic multi-step workflows.

Requirements: 19.4, 19.5
"""

from datetime import date, datetime
from typing import Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.cache.client import RedisClient
from app.cache.keys import CacheKeys
from app.core.idempotency import IdempotencyManager
from app.core.patients.validators import validate_patient_data
from app.core.queue.validators import validate_priority, validate_symptoms
from app.core.unit_of_work import UnitOfWork
from app.models.patient import Patient
from app.models.queue import QueueEntry
from app.schemas.patient import PatientCreateDTO
from app.schemas.queue import QueueEntryCreate
from app.utils.exceptions import ValidationError, ConflictError


class TransactionalPatientIntakeService:
    """
    Patient Intake Service with transactional operations.
    
    This demonstrates the refactored approach using Unit of Work pattern
    for atomic multi-step workflows like patient creation + queue entry.
    
    Requirements: 19.4, 19.5
    """
    
    def __init__(self, cache: RedisClient):
        """
        Initialize TransactionalPatientIntakeService.
        
        Args:
            cache: Redis cache client
        """
        self.cache = cache
        self._cache_ttl = 300  # 5 minutes
    
    async def create_patient_and_add_to_queue(
        self,
        patient_data: PatientCreateDTO,
        queue_data: QueueEntryCreate,
        idempotency_key: str = None
    ) -> Tuple[Patient, QueueEntry]:
        """
        Atomically create patient and add to queue.
        
        This is a critical multi-step workflow that must be atomic:
        1. Validate patient data
        2. Generate unique MRN
        3. Create patient record
        4. Validate queue data
        5. Create queue entry
        
        If any step fails, all changes are rolled back.
        
        Args:
            patient_data: Patient creation data
            queue_data: Queue entry creation data
            idempotency_key: Optional idempotency key for duplicate prevention
            
        Returns:
            Tuple of (Patient, QueueEntry)
            
        Raises:
            ValidationError: If validation fails
            ConflictError: If MRN or queue entry already exists
            
        Requirements: 4.1, 4.2, 4.3, 6.1, 6.2, 19.4, 19.5
        """
        # Check idempotency if key provided
        if idempotency_key:
            manager = IdempotencyManager(self.cache)
            existing_result = await manager.get_result(
                idempotency_key,
                "create_patient_and_queue"
            )
            if existing_result:
                # Return cached result
                patient_id = UUID(existing_result["patient_id"])
                queue_entry_id = UUID(existing_result["queue_entry_id"])
                
                # Fetch from database
                async with UnitOfWork() as uow:
                    patient = await uow.session.get(Patient, patient_id)
                    queue_entry = await uow.session.get(QueueEntry, queue_entry_id)
                    return patient, queue_entry
            
            # Acquire idempotency lock
            can_proceed = await manager.check_and_set(
                idempotency_key,
                "create_patient_and_queue"
            )
            if not can_proceed:
                raise ConflictError("Request already in progress")
        
        # Validate patient data
        patient_dict = patient_data.model_dump()
        validate_patient_data(patient_dict, is_update=False)
        
        # Validate queue data
        is_valid, error = validate_priority(queue_data.priority)
        if not is_valid:
            raise ValidationError(error)
        
        is_valid, error = validate_symptoms(queue_data.symptoms)
        if not is_valid:
            raise ValidationError(error)
        
        # Use Unit of Work for atomic transaction
        async with UnitOfWork() as uow:
            # Generate unique MRN
            mrn = await self._generate_mrn(uow)
            
            # Create patient record
            patient = Patient(
                mrn=mrn,
                first_name=patient_data.first_name,
                last_name=patient_data.last_name,
                date_of_birth=patient_data.date_of_birth,
                gender=patient_data.gender.lower(),
                contact_info=patient_data.contact_info,
                medical_history=patient_data.medical_history or {}
            )
            uow.session.add(patient)
            
            # Flush to get patient ID
            await uow.session.flush()
            
            # Check for existing active queue entry
            active_statuses = ["waiting", "assigned", "in_progress"]
            stmt = select(QueueEntry).where(
                QueueEntry.patient_id == patient.id,
                QueueEntry.status.in_(active_statuses)
            )
            result = await uow.session.execute(stmt)
            existing_entry = result.scalar_one_or_none()
            
            if existing_entry:
                raise ConflictError(
                    f"Patient already has an active queue entry"
                )
            
            # Create queue entry
            queue_entry = QueueEntry(
                patient_id=patient.id,
                priority=queue_data.priority,
                status="waiting",
                symptoms=queue_data.symptoms,
                vital_signs=queue_data.vital_signs,
                arrival_time=datetime.utcnow(),
            )
            uow.session.add(queue_entry)
            
            # Flush to get queue entry ID
            await uow.session.flush()
            
            # Transaction commits automatically on context exit
        
        # After successful transaction, update cache
        await self._cache_patient(patient)
        await self._invalidate_queue_cache()
        
        # Store result for idempotency
        if idempotency_key:
            manager = IdempotencyManager(self.cache)
            await manager.store_result(
                idempotency_key,
                "create_patient_and_queue",
                {
                    "patient_id": str(patient.id),
                    "queue_entry_id": str(queue_entry.id)
                }
            )
        
        return patient, queue_entry
    
    async def _generate_mrn(self, uow: UnitOfWork) -> str:
        """
        Generate unique MRN in format MRN-YYYYMMDD-XXXX.
        
        Args:
            uow: Unit of Work with active session
            
        Returns:
            Generated MRN
            
        Requirements: 4.2, 4.3
        """
        today = date.today()
        date_part = today.strftime("%Y%m%d")
        
        # Get count of patients created today
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        count_query = select(func.count()).select_from(Patient).where(
            Patient.created_at >= today_start,
            Patient.created_at <= today_end
        )
        
        result = await uow.session.execute(count_query)
        count = result.scalar()
        
        # Generate sequential number (1-based)
        sequence = count + 1
        sequence_str = str(sequence).zfill(4)
        
        mrn = f"MRN-{date_part}-{sequence_str}"
        
        # Verify uniqueness (in case of race condition)
        existing = await uow.session.execute(
            select(Patient).where(Patient.mrn == mrn)
        )
        if existing.scalar_one_or_none():
            # Retry with incremented sequence
            sequence += 1
            sequence_str = str(sequence).zfill(4)
            mrn = f"MRN-{date_part}-{sequence_str}"
        
        return mrn
    
    async def _cache_patient(self, patient: Patient) -> None:
        """Cache patient record in Redis."""
        cache_key = CacheKeys.patient(patient.id)
        patient_data = {
            "id": str(patient.id),
            "mrn": patient.mrn,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "date_of_birth": patient.date_of_birth.isoformat(),
            "gender": patient.gender,
            "contact_info": patient.contact_info,
            "medical_history": patient.medical_history,
            "created_at": patient.created_at.isoformat(),
            "updated_at": patient.updated_at.isoformat()
        }
        await self.cache.set_json(cache_key, patient_data, ttl=self._cache_ttl)
    
    async def _invalidate_queue_cache(self) -> None:
        """Invalidate queue cache."""
        await self.cache.delete(CacheKeys.active_queue())
        await self.cache.delete(CacheKeys.queue_stats())
