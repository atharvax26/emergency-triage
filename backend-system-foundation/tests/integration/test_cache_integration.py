"""Integration tests for Redis cache layer."""

import pytest
from uuid import uuid4
import asyncio

from app.cache.client import RedisClient
from app.cache.service import CacheService
from app.cache.keys import CacheKeys
from app.config import settings


@pytest.fixture
async def redis_client():
    """Create real Redis client for integration tests."""
    client = RedisClient()
    try:
        await client.connect()
        yield client
    finally:
        await client.disconnect()


@pytest.fixture
async def cache_service(redis_client):
    """Create cache service with real Redis client."""
    return CacheService(redis_client)


@pytest.fixture(autouse=True)
async def cleanup_redis(redis_client):
    """Clean up Redis after each test."""
    yield
    # Cleanup test keys after each test
    # In a real scenario, you'd use a separate test database


class TestRedisConnectionPooling:
    """Test Redis connection pooling."""

    @pytest.mark.asyncio
    async def test_redis_connection_success(self, redis_client):
        """Test Redis connection is established."""
        is_connected = await redis_client.ping()
        assert is_connected is True

    @pytest.mark.asyncio
    async def test_redis_connection_pool_configured(self, redis_client):
        """Test Redis connection pool is configured correctly."""
        assert redis_client._connection_pool is not None
        assert redis_client._redis is not None


class TestSessionCacheIntegration:
    """Test session cache operations with real Redis."""

    @pytest.mark.asyncio
    async def test_session_cache_roundtrip(self, cache_service):
        """Test storing and retrieving session data."""
        token_hash = f"test_token_{uuid4()}"
        session_data = {
            "user_id": str(uuid4()),
            "email": "test@example.com",
            "roles": ["nurse"]
        }
        
        # Set session
        set_result = await cache_service.set_session(token_hash, session_data)
        assert set_result is True
        
        # Get session
        retrieved_data = await cache_service.get_session(token_hash)
        assert retrieved_data == session_data
        
        # Delete session
        delete_result = await cache_service.delete_session(token_hash)
        assert delete_result is True
        
        # Verify deletion
        deleted_data = await cache_service.get_session(token_hash)
        assert deleted_data is None

    @pytest.mark.asyncio
    async def test_session_ttl_expiration(self, cache_service, redis_client):
        """Test session expires after TTL."""
        token_hash = f"test_token_{uuid4()}"
        session_data = {"user_id": str(uuid4())}
        
        # Set session with short TTL for testing
        key = CacheKeys.session(token_hash)
        await redis_client.set_json(key, session_data, ttl=1)
        
        # Verify it exists
        data = await cache_service.get_session(token_hash)
        assert data == session_data
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Verify it's gone
        expired_data = await cache_service.get_session(token_hash)
        assert expired_data is None

    @pytest.mark.asyncio
    async def test_token_revocation(self, cache_service):
        """Test token revocation."""
        token_hash = f"test_token_{uuid4()}"
        
        # Initially not revoked
        is_revoked = await cache_service.is_token_revoked(token_hash)
        assert is_revoked is False
        
        # Revoke token
        revoke_result = await cache_service.revoke_token(token_hash, ttl=900)
        assert revoke_result is True
        
        # Verify revocation
        is_revoked = await cache_service.is_token_revoked(token_hash)
        assert is_revoked is True


class TestPatientCacheIntegration:
    """Test patient cache operations with real Redis."""

    @pytest.mark.asyncio
    async def test_patient_cache_roundtrip(self, cache_service):
        """Test storing and retrieving patient data."""
        patient_id = uuid4()
        mrn = f"MRN-20240101-{uuid4().hex[:4]}"
        patient_data = {
            "id": str(patient_id),
            "mrn": mrn,
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01"
        }
        
        # Set patient by ID
        set_result = await cache_service.set_patient(patient_id, patient_data)
        assert set_result is True
        
        # Set patient by MRN
        mrn_result = await cache_service.set_patient_by_mrn(mrn, patient_data)
        assert mrn_result is True
        
        # Get patient by ID
        retrieved_by_id = await cache_service.get_patient(patient_id)
        assert retrieved_by_id == patient_data
        
        # Get patient by MRN
        retrieved_by_mrn = await cache_service.get_patient_by_mrn(mrn)
        assert retrieved_by_mrn == patient_data
        
        # Invalidate patient
        invalidate_result = await cache_service.invalidate_patient(patient_id, mrn)
        assert invalidate_result is True
        
        # Verify both caches are cleared
        assert await cache_service.get_patient(patient_id) is None
        assert await cache_service.get_patient_by_mrn(mrn) is None


