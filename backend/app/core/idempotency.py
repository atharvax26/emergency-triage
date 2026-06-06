"""Idempotency protection for critical operations.

This module provides Redis-based idempotency key management to prevent
duplicate operations from being executed multiple times. This is critical for:
- POST endpoints (resource creation)
- Payment processing
- Audit log generation
- Any operation that should not be repeated

Requirements: 19.4, 19.5
"""

import hashlib
import json
from typing import Any, Dict, Optional
from uuid import UUID

from app.cache.client import RedisClient
from app.cache.keys import CacheKeys
from app.utils.exceptions import ConflictError


class IdempotencyManager:
    """
    Manages idempotency keys for preventing duplicate operations.
    
    Uses Redis to store idempotency keys with TTL. When an operation
    is attempted with an idempotency key:
    1. If key doesn't exist: Store key and execute operation
    2. If key exists: Return cached result without executing
    
    This prevents:
    - Duplicate database writes
    - Duplicate audit logs
    - Race conditions in concurrent requests
    
    Requirements: 19.4, 19.5
    """
    
    def __init__(self, cache: RedisClient):
        """
        Initialize IdempotencyManager.
        
        Args:
            cache: Redis cache client
        """
        self.cache = cache
        self._default_ttl = 86400  # 24 hours
    
    async def check_and_set(
        self,
        idempotency_key: str,
        operation_type: str,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Check if operation has been executed and set key if not.
        
        This is an atomic operation using Redis SETNX (SET if Not eXists).
        
        Args:
            idempotency_key: Unique key for this operation
            operation_type: Type of operation (e.g., 'create_patient', 'assign_doctor')
            ttl: Time to live in seconds (default: 24 hours)
            
        Returns:
            True if operation should proceed (key was set)
            False if operation was already executed (key exists)
            
        Example:
            manager = IdempotencyManager(cache)
            if await manager.check_and_set("req-123", "create_patient"):
                # Execute operation
                patient = create_patient(...)
                await manager.store_result("req-123", patient.id)
            else:
                # Operation already executed
                result = await manager.get_result("req-123")
                return result
        """
        cache_key = CacheKeys.idempotency_key(operation_type, idempotency_key)
        ttl = ttl or self._default_ttl
        
        # Try to set key (returns True if key was set, False if already exists)
        was_set = await self.cache.set_if_not_exists(
            cache_key,
            "processing",
            ttl=ttl
        )
        
        return was_set
    
    async def store_result(
        self,
        idempotency_key: str,
        operation_type: str,
        result: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Store operation result for idempotency key.
        
        Args:
            idempotency_key: Unique key for this operation
            operation_type: Type of operation
            result: Operation result (will be JSON serialized)
            ttl: Time to live in seconds (default: 24 hours)
        """
        cache_key = CacheKeys.idempotency_key(operation_type, idempotency_key)
        ttl = ttl or self._default_ttl
        
        # Serialize result
        if isinstance(result, (UUID, str, int, float, bool)):
            result_data = {"value": str(result), "type": "scalar"}
        elif isinstance(result, dict):
            result_data = {"value": result, "type": "dict"}
        else:
            # For complex objects, store their ID or string representation
            result_data = {
                "value": str(getattr(result, "id", result)),
                "type": "object"
            }
        
        await self.cache.set_json(cache_key, result_data, ttl=ttl)
    
    async def get_result(
        self,
        idempotency_key: str,
        operation_type: str
    ) -> Optional[Any]:
        """
        Get stored result for idempotency key.
        
        Args:
            idempotency_key: Unique key for this operation
            operation_type: Type of operation
            
        Returns:
            Stored result if exists, None otherwise
        """
        cache_key = CacheKeys.idempotency_key(operation_type, idempotency_key)
        result_data = await self.cache.get_json(cache_key)
        
        if not result_data:
            return None
        
        # Deserialize result
        if result_data.get("type") == "scalar":
            return result_data.get("value")
        elif result_data.get("type") == "dict":
            return result_data.get("value")
        else:
            return result_data.get("value")
    
    async def exists(
        self,
        idempotency_key: str,
        operation_type: str
    ) -> bool:
        """
        Check if idempotency key exists.
        
        Args:
            idempotency_key: Unique key for this operation
            operation_type: Type of operation
            
        Returns:
            True if key exists, False otherwise
        """
        cache_key = CacheKeys.idempotency_key(operation_type, idempotency_key)
        return await self.cache.exists(cache_key)
    
    async def delete(
        self,
        idempotency_key: str,
        operation_type: str
    ) -> None:
        """
        Delete idempotency key (for cleanup or retry scenarios).
        
        Args:
            idempotency_key: Unique key for this operation
            operation_type: Type of operation
        """
        cache_key = CacheKeys.idempotency_key(operation_type, idempotency_key)
        await self.cache.delete(cache_key)
    
    @staticmethod
    def generate_key(
        user_id: UUID,
        operation_type: str,
        operation_data: Dict[str, Any]
    ) -> str:
        """
        Generate idempotency key from operation parameters.
        
        Creates a deterministic hash from user ID, operation type, and data.
        Same inputs always produce the same key.
        
        Args:
            user_id: User performing the operation
            operation_type: Type of operation
            operation_data: Operation parameters
            
        Returns:
            Idempotency key (hex string)
            
        Example:
            key = IdempotencyManager.generate_key(
                user_id=user.id,
                operation_type="create_patient",
                operation_data={"first_name": "John", "last_name": "Doe"}
            )
        """
        # Create deterministic string from inputs
        key_data = {
            "user_id": str(user_id),
            "operation_type": operation_type,
            "data": operation_data
        }
        
        # Sort keys for deterministic JSON
        key_string = json.dumps(key_data, sort_keys=True)
        
        # Generate SHA256 hash
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()
        
        return key_hash


async def with_idempotency(
    cache: RedisClient,
    idempotency_key: str,
    operation_type: str,
    operation_func,
    *args,
    **kwargs
) -> Any:
    """
    Execute operation with idempotency protection.
    
    This is a convenience function that wraps an operation with
    idempotency checking and result caching.
    
    Args:
        cache: Redis cache client
        idempotency_key: Unique key for this operation
        operation_type: Type of operation
        operation_func: Async function to execute
        *args: Positional arguments for operation_func
        **kwargs: Keyword arguments for operation_func
        
    Returns:
        Operation result (either from cache or fresh execution)
        
    Raises:
        ConflictError: If operation is already in progress
        
    Example:
        result = await with_idempotency(
            cache=cache,
            idempotency_key="req-123",
            operation_type="create_patient",
            operation_func=create_patient_internal,
            data=patient_data
        )
    """
    manager = IdempotencyManager(cache)
    
    # Check if operation already executed
    existing_result = await manager.get_result(idempotency_key, operation_type)
    if existing_result is not None:
        return existing_result
    
    # Try to acquire lock
    can_proceed = await manager.check_and_set(idempotency_key, operation_type)
    
    if not can_proceed:
        # Operation is in progress or completed
        # Wait a bit and check for result
        import asyncio
        await asyncio.sleep(0.1)
        
        result = await manager.get_result(idempotency_key, operation_type)
        if result is not None:
            return result
        
        # Still processing
        raise ConflictError(
            message="Operation already in progress",
            details={
                "idempotency_key": idempotency_key,
                "operation_type": operation_type
            }
        )
    
    try:
        # Execute operation
        result = await operation_func(*args, **kwargs)
        
        # Store result
        await manager.store_result(idempotency_key, operation_type, result)
        
        return result
        
    except Exception as e:
        # Clean up idempotency key on failure
        await manager.delete(idempotency_key, operation_type)
        raise
