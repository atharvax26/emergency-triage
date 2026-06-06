"""Patient Intake Service for managing patient records."""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.cache.client import RedisClient
from app.cache.keys import CacheKeys
from app.core.patients.validators import validate_patient_data
from app.models.patient import Patient
from app.schemas.patient import (
    PatientCreateDTO,
    PatientUpdateDTO,
    PatientResponse,
    SearchCriteria,
    PatientListResponse,
    ValidationResult
)
from app.utils.exceptions import ValidationError, ConflictError, NotFoundError


class PatientIntakeService:
    """
    Patient Intake Service for managing patient records.
    
    Handles patient data validation, creation, retrieval, updates, and search
    with Redis caching for performance optimization.
    
    Requirements: 4.1-4.8, 5.1-5.5, 12.5
    """
    
    def __init__(self, db: AsyncSession, cache: RedisClient):
        """
        Initialize Patient Intake Service.
        
        Args:
            db: Database session
            cache: Redis cache client
        """
        self.db = db
        self.cache = cache
        self._cache_ttl = 300  # 5 minutes
    
    async def create_patient(self, data: PatientCreateDTO) -> Patient:
        """
        Create a new patient record with validation and MRN generation.
        
        Uses database-level unique constraint enforcement to prevent duplicate MRNs
        under concurrent access scenarios.
        
        Args:
            data: Patient creation data
            
        Returns:
            Created patient record
            
        Raises:
            ValidationError: If patient data is invalid
            ConflictError: If MRN already exists
            
        Requirements: 4.1, 4.2, 4.3, 19.1
        """
        # Validate patient data
        patient_dict = data.model_dump()
        validate_patient_data(patient_dict, is_update=False)
        
        # Generate unique MRN with database-level locking
        mrn = await self._generate_mrn()
        
        # Create patient record
        patient = Patient(
            mrn=mrn,
            first_name=data.first_name,
            last_name=data.last_name,
            date_of_birth=data.date_of_birth,
            gender=data.gender.lower(),
            contact_info=data.contact_info,
            medical_history=data.medical_history or {}
        )
        
        try:
            self.db.add(patient)
            await self.db.commit()
            await self.db.refresh(patient)
            
            # Cache the patient record
            await self._cache_patient(patient)
            
            return patient
            
        except IntegrityError as e:
            await self.db.rollback()
            if "mrn" in str(e.orig) or "uq_patients_mrn" in str(e.orig):
                raise ConflictError(
                    message="Patient with this MRN already exists",
                    details={"mrn": mrn}
                )
            raise ConflictError(
                message="Patient record conflicts with existing data",
                details={"error": str(e.orig)}
            )
    
    async def get_patient(self, patient_id: UUID) -> Optional[Patient]:
        """
        Get patient by ID with Redis caching.
        
        Args:
            patient_id: Patient unique identifier
            
        Returns:
            Patient record if found, None otherwise
            
        Requirements: 5.3, 5.4, 12.5
        """
        # Try cache first
        cache_key = CacheKeys.patient(patient_id)
        cached_data = await self.cache.get_json(cache_key)
        
        if cached_data:
            # Reconstruct patient from cache
            return await self._patient_from_cache(cached_data)
        
        # Cache miss - fetch from database
        result = await self.db.execute(
            select(Patient).where(Patient.id == patient_id)
        )
        patient = result.scalar_one_or_none()
        
        if patient:
            # Cache the patient record
            await self._cache_patient(patient)
        
        return patient
    
    async def update_patient(
        self,
        patient_id: UUID,
        data: PatientUpdateDTO
    ) -> Patient:
        """
        Update patient record with immutable field preservation.
        
        Args:
            patient_id: Patient unique identifier
            data: Patient update data
            
        Returns:
            Updated patient record
            
        Raises:
            NotFoundError: If patient not found
            ValidationError: If update data is invalid
            
        Requirements: 4.6, 5.5, 12.8
        """
        # Get existing patient
        patient = await self.get_patient(patient_id)
        if not patient:
            raise NotFoundError(
                message="Patient not found",
                details={"patient_id": str(patient_id)}
            )
        
        # Validate update data
        update_dict = data.model_dump(exclude_unset=True)
        if update_dict:
            validate_patient_data(update_dict, is_update=True)
        
        # Update only provided fields (preserve immutable fields)
        if data.first_name is not None:
            patient.first_name = data.first_name
        if data.last_name is not None:
            patient.last_name = data.last_name
        if data.date_of_birth is not None:
            patient.date_of_birth = data.date_of_birth
        if data.gender is not None:
            patient.gender = data.gender.lower()
        if data.contact_info is not None:
            patient.contact_info = data.contact_info
        if data.medical_history is not None:
            patient.medical_history = data.medical_history
        
        # Note: id, mrn, created_at are immutable and not updated
        
        try:
            await self.db.commit()
            await self.db.refresh(patient)
            
            # Invalidate cache
            await self._invalidate_patient_cache(patient_id)
            
            # Cache updated patient
            await self._cache_patient(patient)
            
            return patient
            
        except IntegrityError as e:
            await self.db.rollback()
            raise ConflictError(
                message="Patient update conflicts with existing data",
                details={"error": str(e.orig)}
            )
    
    async def search_patients(
        self,
        criteria: SearchCriteria
    ) -> PatientListResponse:
        """
        Search patients with case-insensitive matching and pagination.
        
        Args:
            criteria: Search criteria
            
        Returns:
            Paginated list of patients
            
        Requirements: 4.8, 5.1, 5.2
        """
        # Build query
        query = select(Patient)
        filters = []
        
        if criteria.mrn:
            filters.append(Patient.mrn == criteria.mrn)
        
        if criteria.first_name:
            filters.append(
                func.lower(Patient.first_name).contains(criteria.first_name.lower())
            )
        
        if criteria.last_name:
            filters.append(
                func.lower(Patient.last_name).contains(criteria.last_name.lower())
            )
        
        if criteria.date_of_birth:
            filters.append(Patient.date_of_birth == criteria.date_of_birth)
        
        if filters:
            query = query.where(or_(*filters))
        
        # Get total count
        count_query = select(func.count()).select_from(Patient)
        if filters:
            count_query = count_query.where(or_(*filters))
        
        total_count_result = await self.db.execute(count_query)
        total_count = total_count_result.scalar()
        
        # Apply pagination
        offset = (criteria.page - 1) * criteria.page_size
        query = query.offset(offset).limit(criteria.page_size)
        
        # Execute query
        result = await self.db.execute(query)
        patients = result.scalars().all()
        
        # Calculate total pages
        total_pages = (total_count + criteria.page_size - 1) // criteria.page_size
        
        # Convert to response DTOs
        patient_responses = [
            PatientResponse(
                id=p.id,
                mrn=p.mrn,
                first_name=p.first_name,
                last_name=p.last_name,
                date_of_birth=p.date_of_birth,
                gender=p.gender,
                contact_info=p.contact_info,
                medical_history=p.medical_history,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat()
            )
            for p in patients
        ]
        
        return PatientListResponse(
            patients=patient_responses,
            total_count=total_count,
            page=criteria.page,
            page_size=criteria.page_size,
            total_pages=total_pages
        )
    
    async def validate_patient_data(
        self,
        data: PatientCreateDTO
    ) -> ValidationResult:
        """
        Validate patient data without creating a record.
        
        Args:
            data: Patient data to validate
            
        Returns:
            Validation result with errors if any
        """
        try:
            patient_dict = data.model_dump()
            validate_patient_data(patient_dict, is_update=False)
            return ValidationResult(is_valid=True, errors=None)
        except ValidationError as e:
            return ValidationResult(
                is_valid=False,
                errors=[{"field": e.details.get("field", "unknown"), "message": e.message}]
            )
    
    async def _generate_mrn(self) -> str:
        """
        Generate unique MRN in format MRN-YYYYMMDD-XXXX.
        
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
        
        result = await self.db.execute(count_query)
        count = result.scalar()
        
        # Generate sequential number (1-based)
        sequence = count + 1
        sequence_str = str(sequence).zfill(4)
        
        mrn = f"MRN-{date_part}-{sequence_str}"
        
        # Verify uniqueness (in case of race condition)
        existing = await self.db.execute(
            select(Patient).where(Patient.mrn == mrn)
        )
        if existing.scalar_one_or_none():
            # Retry with incremented sequence
            sequence += 1
            sequence_str = str(sequence).zfill(4)
            mrn = f"MRN-{date_part}-{sequence_str}"
        
        return mrn
    
    async def _cache_patient(self, patient: Patient) -> None:
        """
        Cache patient record in Redis.
        
        Args:
            patient: Patient record to cache
        """
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
    
    async def _invalidate_patient_cache(self, patient_id: UUID) -> None:
        """
        Invalidate patient cache.
        
        Args:
            patient_id: Patient unique identifier
            
        Requirements: 5.5, 12.8
        """
        cache_key = CacheKeys.patient(patient_id)
        await self.cache.delete(cache_key)
    
    async def _patient_from_cache(self, cached_data: dict) -> Patient:
        """
        Reconstruct patient object from cached data.
        
        Args:
            cached_data: Cached patient data
            
        Returns:
            Patient object
        """
        # Note: This returns a detached Patient object (not attached to session)
        # For read operations, this is fine. For updates, fetch from DB.
        patient = Patient(
            id=UUID(cached_data["id"]),
            mrn=cached_data["mrn"],
            first_name=cached_data["first_name"],
            last_name=cached_data["last_name"],
            date_of_birth=date.fromisoformat(cached_data["date_of_birth"]),
            gender=cached_data["gender"],
            contact_info=cached_data["contact_info"],
            medical_history=cached_data["medical_history"]
        )
        # Set timestamps
        patient.created_at = datetime.fromisoformat(cached_data["created_at"])
        patient.updated_at = datetime.fromisoformat(cached_data["updated_at"])
        
        return patient