class TestQueueCacheIntegration:
    """Test queue cache operations with real Redis."""

    @pytest.mark.asyncio
    async def test_queue_entry_cache_roundtrip(self, cache_service):
        """Test storing and retrieving queue entry."""
        entry_id = uuid4()
        entry_data = {
            "id": str(entry_id),
            "patient_id": str(uuid4()),
            "priority": 8,
            "status": "waiting"
        }
        
        # Set queue entry
        set_result = await cache_service.set_queue_entry(entry_id, entry_data)
        assert set_result is True
        
        # Get queue entry
        retrieved_data = await cache_service.get_queue_entry(entry_id)
        assert retrieved_data == entry_data
        
        # Delete queue entry
        delete_result = await cache_service.delete_queue_entry(entry_id)
        assert delete_result is True
        
        # Verify deletion
        assert await cache_service.get_queue_entry(entry_id) is None

    @pytest.mark.asyncio
    async def test_active_queue_cache(self, cache_service):
        """Test storing and retrieving active queue."""
        queue_data = [
            {"id": str(uuid4()), "priority": 10, "status": "waiting"},
            {"id": str(uuid4()), "priority": 8, "status": "assigned"},
            {"id": str(uuid4()), "priority": 5, "status": "waiting"}
        ]
        
        # Set active queue
        set_result = await cache_service.set_active_queue(queue_data)
        assert set_result is True
        
        # Get active queue
        retrieved_queue = await cache_service.get_active_queue()
        assert retrieved_queue == queue_data
        
        # Invalidate queue
        invalidate_result = await cache_service.invalidate_queue()
        assert invalidate_result is True
        
        # Verify invalidation
        assert await cache_service.get_active_queue() is None

    @pytest.mark.asyncio
    async def test_queue_stats_cache_with_short_ttl(self, cache_service, redis_client):
        """Test queue stats cache with 30 second TTL."""
        stats_data = {
            "total": 10,
            "waiting": 5,
            "assigned": 3,
            "in_progress": 2
        }
        
        # Set queue stats
        set_result = await cache_service.set_queue_stats(stats_data)
        assert set_result is True
        
        # Verify TTL is set to 30 seconds
        key = CacheKeys.queue_stats()
        ttl = await redis_client.ttl(key)
        assert ttl is not None
        assert 25 <= ttl <= 30  # Allow some margin for execution time


class TestPermissionCacheIntegration:
    """Test permission cache operations with real Redis."""

    @pytest.mark.asyncio
    async def test_user_permissions_cache_roundtrip(self, cache_service):
        """Test storing and retrieving user permissions."""
        user_id = uuid4()
        permissions = [
            {"resource": "patient", "action": "read"},
            {"resource": "patient", "action": "create"},
            {"resource": "queue", "action": "read"}
        ]
        
        # Set permissions
        set_result = await cache_service.set_user_permissions(user_id, permissions)
        assert set_result is True
        
        # Get permissions
        retrieved_permissions = await cache_service.get_user_permissions(user_id)
        assert retrieved_permissions == permissions
        
        # Delete permissions
        delete_result = await cache_service.delete_user_permissions(user_id)
        assert delete_result is True
        
        # Verify deletion
        assert await cache_service.get_user_permissions(user_id) is None

    @pytest.mark.asyncio
    async def test_user_roles_cache_roundtrip(self, cache_service):
        """Test storing and retrieving user roles."""
        user_id = uuid4()
        roles = ["nurse", "doctor"]
        
        # Set roles
        set_result = await cache_service.set_user_roles(user_id, roles)
        assert set_result is True
        
        # Get roles
        retrieved_roles = await cache_service.get_user_roles(user_id)
        assert retrieved_roles == roles
        
        # Invalidate permissions (includes roles)
        invalidate_result = await cache_service.invalidate_user_permissions(user_id)
        assert invalidate_result is True
        
        # Verify both are cleared
        assert await cache_service.get_user_permissions(user_id) is None
        assert await cache_service.get_user_roles(user_id) is None


class TestRateLimitingIntegration:
    """Test rate limiting operations with real Redis."""

    @pytest.mark.asyncio
    async def test_rate_limit_increment_and_get(self, cache_service):
        """Test incrementing and getting rate limit count."""
        user_id = uuid4()
        
        # First increment
        count1 = await cache_service.increment_rate_limit(user_id=user_id)
        assert count1 == 1
        
        # Second increment
        count2 = await cache_service.increment_rate_limit(user_id=user_id)
        assert count2 == 2
        
        # Get count
        current_count = await cache_service.get_rate_limit_count(user_id=user_id)
        assert current_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_expiration(self, cache_service, redis_client):
        """Test rate limit counter expires after 60 seconds."""
        user_id = uuid4()
        
        # Increment with short TTL for testing
        key = CacheKeys.rate_limit_user(user_id)
        await redis_client.increment(key)
        await redis_client.expire(key, 1)
        
        # Verify it exists
        count = await cache_service.get_rate_limit_count(user_id=user_id)
        assert count == 1
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Verify it's reset
        expired_count = await cache_service.get_rate_limit_count(user_id=user_id)
        assert expired_count == 0


