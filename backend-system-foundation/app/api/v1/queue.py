"""Queue management API endpoints."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.cache.client import RedisClient, get_redis
from app.core.queue.service import QueueEngine
from app.database.session import get_async_db
from app.schemas.queue import (
    AssignmentCreate,
    AssignmentResponse,
    QueueEntryCreate,
    QueueEntryResponse,
    QueueEntryUpdate,
    QueueFilters,
    QueueListResponse,
    QueueStats,
)
from app.utils.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


router = APIRouter(prefix="/queue", tags=["Queue Management"])


# Dependency to get QueueEngine
async def get_queue_engine(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    cache: Annotated[RedisClient, Depends(get_redis)]
) -> QueueEngine:
    """
    Dependency to get QueueEngine instance.
    
    Args:
        db: Database session
        cache: Redis client
        
    Returns:
        QueueEngine instance
    """
    return QueueEngine(db=db, cache=cache)


# Role-based permission check dependencies
async def check_nurse_permission(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """
    Dependency to check if current user has nurse role or higher.
    
    Args:
        current_user: Current authenticated user from JWT token
        
    Returns:
        Current user dict if authorized
        
    Raises:
        HTTPException: 403 if user doesn't have required role
    """
    user_roles = current_user.get("roles", [])
    allowed_roles = {"nurse", "doctor", "admin"}
    
    if not any(role in allowed_roles for role in user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nurse, doctor, or admin permission required"
        )
    return current_user


async def check_doctor_permission(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """
    Dependency to check if current user has doctor role or higher.
    
    Args:
        current_user: Current authenticated user from JWT token
        
    Returns:
        Current user dict if authorized
        
    Raises:
        HTTPException: 403 if user doesn't have required role
    """
    user_roles = current_user.get("roles", [])
    allowed_roles = {"doctor", "admin"}
    
    if not any(role in allowed_roles for role in user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor or admin permission required"
        )
    return current_user


async def check_admin_permission(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """
    Dependency to check if current user has admin role.
    
    Args:
        current_user: Current authenticated user from JWT token
        
    Returns:
        Current user dict if admin
        
    Raises:
        HTTPException: 403 if user is not admin
    """
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required"
        )
    return current_user


@router.get(
    "",
    response_model=QueueListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current queue",
    description="Get current queue with filters and sorting (nurse, doctor, or admin)"
)
async def get_queue(
    status_filter: Annotated[str | None, Query(alias="status", description="Filter by status")] = None,
    min_priority: Annotated[int | None, Query(ge=1, le=10, description="Minimum priority")] = None,
    max_priority: Annotated[int | None, Query(ge=1, le=10, description="Maximum priority")] = None,
    from_date: Annotated[str | None, Query(description="Filter from date (ISO format)")] = None,
    to_date: Annotated[str | None, Query(description="Filter to date (ISO format)")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    queue_engine: Annotated[QueueEngine, Depends(get_queue_engine)] = None,
    current_user: Annotated[dict, Depends(check_nurse_permission)] = None,
) -> QueueListResponse:
    """
    Get current queue with filters and sorting.
    
    Queue is ordered by:
    1. Priority (descending)
    2. Arrival time (ascending - FIFO within same priority)
    
    Args:
        status_filter: Filter by status (waiting, assigned, in_progress, completed, cancelled)
        min_priority: Minimum priority (1-10)
        max_priority: Maximum priority (1-10)
        from_date: Filter from date (ISO format)
        to_date: Filter to date (ISO format)
        page: Page number (starts at 1)
        page_size: Number of items per page (max 100)
        queue_engine: QueueEngine instance
        current_user: Current authenticated user
        
    Returns:
        QueueListResponse with paginated queue entries
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not authorized
        HTTPException: 422 if validation fails
        HTTPException: 500 if service error
    """
    try:
        # Parse dates if provided
        from datetime import datetime
        from_date_parsed = datetime.fromisoformat(from_date) if from_date else None
        to_date_parsed = datetime.fromisoformat(to_date) if to_date else None
        
        # Build filters
        filters = QueueFilters(
            status=status_filter,
            min_priority=min_priority,
            max_priority=max_priority,
            from_date=from_date_parsed,
            to_date=to_date_parsed,
            page=page,
            page_size=page_size
        )
        
        # Get queue entries
        entries = await queue_engine.get_queue(filters)
        
        # Get total count for pagination
        from sqlalchemy import and_, func, select
        from app.models.queue import QueueEntry
        
        count_stmt = select(func.count(QueueEntry.id))
        
        # Apply same filters for count
        conditions = []
        if filters.status:
            conditions.append(QueueEntry.status == filters.status)
        if filters.min_priority is not None:
            conditions.append(QueueEntry.priority >= filters.min_priority)
        if filters.max_priority is not None:
            conditions.append(QueueEntry.priority <= filters.max_priority)
        if filters.from_date:
            conditions.append(QueueEntry.arrival_time >= filters.from_date)
        if filters.to_date:
            conditions.append(QueueEntry.arrival_time <= filters.to_date)
        
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        
        count_result = await queue_engine.db.execute(count_stmt)
        total_count = count_result.scalar_one()
        
        # Calculate total pages
        total_pages = ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response models
        entry_responses = [QueueEntryResponse.model_validate(entry) for entry in entries]
        
        return QueueListResponse(
            entries=entry_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve queue"
        )


@router.post(
    "",
    response_model=QueueEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add patient to queue",
    description="Add a patient to the queue (nurse, doctor, or admin)"
)
async def add_to_queue(
    entry_data: QueueEntryCreate,
    queue_engine: Annotated[QueueEngine, Depends(get_queue_engine)],
    current_user: Annotated[dict, Depends(check_nurse_permission)],
) -> QueueEntryResponse:
    """
    Add a patient to the queue.
    
    Args:
        entry_data: Queue entry creation data
        queue_engine: QueueEngine instance
        current_user: Current authenticated user
        
    Returns:
        Created queue entry
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not authorized
        HTTPException: 409 if patient already has active queue entry
        HTTPException: 422 if validation fails
        HTTPException: 500 if service error
    """
    try:
        entry = await queue_engine.add_to_queue(entry_data)
        return QueueEntryResponse.model_validate(entry)
        
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add patient to queue"
        )


@router.get(
    "/{entry_id}",
    response_model=QueueEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get queue entry details",
    description="Get detailed information about a specific queue entry (nurse, doctor, or admin)"
)
async def get_queue_entry(
    entry_id: UUID,
    queue_engine: Annotated[QueueEngine, Depends(get_queue_engine)],
    current_user: Annotated[dict, Depends(check_nurse_permission)],
) -> QueueEntryResponse:
    """
    Get detailed information about a specific queue entry.
    
    Args:
        entry_id: Queue entry ID
        queue_engine: QueueEngine instance
        current_user: Current authenticated user
        
    Returns:
        Queue entry details
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not authorized
        HTTPException: 404 if queue entry not found
        HTTPException: 500 if service error
    """
    try:
        from sqlalchemy import select
        from app.models.queue import QueueEntry
        
        stmt = select(QueueEntry).where(QueueEntry.id == entry_id)
        result = await queue_engine.db.execute(stmt)
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Queue entry not found"
            )
        
        return QueueEntryResponse.model_validate(entry)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve queue entry"
        )


@router.put(
    "/{entry_id}",
    response_model=QueueEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update queue entry",
    description="Update queue entry information (doctor or admin)"
)
async def update_queue_entry(
    entry_id: UUID,
    entry_data: QueueEntryUpdate,
    queue_engine: Annotated[QueueEngine, Depends(get_queue_engine)],
    current_user: Annotated[dict, Depends(check_doctor_permission)],
) -> QueueEntryResponse:
    """
    Update queue entry information.
    
    Args:
        entry_id: Queue entry ID
        entry_data: Queue entry update data
        queue_engine: QueueEngine instance
        current_user: Current authenticated user
        
    Returns:
        Updated queue entry
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not authorized
        HTTPException: 404 if queue entry not found
        HTTPException: 422 if validation fails
        HTTPException: 500 if service error
    """
    try:
        entry = await queue_engine.update_queue_entry(entry_id, entry_data)
        return QueueEntryResponse.model_validate(entry)
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update queue entry"
        )


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove from queue",
    description="Remove patient from queue (soft delete, admin only)"
)
async def remove_from_queue(
    entry_id: UUID,
    queue_engine: Annotated[QueueEngine, Depends(get_queue_engine)],
    current_user: Annotated[dict, Depends(check_admin_permission)],
) -> dict:
    """
    Remove patient from queue (soft delete by setting status to cancelled).
    
    Args:
        entry_id: Queue entry ID
        queue_engine: QueueEngine instance
        current_user: Current authenticated user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if queue entry not found
        HTTPException: 422 if validation fails
        HTTPException: 500 if service error
    """
    try:
        await queue_engine.remove_from_queue(entry_id)
        
        return {
            "message": "Queue entry removed successfully",
            "entry_id": str(entry_id)
        }
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove queue entry"
        )


@router.post(
    "/{entry_id}/assign",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign patient to doctor",
    description="Assign a patient to a doctor (doctor or admin)"
)
async def assign_patient(
    entry_id: UUID,
    doctor_id: UUID,
    queue_engine: Annotated[QueueEngine, Depends(get_queue_engine)],
    current_user: Annotated[dict, Depends(check_doctor_permission)],
) -> AssignmentResponse:
    """
    Assign a patient to a doctor.
    
    Args:
        entry_id: Queue entry ID
        doctor_id: Doctor (user) ID
        queue_engine: QueueEngine instance
        current_user: Current authenticated user
        
    Returns:
        Created assignment
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not authorized or user doesn't have doctor role
        HTTPException: 404 if queue entry or doctor not found
        HTTPException: 409 if active assignment already exists
        HTTPException: 422 if validation fails
        HTTPException: 500 if service error
    """
    try:
        assignment_data = AssignmentCreate(
            queue_entry_id=entry_id,
            doctor_id=doctor_id
        )
        
        assignment = await queue_engine.assign_patient(assignment_data)
        return AssignmentResponse.model_validate(assignment)
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign patient"
        )


@router.get(
    "/stats",
    response_model=QueueStats,
    status_code=status.HTTP_200_OK,
    summary="Get queue statistics",
    description="Get queue statistics (nurse, doctor, or admin)"
)
async def get_queue_statistics(
    queue_engine: Annotated[QueueEngine, Depends(get_queue_engine)],
    current_user: Annotated[dict, Depends(check_nurse_permission)],
) -> QueueStats:
    """
    Get queue statistics.
    
    Args:
        queue_engine: QueueEngine instance
        current_user: Current authenticated user
        
    Returns:
        Queue statistics
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not authorized
        HTTPException: 500 if service error
    """
    try:
        stats = await queue_engine.get_queue_statistics()
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve queue statistics"
        )
