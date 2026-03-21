"""QueueEngine service for emergency triage queue management."""

import json
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.cache.client import RedisClient
from app.cache.keys import CacheKeys
from app.core.queue.validators import (
    validate_priority,
    validate_status,
    validate_status_transition,
    validate_symptoms,
    validate_vital_signs,
)
from app.models.queue import Assignment, QueueEntry
from app.models.user import User, Role
from app.schemas.queue import (
    QueueEntryCreate,
    QueueEntryUpdate,
    QueueFilters,
    QueueStats,
    AssignmentCreate,
)
from app.utils.exceptions import (
    ValidationError,
    NotFoundError,
    ConflictError,
    AuthorizationError,
)


class QueueEngine:
    """
    Queue Engine for managing emergency triage queue.
    
    Responsibilities:
    - Queue entry creation and management
    - Priority-based queue ordering
    - Patient-doctor assignment tracking
    - Queue state persistence and caching
    - Real-time queue statistics
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.1, 7.2, 7.3, 7.4, 7.5, 12.6, 19.2, 19.3
    """
    
    def __init__(self, db: AsyncSession, cache: RedisClient):
        """
        Initialize QueueEngine.
        
        Args:
            db: Database session
            cache: Redis cache client
        """
        self.db = db
        self.cache = cache
    
    async def add_to_queue(
        self,
        data: QueueEntryCreate,
    ) -> QueueEntry:
        """
        Add a patient to the queue with duplicate prevention.
        
        Uses database-level locking (SELECT FOR UPDATE) to prevent race conditions
        when checking for existing active queue entries under concurrent access.
        
        Validates:
        - Priority is within bounds (1-10)
        - Symptoms contain required fields
        - Vital signs are valid if provided
        - Patient doesn't already have an active queue entry
        
        Args:
            data: Queue entry creation data
            
        Returns:
            Created queue entry
            
        Raises:
            ValidationError: If validation fails
            ConflictError: If patient already has active queue entry
            
        Requirements: 6.1, 6.2, 19.2
        Property 16: Single Active Queue Entry
        """
        # Validate priority
        is_valid, error = validate_priority(data.priority)
        if not is_valid:
            raise ValidationError(error)
        
        # Validate symptoms
        is_valid, error = validate_symptoms(data.symptoms)
        if not is_valid:
            raise ValidationError(error)
        
        # Validate vital signs if provided
        is_valid, error = validate_vital_signs(data.vital_signs)
        if not is_valid:
            raise ValidationError(error)
        
        # Check for existing active queue entry with row-level locking
        # This prevents race conditions when multiple requests try to add
        # the same patient to the queue concurrently
        active_statuses = ["waiting", "assigned", "in_progress"]
        stmt = select(QueueEntry).where(
            and_(
                QueueEntry.patient_id == data.patient_id,
                QueueEntry.status.in_(active_statuses)
            )
        ).with_for_update()
        
        result = await self.db.execute(stmt)
        existing_entry = result.scalar_one_or_none()
        
        if existing_entry:
            raise ConflictError(
                f"Patient already has an active queue entry (ID: {existing_entry.id}, Status: {existing_entry.status})"
            )
        
        # Create queue entry
        queue_entry = QueueEntry(
            patient_id=data.patient_id,
            priority=data.priority,
            status="waiting",
            symptoms=data.symptoms,
            vital_signs=data.vital_signs,
            arrival_time=datetime.utcnow(),
        )
        
        self.db.add(queue_entry)
        await self.db.commit()
        await self.db.refresh(queue_entry)
        
        # Invalidate queue cache
        await self._invalidate_queue_cache()
        
        return queue_entry
    
    async def get_queue(
        self,
        filters: Optional[QueueFilters] = None,
    ) -> List[QueueEntry]:
        """
        Get queue entries with priority ordering and Redis caching.
        
        Queue ordering:
        1. Higher priority first (descending)
        2. Within same priority, FIFO by arrival_time (ascending)
        
        Cache TTL: 1 minute
        
        Args:
            filters: Optional filters for status, priority range, date range, pagination
            
        Returns:
            List of queue entries ordered by priority
            
        Requirements: 6.3, 6.6, 6.7, 12.6
        Property 17: Queue Priority Ordering
        """
        if filters is None:
            filters = QueueFilters()
        
        # Try to get from cache (only for default filters)
        if self._is_default_filters(filters):
            cache_key = CacheKeys.active_queue()
            cached_data = await self.cache.get_json(cache_key)
            
            if cached_data:
                # Reconstruct queue entries from cached data
                return await self._reconstruct_queue_entries(cached_data)
        
        # Build query
        stmt = select(QueueEntry)
        
        # Apply filters
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
            stmt = stmt.where(and_(*conditions))
        
        # Order by priority (descending) then arrival_time (ascending) - FIFO within priority
        stmt = stmt.order_by(
            QueueEntry.priority.desc(),
            QueueEntry.arrival_time.asc()
        )
        
        # Apply pagination
        offset = (filters.page - 1) * filters.page_size
        stmt = stmt.offset(offset).limit(filters.page_size)
        
        # Execute query
        result = await self.db.execute(stmt)
        entries = result.scalars().all()
        
        # Cache if default filters
        if self._is_default_filters(filters):
            await self._cache_queue_entries(entries)
        
        return list(entries)
    
    async def update_priority(
        self,
        entry_id: UUID,
        new_priority: int,
    ) -> QueueEntry:
        """
        Update queue entry priority.
        
        Args:
            entry_id: Queue entry ID
            new_priority: New priority value (1-10)
            
        Returns:
            Updated queue entry
            
        Raises:
            ValidationError: If priority is invalid
            NotFoundError: If queue entry not found
            
        Requirements: 6.1, 6.6
        """
        # Validate priority
        is_valid, error = validate_priority(new_priority)
        if not is_valid:
            raise ValidationError(error)
        
        # Get queue entry
        stmt = select(QueueEntry).where(QueueEntry.id == entry_id)
        result = await self.db.execute(stmt)
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise NotFoundError(f"Queue entry not found: {entry_id}")
        
        # Update priority
        entry.priority = new_priority
        await self.db.commit()
        await self.db.refresh(entry)
        
        # Invalidate cache
        await self._invalidate_queue_cache()
        
        return entry
    
    async def update_queue_entry(
        self,
        entry_id: UUID,
        data: QueueEntryUpdate,
    ) -> QueueEntry:
        """
        Update queue entry with cache invalidation.
        
        Validates status transitions according to state machine.
        
        Args:
            entry_id: Queue entry ID
            data: Update data
            
        Returns:
            Updated queue entry
            
        Raises:
            ValidationError: If validation fails
            NotFoundError: If queue entry not found
            
        Requirements: 6.4, 6.5, 6.6, 12.8
        Property 19: Valid Status Transitions
        """
        # Get queue entry
        stmt = select(QueueEntry).where(QueueEntry.id == entry_id)
        result = await self.db.execute(stmt)
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise NotFoundError(f"Queue entry not found: {entry_id}")
        
        # Validate and update priority
        if data.priority is not None:
            is_valid, error = validate_priority(data.priority)
            if not is_valid:
                raise ValidationError(error)
            entry.priority = data.priority
        
        # Validate and update status
        if data.status is not None:
            is_valid, error = validate_status_transition(entry.status, data.status)
            if not is_valid:
                raise ValidationError(error)
            entry.status = data.status
        
        # Validate and update symptoms
        if data.symptoms is not None:
            is_valid, error = validate_symptoms(data.symptoms)
            if not is_valid:
                raise ValidationError(error)
            entry.symptoms = data.symptoms
        
        # Validate and update vital signs
        if data.vital_signs is not None:
            is_valid, error = validate_vital_signs(data.vital_signs)
            if not is_valid:
                raise ValidationError(error)
            entry.vital_signs = data.vital_signs
        
        await self.db.commit()
        await self.db.refresh(entry)
        
        # Invalidate cache
        await self._invalidate_queue_cache()
        
        return entry
    
    async def remove_from_queue(
        self,
        entry_id: UUID,
    ) -> bool:
        """
        Remove queue entry (soft delete by setting status to cancelled).
        
        Args:
            entry_id: Queue entry ID
            
        Returns:
            True if successful
            
        Raises:
            NotFoundError: If queue entry not found
            
        Requirements: 6.6
        """
        # Get queue entry
        stmt = select(QueueEntry).where(QueueEntry.id == entry_id)
        result = await self.db.execute(stmt)
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise NotFoundError(f"Queue entry not found: {entry_id}")
        
        # Validate status transition to cancelled
        is_valid, error = validate_status_transition(entry.status, "cancelled")
        if not is_valid:
            raise ValidationError(error)
        
        # Set status to cancelled
        entry.status = "cancelled"
        await self.db.commit()
        
        # Invalidate cache
        await self._invalidate_queue_cache()
        
        return True
    
    async def get_queue_statistics(self) -> QueueStats:
        """
        Get queue statistics with caching.
        
        Cache TTL: 1 minute
        
        Returns:
            Queue statistics
            
        Requirements: 6.7, 12.6
        """
        # Try to get from cache
        cache_key = CacheKeys.queue_stats()
        cached_stats = await self.cache.get_json(cache_key)
        
        if cached_stats:
            return QueueStats(**cached_stats)
        
        # Calculate statistics
        # Count by status
        status_counts = await self.db.execute(
            select(
                QueueEntry.status,
                func.count(QueueEntry.id).label("count")
            ).group_by(QueueEntry.status)
        )
        
        status_dict = {row.status: row.count for row in status_counts}
        
        # Calculate priority statistics
        priority_stats = await self.db.execute(
            select(
                func.count(QueueEntry.id).label("total"),
                func.avg(QueueEntry.priority).label("avg_priority"),
                func.sum(func.case((QueueEntry.priority >= 9, 1), else_=0)).label("critical"),
                func.sum(func.case((and_(QueueEntry.priority >= 7, QueueEntry.priority < 9), 1), else_=0)).label("high"),
                func.sum(func.case((and_(QueueEntry.priority >= 4, QueueEntry.priority < 7), 1), else_=0)).label("medium"),
                func.sum(func.case((QueueEntry.priority < 4, 1), else_=0)).label("low"),
            )
        )
        
        stats_row = priority_stats.one()
        
        stats = QueueStats(
            total_entries=stats_row.total or 0,
            waiting=status_dict.get("waiting", 0),
            assigned=status_dict.get("assigned", 0),
            in_progress=status_dict.get("in_progress", 0),
            completed=status_dict.get("completed", 0),
            cancelled=status_dict.get("cancelled", 0),
            avg_priority=float(stats_row.avg_priority or 0),
            critical_count=stats_row.critical or 0,
            high_count=stats_row.high or 0,
            medium_count=stats_row.medium or 0,
            low_count=stats_row.low or 0,
        )
        
        # Cache statistics
        await self.cache.set_json(cache_key, stats.model_dump(), ttl=60)
        
        return stats
    
    async def assign_patient(
        self,
        data: AssignmentCreate,
    ) -> Assignment:
        """
        Assign a patient to a doctor.
        
        Uses database-level locking (SELECT FOR UPDATE) to prevent race conditions
        when checking for existing assignments and updating queue entry status.
        
        Validates:
        - Assigned user has doctor role
        - Queue entry exists and is not completed/cancelled
        - No active assignment already exists
        
        Updates queue entry status to 'assigned'.
        
        Args:
            data: Assignment creation data
            
        Returns:
            Created assignment
            
        Raises:
            NotFoundError: If queue entry or doctor not found
            AuthorizationError: If user doesn't have doctor role
            ConflictError: If active assignment already exists
            ValidationError: If status transition is invalid
            
        Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 19.3
        Property 20: Doctor Role Required for Assignment
        Property 21: Single Active Assignment
        Property 51: Queue Entry Status Update on Assignment
        """
        # Get queue entry with row-level lock to prevent concurrent assignments
        stmt = select(QueueEntry).where(
            QueueEntry.id == data.queue_entry_id
        ).with_for_update()
        
        result = await self.db.execute(stmt)
        queue_entry = result.scalar_one_or_none()
        
        if not queue_entry:
            raise NotFoundError(f"Queue entry not found: {data.queue_entry_id}")
        
        # Verify queue entry is not completed or cancelled
        if queue_entry.status in ["completed", "cancelled"]:
            raise ValidationError(f"Cannot assign queue entry with status: {queue_entry.status}")
        
        # Get doctor and verify role
        stmt = select(User).where(User.id == data.doctor_id)
        result = await self.db.execute(stmt)
        doctor = result.scalar_one_or_none()
        
        if not doctor:
            raise NotFoundError(f"Doctor not found: {data.doctor_id}")
        
        # Verify doctor has doctor role
        stmt = select(Role).join(User.roles).where(
            and_(
                User.id == data.doctor_id,
                Role.name == "doctor"
            )
        )
        result = await self.db.execute(stmt)
        has_doctor_role = result.scalar_one_or_none() is not None
        
        if not has_doctor_role:
            raise AuthorizationError(f"User {data.doctor_id} does not have doctor role")
        
        # Check for existing active assignment with row-level lock
        stmt = select(Assignment).where(
            and_(
                Assignment.queue_entry_id == data.queue_entry_id,
                Assignment.status == "active"
            )
        ).with_for_update()
        
        result = await self.db.execute(stmt)
        existing_assignment = result.scalar_one_or_none()
        
        if existing_assignment:
            raise ConflictError(
                f"Queue entry already has an active assignment (ID: {existing_assignment.id})"
            )
        
        # Validate status transition to assigned
        is_valid, error = validate_status_transition(queue_entry.status, "assigned")
        if not is_valid:
            raise ValidationError(error)
        
        # Create assignment
        assignment = Assignment(
            queue_entry_id=data.queue_entry_id,
            doctor_id=data.doctor_id,
            assigned_at=datetime.utcnow(),
            status="active",
        )
        
        # Update queue entry status
        queue_entry.status = "assigned"
        
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)
        
        # Invalidate cache
        await self._invalidate_queue_cache()
        
        return assignment
    
    # Private helper methods
    
    def _is_default_filters(self, filters: QueueFilters) -> bool:
        """Check if filters are default (for caching)."""
        return (
            filters.status is None
            and filters.min_priority is None
            and filters.max_priority is None
            and filters.from_date is None
            and filters.to_date is None
            and filters.page == 1
            and filters.page_size == 50
        )
    
    async def _cache_queue_entries(self, entries: List[QueueEntry]) -> None:
        """Cache queue entries."""
        cache_key = CacheKeys.active_queue()
        
        # Serialize entries
        entries_data = [
            {
                "id": str(entry.id),
                "patient_id": str(entry.patient_id),
                "priority": entry.priority,
                "status": entry.status,
                "symptoms": entry.symptoms,
                "vital_signs": entry.vital_signs,
                "arrival_time": entry.arrival_time.isoformat(),
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
            }
            for entry in entries
        ]
        
        # Cache with 1-minute TTL
        await self.cache.set_json(cache_key, entries_data, ttl=60)
    
    async def _reconstruct_queue_entries(self, cached_data: List[Dict]) -> List[QueueEntry]:
        """Reconstruct queue entries from cached data."""
        entries = []
        
        for data in cached_data:
            entry = QueueEntry(
                id=UUID(data["id"]),
                patient_id=UUID(data["patient_id"]),
                priority=data["priority"],
                status=data["status"],
                symptoms=data["symptoms"],
                vital_signs=data["vital_signs"],
                arrival_time=datetime.fromisoformat(data["arrival_time"]),
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
            )
            entries.append(entry)
        
        return entries
    
    async def _invalidate_queue_cache(self) -> None:
        """Invalidate queue cache."""
        await self.cache.delete(CacheKeys.active_queue())
        await self.cache.delete(CacheKeys.queue_stats())