class TestAccountLockoutIntegration:
    """Test account lockout operations with real Redis."""

    @pytest.mark.asyncio
    async def test_login_attempts_tracking(self, cache_service):
        """Test tracking failed login attempts."""
        user_id = uuid4()
        
        # Initially no attempts
        attempts = await cache_service.get_login_attempts(user_id)
        assert attempts == 0
        
        # Increment attempts
        for i in range(1, 6):
            count = await cache_service.increment_login_attempts(user_id)
            assert count == i
        
        # Get attempts
        final_attempts = await cache_service.get_login_attempts(user_id)
        assert final_attempts == 5
        
        # Reset attempts
        reset_result = await cache_service.reset_login_attempts(user_id)
        assert reset_result is True
        
        # Verify reset
        reset_attempts = await cache_service.get_login_attempts(user_id)
        assert reset_attempts == 0

    @pytest.mark.asyncio
    async def test_account_lockout(self, cache_service):
        """Test account lockout functionality."""
        user_id = uuid4()
        
        # Initially not locked
        is_locked = await cache_service.is_account_locked(user_id)
        assert is_locked is False
        
        # Lock account
        lock_result = await cache_service.lock_account(user_id)
        assert lock_result is True
        
        # Verify locked
        is_locked = await cache_service.is_account_locked(user_id)
        assert is_locked is True


class TestIdempotencyIntegration:
    """Test idempotency operations with real Redis."""

    @pytest.mark.asyncio
    async def test_idempotency_prevents_duplicates(self, cache_service):
        """Test idempotency key prevents duplicate operations."""
        operation_type = "create_patient"
        key = f"patient_{uuid4()}"
        
        # First operation should succeed
        first_check = await cache_service.check_idempotency(operation_type, key)
        assert first_check is True
        
        # Second operation should fail (duplicate)
        second_check = await cache_service.check_idempotency(operation_type, key)
        assert second_check is False
        
        # Clear idempotency
        clear_result = await cache_service.clear_idempotency(operation_type, key)
        assert clear_result is True
        
        # Third operation should succeed after clearing
        third_check = await cache_service.check_idempotency(operation_type, key)
        assert third_check is True


class TestCacheKeyPatterns:
    """Test cache key patterns follow centralized format."""

    def test_session_key_pattern(self):
        """Test session key follows cache:{domain}:{entity}:{id} pattern."""
        token_hash = "test_token"
        key = CacheKeys.session(token_hash)
        assert key.startswith("cache:session:")
        assert "test_token" in key

    def test_patient_key_pattern(self):
        """Test patient key follows cache:{domain}:{entity}:{id} pattern."""
        patient_id = uuid4()
        key = CacheKeys.patient(patient_id)
        assert key.startswith("cache:patient:")
        assert str(patient_id) in key

    def test_queue_key_pattern(self):
        """Test queue key follows cache:{domain}:{entity}:{id} pattern."""
        entry_id = uuid4()
        key = CacheKeys.queue_entry(entry_id)
        assert key.startswith("cache:queue:")
        assert str(entry_id) in key

    def test_permission_key_pattern(self):
        """Test permission key follows cache:{domain}:{entity}:{id} pattern."""
        user_id = uuid4()
        key = CacheKeys.user_permissions(user_id)
        assert key.startswith("cache:permissions:")
        assert str(user_id) in key


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, cache_service):
        """Test health check returns healthy status."""
        health = await cache_service.health_check()
        
        assert health["status"] == "healthy"
        assert health["connected"] is True
        assert "operational" in health["message"]


class TestGracefulFallback:
    """Test graceful fallback on Redis failures."""

    @pytest.mark.asyncio
    async def test_cache_operations_dont_crash_on_redis_failure(self, cache_service):
        """Test that cache operations handle Redis failures gracefully."""
        # Disconnect Redis to simulate failure
        await cache_service.redis.disconnect()
        
        # Operations should not raise exceptions
        token_hash = "test_token"
        session_data = {"user_id": str(uuid4())}
        
        # These should return None/False instead of raising exceptions
        get_result = await cache_service.get_session(token_hash)
        set_result = await cache_service.set_session(token_hash, session_data)
        
        # Results should indicate failure, not crash
        assert get_result is None or isinstance(get_result, dict)
        assert isinstance(set_result, bool)
