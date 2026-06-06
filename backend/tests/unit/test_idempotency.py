"""Unit tests for idempotency protection.

Tests idempotency key management and duplicate operation prevention.

Requirements: 19.4, 19.5
"""

import pytest
from uuid import uuid4

from app.core.idempotency import IdempotencyManager, with_idempotency
from app.utils.exceptions import ConflictError


@pytest.mark.asyncio
class TestIdempotencyManager:
    """Test IdempotencyManager implementation."""
    
    async def test_check_and_set_first_time(self, redis_client):
        """Test that first check_and_set returns True."""
        manager = IdempotencyManager(redis_client)
        
        key = f"test-{uuid4()}"
        can_proceed = await manager.check_and_set(key, "test_operation")
        
        assert can_proceed is True
    
    async def test_check_and_set_duplicate(self, redis_client):
        """Test that duplicate check_and_set returns False."""
        manager = IdempotencyManager(redis_client)
        
        key = f"test-{uuid4()}"
        
        # First call
        can_proceed1 = await manager.check_and_set(key, "test_operation")
        assert can_proceed1 is True
        
        # Duplicate call
        can_proceed2 = await manager.check_and_set(key, "test_operation")
        assert can_proceed2 is False
    
    async def test_store_and_get_result_scalar(self, redis_client):
        """Test storing and retrieving scalar result."""
        manager = IdempotencyManager(redis_client)
        
        key = f"test-{uuid4()}"
        await manager.check_and_set(key, "test_operation")
        
        # Store result
        result_value = "test-result-123"
        await manager.store_result(key, "test_operation", result_value)
        
        # Retrieve result
        retrieved = await manager.get_result(key, "test_operation")
        assert retrieved == result_value
    
    async def test_store_and_get_result_dict(self, redis_client):
        """Test storing and retrieving dict result."""
        manager = IdempotencyManager(redis_client)
        
        key = f"test-{uuid4()}"
        await manager.check_and_set(key, "test_operation")
        
        # Store result
        result_value = {"patient_id": "123", "queue_id": "456"}
        await manager.store_result(key, "test_operation", result_value)
        
        # Retrieve result
        retrieved = await manager.get_result(key, "test_operation")
        assert retrieved == result_value
    
    async def test_store_and_get_result_uuid(self, redis_client):
        """Test storing and retrieving UUID result."""
        manager = IdempotencyManager(redis_client)
        
        key = f"test-{uuid4()}"
        await manager.check_and_set(key, "test_operation")
        
        # Store result
        result_value = uuid4()
        await manager.store_result(key, "test_operation", result_value)
        
        # Retrieve result
        retrieved = await manager.get_result(key, "test_operation")
        assert retrieved == str(result_value)
    
    async def test_exists(self, redis_client):
        """Test exists method."""
        manager = IdempotencyManager(redis_client)
        
        key = f"test-{uuid4()}"
        
        # Should not exist initially
        exists = await manager.exists(key, "test_operation")
        assert exists is False
        
        # Set key
        await manager.check_and_set(key, "test_operation")
        
        # Should exist now
        exists = await manager.exists(key, "test_operation")
        assert exists is True
    
    async def test_delete(self, redis_client):
        """Test delete method."""
        manager = IdempotencyManager(redis_client)
        
        key = f"test-{uuid4()}"
        
        # Set key
        await manager.check_and_set(key, "test_operation")
        assert await manager.exists(key, "test_operation") is True
        
        # Delete key
        await manager.delete(key, "test_operation")
        
        # Should not exist
        assert await manager.exists(key, "test_operation") is False
    
    async def test_generate_key_deterministic(self):
        """Test that generate_key produces deterministic results."""
        user_id = uuid4()
        operation_type = "create_patient"
        operation_data = {"first_name": "John", "last_name": "Doe"}
        
        # Generate key twice
        key1 = IdempotencyManager.generate_key(
            user_id, operation_type, operation_data
        )
        key2 = IdempotencyManager.generate_key(
            user_id, operation_type, operation_data
        )
        
        # Should be identical
        assert key1 == key2
    
    async def test_generate_key_different_data(self):
        """Test that different data produces different keys."""
        user_id = uuid4()
        operation_type = "create_patient"
        
        key1 = IdempotencyManager.generate_key(
            user_id, operation_type, {"first_name": "John"}
        )
        key2 = IdempotencyManager.generate_key(
            user_id, operation_type, {"first_name": "Jane"}
        )
        
        # Should be different
        assert key1 != key2
    
    async def test_ttl_expiration(self, redis_client):
        """Test that keys expire after TTL."""
        manager = IdempotencyManager(redis_client)
        
        key = f"test-{uuid4()}"
        
        # Set key with 1 second TTL
        await manager.check_and_set(key, "test_operation", ttl=1)
        
        # Should exist immediately
        assert await manager.exists(key, "test_operation") is True
        
        # Wait for expiration
        import asyncio
        await asyncio.sleep(2)
        
        # Should not exist after TTL
        assert await manager.exists(key, "test_operation") is False
    
    async def test_with_idempotency_first_execution(self, redis_client):
        """Test with_idempotency executes operation first time."""
        execution_count = 0
        
        async def test_operation():
            nonlocal execution_count
            execution_count += 1
            return "result"
        
        key = f"test-{uuid4()}"
        result = await with_idempotency(
            redis_client,
            key,
            "test_operation",
            test_operation
        )
        
        assert result == "result"
        assert execution_count == 1
    
    async def test_with_idempotency_duplicate_execution(self, redis_client):
        """Test with_idempotency returns cached result on duplicate."""
        execution_count = 0
        
        async def test_operation():
            nonlocal execution_count
            execution_count += 1
            return "result"
        
        key = f"test-{uuid4()}"
        
        # First execution
        result1 = await with_idempotency(
            redis_client,
            key,
            "test_operation",
            test_operation
        )
        
        # Second execution (should use cache)
        result2 = await with_idempotency(
            redis_client,
            key,
            "test_operation",
            test_operation
        )
        
        assert result1 == "result"
        assert result2 == "result"
        assert execution_count == 1  # Only executed once
    
    async def test_with_idempotency_cleanup_on_failure(self, redis_client):
        """Test that idempotency key is cleaned up on failure."""
        async def failing_operation():
            raise ValueError("Test failure")
        
        key = f"test-{uuid4()}"
        manager = IdempotencyManager(redis_client)
        
        # Execute failing operation
        try:
            await with_idempotency(
                redis_client,
                key,
                "test_operation",
                failing_operation
            )
        except ValueError:
            pass
        
        # Key should be cleaned up
        exists = await manager.exists(key, "test_operation")
        assert exists is False
    
    async def test_different_operation_types(self, redis_client):
        """Test that different operation types use different keys."""
        manager = IdempotencyManager(redis_client)
        
        key = f"test-{uuid4()}"
        
        # Set for operation type 1
        can_proceed1 = await manager.check_and_set(key, "operation_type_1")
        assert can_proceed1 is True
        
        # Should be able to set for operation type 2 (different namespace)
        can_proceed2 = await manager.check_and_set(key, "operation_type_2")
        assert can_proceed2 is True
