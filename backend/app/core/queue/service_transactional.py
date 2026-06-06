"""Transactional queue service methods.

This module demonstrates how to refactor queue operations
to use the Unit of Work pattern for atomic multi-step workflows.

Requirements: 19.4, 19.5
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.cache.client import RedisClient
from app.cache.keys import CacheKeys
from app.core.idempotency import IdempotencyManager
from app.core.queue.validators import validate_status_transition
from app.core.unit_of_work import UnitOfWork
from app.models.queue import Assignment, QueueEntry
from app.models.user import User, Role
from app.schemas.queue import AssignmentCreate
from app.utils.exceptions import (
    NotFoundError,
    AuthorizationError,
    ConflictError,
    ValidationError,
)


class TransactionalQueueEngine:
    """
    Queue Engine with transactional operations.
    
    This demonstrates the refactored approach using Unit of Work pattern
    for atomic multi-step workflows like patient assignment.
    
    Requirements: 19.4, 19.5
    """
    
    def __init__(self, cache: RedisClient):
        """
        Initialize TransactionalQueueEngine.
        
        Args:
            cache: Redis cache client
        """
        self.cache = cache
    
    async def assign_patient_atomic(
        self,
        data: AssignmentCreate,
        idempotency_key: str = None
    ) -> Assignment:
        """
        Atomically assign a patient to a doctor.
        
        This is a critical multi-step workflow that must be atomic:
        1. Verify queue entry exists and is assignable
        2. Verify doctor exists and has doctor role
        3. Check for existing active assignment
        4. Create assignment record
        5. Update queue entry status to 'assigned'
        
        If any step fails, all changes are rolled back.
        
        Args:
            data: Assignment creation data
            idempotency_key: Optional idempotency key for duplicate prevention
            
        Returns:
            Created assignment
            
        Raises:
            NotFoundError: If queue entry or doctor not found
            AuthorizationError: If user doesn't have doctor role
            ConflictError: If active assignment already exists
            ValidationError: If status transition is invalid
            
        Requirements: 7.1, 7.2, 7.3, 7.4, 19.3, 19.4, 19.5
        """
        # Check idempotency if key provided
        if idempotency_key:
            manager = IdempotencyManager(self.cache)
            existing_result = await manager.get_result(
                idempotency_key,
                "assign_patient"
            )
            if existing_result:
                # Return cached result
                assignment_id = UUID(existing_result)
                async with UnitOfWork() as uow:
                    assignment = await uow.session.get(Assignment, assignment_id)
                    return assignment
            
            # Acquire idempotency lock
            can_proceed = await manager.check_and_set(
                idempotency_key,
                "assign_patient"
            )
            if not can_proceed:
                raise ConflictError("Assignment request already in progress")
        
        # Use Unit of Work for atomic transaction
        async with UnitOfWork() as uow:
            # Get queue entry with lock (SELECT FOR UPDATE)
            stmt = select(QueueEntry).where(
                QueueEntry.id == data.queue_entry_id
            ).with_for_update()
            result = await uow.session.execute(stmt)
            queue_entry = result.scalar_one_or_none()
            
            if not queue_entry:
                raise NotFoundError(
                    f"Queue entry not found: {data.queue_entry_id}"
                )
            
            # Verify queue entry is not completed or cancelled
            if queue_entry.status in ["completed", "cancelled"]:
                raise ValidationError(
                    f"Cannot assign queue entry with status: {queue_entry.status}"
                )
            
            # Get doctor and verify role
            stmt = select(User).where(
                User.id == data.doctor_id
            ).options(
                selectinload(User.user_roles).selectinload(User.user_roles)
            )
            result = await uow.session.execute(stmt)
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
            result = await uow.session.execute(stmt)
            has_doctor_role = result.scalar_one_or_none() is not None
            
            if not has_doctor_role:
                raise AuthorizationError(
                    f"User {data.doctor_id} does not have doctor role"
                )
            
            # Check for existing active assignment (with lock)
            stmt = select(Assignment).where(
                and_(
                    Assignment.queue_entry_id == data.queue_entry_id,
                    Assignment.status == "active"
                )
            ).with_for_update()
            result = await uow.session.execute(stmt)
            existing_assignment = result.scalar_one_or_none()
            
            if existing_assignment:
                raise ConflictError(
                    f"Queue entry already has an active assignment "
                    f"(ID: {existing_assignment.id})"
                )
            
            # Validate status transition to assigned
            is_valid, error = validate_status_transition(
                queue_entry.status,
                "assigned"
            )
            if not is_valid:
                raise ValidationError(error)
            
            # Create assignment
            assignment = Assignment(
                queue_entry_id=data.queue_entry_id,
                doctor_id=data.doctor_id,
                assigned_at=datetime.utcnow(),
                status="active",
            )
            uow.session.add(assignment)
            
            # Update queue entry status
            queue_entry.status = "assigned"
            
            # Flush to get assignment ID
            await uow.session.flush()
            
            # Transaction commits automatically on context exit
        
        # After successful transaction, invalidate cache
        await self._invalidate_queue_cache()
        
        # Store result for idempotency
        if idempotency_key:
            manager = IdempotencyManager(self.cache)
            await manager.store_result(
                idempotency_key,
                "assign_patient",
                str(assignment.id)
            )
        
        return assignment
    
    async def complete_assignment_atomic(
        self,
        assignment_id: UUID,
        idempotency_key: str = None
    ) -> Assignment:
        """
        Atomically complete an assignment.
        
        This is a multi-step workflow that must be atomic:
        1. Verify assignment exists and is active
        2. Update assignment status to 'completed'
        3. Set completion timestamp
        4. Update queue entry status to 'completed'
        
        If any step fails, all changes are rolled back.
        
        Args:
            assignment_id: Assignment ID
            idempotency_key: Optional idempotency key for duplicate prevention
            
        Returns:
            Updated assignment
            
        Raises:
            NotFoundError: If assignment not found
            ValidationError: If assignment is not active
            
        Requirements: 7.5, 7.6, 19.4, 19.5
        """
        # Check idempotency if key provided
        if idempotency_key:
            manager = IdempotencyManager(self.cache)
            existing_result = await manager.get_result(
                idempotency_key,
                "complete_assignment"
            )
            if existing_result:
                # Return cached result
                async with UnitOfWork() as uow:
                    assignment = await uow.session.get(Assignment, assignment_id)
                    return assignment
            
            # Acquire idempotency lock
            can_proceed = await manager.check_and_set(
                idempotency_key,
                "complete_assignment"
            )
            if not can_proceed:
                raise ConflictError("Completion request already in progress")
        
        # Use Unit of Work for atomic transaction
        async with UnitOfWork() as uow:
            # Get assignment with lock
            stmt = select(Assignment).where(
                Assignment.id == assignment_id
            ).with_for_update()
            result = await uow.session.execute(stmt)
            assignment = result.scalar_one_or_none()
            
            if not assignment:
                raise NotFoundError(f"Assignment not found: {assignment_id}")
            
            # Verify assignment is active
            if assignment.status != "active":
                raise ValidationError(
                    f"Cannot complete assignment with status: {assignment.status}"
                )
            
            # Get queue entry with lock
            stmt = select(QueueEntry).where(
                QueueEntry.id == assignment.queue_entry_id
            ).with_for_update()
            result = await uow.session.execute(stmt)
            queue_entry = result.scalar_one_or_none()
            
            if not queue_entry:
                raise NotFoundError(
                    f"Queue entry not found: {assignment.queue_entry_id}"
                )
            
            # Validate status transition
            is_valid, error = validate_status_transition(
                queue_entry.status,
                "completed"
            )
            if not is_valid:
                raise ValidationError(error)
            
            # Update assignment
            assignment.status = "completed"
            assignment.completed_at = datetime.utcnow()
            
            # Update queue entry
            queue_entry.status = "completed"
            
            # Transaction commits automatically on context exit
        
        # After successful transaction, invalidate cache
        await self._invalidate_queue_cache()
        
        # Store result for idempotency
        if idempotency_key:
            manager = IdempotencyManager(self.cache)
            await manager.store_result(
                idempotency_key,
                "complete_assignment",
                str(assignment.id)
            )
        
        return assignment
    
    async def _invalidate_queue_cache(self) -> None:
        """Invalidate queue cache."""
        await self.cache.delete(CacheKeys.active_queue())
        await self.cache.delete(CacheKeys.queue_stats())
