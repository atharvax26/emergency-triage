"""Patient Intake API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.cache.client import RedisClient, get_redis
from app.core.patients.service import PatientIntakeService
from app.database.session import get_async_db
from app.schemas.patient import (
    PatientCreateDTO,
    PatientUpdateDTO,
    PatientResponse,
    SearchCriteria,
    PatientListResponse,
)
from app.utils.exceptions import (
    ValidationError,
    ConflictError,
    NotFoundError,
)


router = APIRouter(prefix="/patients", tags=["Patients"])


# Dependency to get PatientIntakeService
async def get_patient_service(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    cache: Annotated[RedisClient, Depends(get_redis)]
) -> PatientIntakeService:
    """
    Dependency to get PatientIntakeService instance.
    
    Args:
        db: Database session
        cache: Redis client
        
    Returns:
        PatientIntakeService instance
    """
    return PatientIntakeService(db=db, cache=cache)


# Dependency to check user has required roles for patient access
async def check_patient_access(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """
    Dependency to verify user has access to patient endpoints.
    
    Allowed roles: nurse, doctor, admin
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user dict
        
    Raises:
        HTTPException: 403 if user doesn't have required role
    """
    allowed_roles = {"nurse", "doctor", "admin"}
    user_roles = set(current_user.get("roles", []))
    
    if not user_roles.intersection(allowed_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Requires nurse, doctor, or admin role.",
        )
    
    return current_user


@router.get(
    "",
    response_model=PatientListResponse,
    status_code=status.HTTP_200_OK,
    summary="List patients",
    description="Get paginated list of all patients"
)
async def list_patients(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Page size (max 100)")] = 50,
    current_user: Annotated[dict, Depends(check_patient_access)] = None,
    patient_service: Annotated[PatientIntakeService, Depends(get_patient_service)] = None
) -> PatientListResponse:
    """
    Get paginated list of all patients.
    
    Args:
        page: Page number (default: 1)
        page_size: Page size (default: 50, max: 100)
        current_user: Current authenticated user
        patient_service: PatientIntakeService instance
        
    Returns:
        Paginated list of patients
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if insufficient permissions
        HTTPException: 500 if service fails
    """
    try:
        # Use search with no criteria to get all patients
        criteria = SearchCriteria(page=page, page_size=page_size)
        result = await patient_service.search_patients(criteria)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve patients",
        )


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create patient",
    description="Create a new patient record with automatic MRN generation"
)
async def create_patient(
    data: PatientCreateDTO,
    current_user: Annotated[dict, Depends(check_patient_access)] = None,
    patient_service: Annotated[PatientIntakeService, Depends(get_patient_service)] = None
) -> PatientResponse:
    """
    Create a new patient record.
    
    Args:
        data: Patient creation data
        current_user: Current authenticated user
        patient_service: PatientIntakeService instance
        
    Returns:
        Created patient record
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if insufficient permissions
        HTTPException: 409 if MRN already exists
        HTTPException: 422 if validation fails
        HTTPException: 500 if service fails
    """
    try:
        patient = await patient_service.create_patient(data)
        
        return PatientResponse(
            id=patient.id,
            mrn=patient.mrn,
            first_name=patient.first_name,
            last_name=patient.last_name,
            date_of_birth=patient.date_of_birth,
            gender=patient.gender,
            contact_info=patient.contact_info,
            medical_history=patient.medical_history,
            created_at=patient.created_at.isoformat(),
            updated_at=patient.updated_at.isoformat()
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create patient",
        )


@router.get(
    "/search",
    response_model=PatientListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search patients",
    description="Search patients by MRN, name, or date of birth with pagination"
)
async def search_patients(
    mrn: Annotated[str | None, Query(description="Medical Record Number")] = None,
    first_name: Annotated[str | None, Query(description="First name (case-insensitive)")] = None,
    last_name: Annotated[str | None, Query(description="Last name (case-insensitive)")] = None,
    date_of_birth: Annotated[str | None, Query(description="Date of birth (YYYY-MM-DD)")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Page size (max 100)")] = 50,
    current_user: Annotated[dict, Depends(check_patient_access)] = None,
    patient_service: Annotated[PatientIntakeService, Depends(get_patient_service)] = None
) -> PatientListResponse:
    """
    Search patients by various criteria.
    
    Args:
        mrn: Medical Record Number
        first_name: First name (case-insensitive)
        last_name: Last name (case-insensitive)
        date_of_birth: Date of birth (YYYY-MM-DD format)
        page: Page number (default: 1)
        page_size: Page size (default: 50, max: 100)
        current_user: Current authenticated user
        patient_service: PatientIntakeService instance
        
    Returns:
        Paginated list of matching patients
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if insufficient permissions
        HTTPException: 422 if date format is invalid
        HTTPException: 500 if service fails
    """
    try:
        # Parse date_of_birth if provided
        from datetime import date as date_type
        dob = None
        if date_of_birth:
            try:
                dob = date_type.fromisoformat(date_of_birth)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid date format. Use YYYY-MM-DD",
                )
        
        # Build search criteria
        criteria = SearchCriteria(
            mrn=mrn,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=dob,
            page=page,
            page_size=page_size
        )
        
        result = await patient_service.search_patients(criteria)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search patients",
        )


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Get patient",
    description="Get patient details by ID"
)
async def get_patient(
    patient_id: UUID,
    current_user: Annotated[dict, Depends(check_patient_access)] = None,
    patient_service: Annotated[PatientIntakeService, Depends(get_patient_service)] = None
) -> PatientResponse:
    """
    Get patient details by ID.
    
    Args:
        patient_id: Patient unique identifier
        current_user: Current authenticated user
        patient_service: PatientIntakeService instance
        
    Returns:
        Patient record
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if insufficient permissions
        HTTPException: 404 if patient not found
        HTTPException: 500 if service fails
    """
    try:
        patient = await patient_service.get_patient(patient_id)
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID {patient_id} not found",
            )
        
        return PatientResponse(
            id=patient.id,
            mrn=patient.mrn,
            first_name=patient.first_name,
            last_name=patient.last_name,
            date_of_birth=patient.date_of_birth,
            gender=patient.gender,
            contact_info=patient.contact_info,
            medical_history=patient.medical_history,
            created_at=patient.created_at.isoformat(),
            updated_at=patient.updated_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve patient",
        )


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Update patient",
    description="Update patient record (MRN and ID are immutable)"
)
async def update_patient(
    patient_id: UUID,
    data: PatientUpdateDTO,
    current_user: Annotated[dict, Depends(check_patient_access)] = None,
    patient_service: Annotated[PatientIntakeService, Depends(get_patient_service)] = None
) -> PatientResponse:
    """
    Update patient record.
    
    Note: MRN and ID are immutable and cannot be changed.
    
    Args:
        patient_id: Patient unique identifier
        data: Patient update data
        current_user: Current authenticated user
        patient_service: PatientIntakeService instance
        
    Returns:
        Updated patient record
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if insufficient permissions
        HTTPException: 404 if patient not found
        HTTPException: 409 if update conflicts with existing data
        HTTPException: 422 if validation fails
        HTTPException: 500 if service fails
    """
    try:
        patient = await patient_service.update_patient(patient_id, data)
        
        return PatientResponse(
            id=patient.id,
            mrn=patient.mrn,
            first_name=patient.first_name,
            last_name=patient.last_name,
            date_of_birth=patient.date_of_birth,
            gender=patient.gender,
            contact_info=patient.contact_info,
            medical_history=patient.medical_history,
            created_at=patient.created_at.isoformat(),
            updated_at=patient.updated_at.isoformat()
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update patient",
        )
