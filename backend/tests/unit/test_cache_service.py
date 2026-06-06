"""Unit tests for cache service."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.cache.service import CacheService
from app.cache.keys import CacheKeys
from app.config import settings


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client."""
    client = MagicMock()
    client.get_json = AsyncMock(return_value=None)
    client.set_json = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=True)
    client.exists = AsyncMock(return_value=False)
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.increment = AsyncMock(return_value=1)
    client.expire = AsyncMock(return_value=True)
    client.ttl = AsyncMock(return_value=None)
    client.ping = AsyncMock(return_value=True)
    client.set_if_not_exists = AsyncMock(return_value=True)
    return client


@pytest.fixture
def cache_service(mock_redis_client):
    """Create cache service with mock Redis client."""
    return CacheService(mock_redis_client)


class TestSessionCacheOperations:
    """Test session cache operations."""

    @pytest.mark.asyncio
    async def test_get_session_success(self, cache_service, mock_redis_client):
        """Test getting session from cache."""
        token_hash = "test_token_hash"
        session_data = {"user_id": str(uuid4()), "email": "test@example.com"}
        
        mock_redis_client.get_json.return_value = session_data
        
        result = await cache_service.get_session(token_hash)
        
        assert result == session_data
        mock_redis_client.get_json.assert_called_once_with(
            CacheKeys.session(token_hash)
        )

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, cache_service, mock_redis_client):
        """Test getting non-existent session."""
        token_hash = "nonexistent_token"
        mock_redis_client.get_json.return_value = None
        
        result = await cache_service.get_session(token_hash)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_set_session_success(self, cache_service, mock_redis_client):
        """Test setting session in cache."""
        token_hash = "test_token_hash"
        session_data = {"user_id": str(uuid4()), "email": "test@example.com"}
        
        result = await cache_service.set_session(token_hash, session_data)
        
        assert result is True
        mock_redis_client.set_json.assert_called_once_with(
            CacheKeys.session(token_hash),
            session_data,
            settings.CACHE_TTL_SESSION
        )

    @pytest.mark.asyncio
    async def test_delete_session_success(self, cache_service, mock_redis_client):
        """Test deleting session from cache."""
        token_hash = "test_token_hash"
        
        result = await cache_service.delete_session(token_hash)
        
        assert result is True
        mock_redis_client.delete.assert_called_once_with(
            CacheKeys.session(token_hash)
        )

    @pytest.mark.asyncio
    async def test_is_token_revoked_true(self, cache_service, mock_redis_client):
        """Test checking if token is revoked."""
        token_hash = "revoked_token"
        mock_redis_client.exists.return_value = True
        
        result = await cache_service.is_token_revoked(token_hash)
        
        assert result is True
        mock_redis_client.exists.assert_called_once_with(
            CacheKeys.revoked_token(token_hash)
        )

    @pytest.mark.asyncio
    async def test_revoke_token_success(self, cache_service, mock_redis_client):
        """Test revoking a token."""
        token_hash = "test_token"
        ttl = 900
        
        result = await cache_service.revoke_token(token_hash, ttl)
        
        assert result is True
        mock_redis_client.set.assert_called_once_with(
            CacheKeys.revoked_token(token_hash),
            "revoked",
            ttl
        )


class TestPatientCacheOperations:
    """Test patient cache operations."""

    @pytest.mark.asyncio
    async def test_get_patient_success(self, cache_service, mock_redis_client):
        """Test getting patient from cache."""
        patient_id = uuid4()
        patient_data = {
            "id": str(patient_id),
            "mrn": "MRN-20240101-0001",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        mock_redis_client.get_json.return_value = patient_data
        
        result = await cache_service.get_patient(patient_id)
        
        assert result == patient_data
        mock_redis_client.get_json.assert_called_once_with(
            CacheKeys.patient(patient_id)
        )

    @pytest.mark.asyncio
    async def test_set_patient_success(self, cache_service, mock_redis_client):
        """Test setting patient in cache."""
        patient_id = uuid4()
        patient_data = {
            "id": str(patient_id),
            "mrn": "MRN-20240101-0001",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        result = await cache_service.set_patient(patient_id, patient_data)
        
        assert result is True
        mock_redis_client.set_json.assert_called_once_with(
            CacheKeys.patient(patient_id),
            patient_data,
            settings.CACHE_TTL_PATIENT
        )

    @pytest.mark.asyncio
    async def test_get_patient_by_mrn_success(self, cache_service, mock_redis_client):
        """Test getting patient by MRN from cache."""
        mrn = "MRN-20240101-0001"
        patient_data = {
            "id": str(uuid4()),
            "mrn": mrn,
            "first_name": "John",
            "last_name": "Doe"
        }
        
        mock_redis_client.get_json.return_value = patient_data
        
        result = await cache_service.get_patient_by_mrn(mrn)
        
        assert result == patient_data
        mock_redis_client.get_json.assert_called_once_with(
            CacheKeys.patient_by_mrn(mrn)
        )

    @pytest.mark.asyncio
    async def test_invalidate_patient_with_mrn(self, cache_service, mock_redis_client):
        """Test invalidating patient cache with MRN."""
        patient_id = uuid4()
        mrn = "MRN-20240101-0001"
        
        result = await cache_service.invalidate_patient(patient_id, mrn)
        
        assert result is True
        assert mock_redis_client.delete.call_count == 2


class TestQueueCacheOperations:
    """Test queue cache operations."""

    @pytest.mark.asyncio
    async def test_get_queue_entry_success(self, cache_service, mock_redis_client):
        """Test getting queue entry from cache."""
        entry_id = uuid4()
        entry_data = {
            "id": str(entry_id),
            "patient_id": str(uuid4()),
            "priority": 5,
            "status": "waiting"
        }
        
        mock_redis_client.get_json.return_value = entry_data
        
        result = await cache_service.get_queue_entry(entry_id)
        
        assert result == entry_data
        mock_redis_client.get_json.assert_called_once_with(
            CacheKeys.queue_entry(entry_id)
        )

    @pytest.mark.asyncio
    async def test_set_queue_entry_success(self, cache_service, mock_redis_client):
        """Test setting queue entry in cache."""
        entry_id = uuid4()
        entry_data = {
            "id": str(entry_id),
            "patient_id": str(uuid4()),
            "priority": 5,
            "status": "waiting"
        }
        
        result = await cache_service.set_queue_entry(entry_id, entry_data)
        
        assert result is True
        mock_redis_client.set_json.assert_called_once_with(
            CacheKeys.queue_entry(entry_id),
            entry_data,
            settings.CACHE_TTL_QUEUE
        )

    @pytest.mark.asyncio
    async def test_get_active_queue_success(self, cache_service, mock_redis_client):
        """Test getting active queue from cache."""
        queue_data = [
            {"id": str(uuid4()), "priority": 10},
            {"id": str(uuid4()), "priority": 8}
        ]
        
        mock_redis_client.get_json.return_value = queue_data
        
        result = await cache_service.get_active_queue()
        
        assert result == queue_data
        mock_redis_client.get_json.assert_called_once_with(
            CacheKeys.active_queue()
        )

    @pytest.mark.asyncio
    async def test_set_queue_stats_with_short_ttl(self, cache_service, mock_redis_client):
        """Test setting queue stats with 30 second TTL."""
        stats_data = {
            "total": 10,
            "waiting": 5,
            "assigned": 3,
            "in_progress": 2
        }
        
        result = await cache_service.set_queue_stats(stats_data)
        
        assert result is True
        mock_redis_client.set_json.assert_called_once_with(
            CacheKeys.queue_stats(),
            stats_data,
            30  # 30 seconds as per requirements
        )

    @pytest.mark.asyncio
    async def test_invalidate_queue_success(self, cache_service, mock_redis_client):
        """Test invalidating queue cache."""
        result = await cache_service.invalidate_queue()
        
        assert result is True
        assert mock_redis_client.delete.call_count == 2


class TestPermissionCacheOperations:
    """Test permission cache operations."""

    @pytest.mark.asyncio
    async def test_get_user_permissions_success(self, cache_service, mock_redis_client):
        """Test getting user permissions from cache."""
        user_id = uuid4()
        permissions = [
            {"resource": "patient", "action": "read"},
            {"resource": "patient", "action": "create"}
        ]
        
        mock_redis_client.get_json.return_value = permissions
        
        result = await cache_service.get_user_permissions(user_id)
        
        assert result == permissions
        mock_redis_client.get_json.assert_called_once_with(
            CacheKeys.user_permissions(user_id)
        )

    @pytest.mark.asyncio
    async def test_set_user_permissions_success(self, cache_service, mock_redis_client):
        """Test setting user permissions in cache."""
        user_id = uuid4()
        permissions = [
            {"resource": "patient", "action": "read"},
            {"resource": "patient", "action": "create"}
        ]
        
        result = await cache_service.set_user_permissions(user_id, permissions)
        
        assert result is True
        mock_redis_client.set_json.assert_called_once_with(
            CacheKeys.user_permissions(user_id),
            permissions,
            settings.CACHE_TTL_PERMISSION
        )

    @pytest.mark.asyncio
    async def test_get_user_roles_success(self, cache_service, mock_redis_client):
        """Test getting user roles from cache."""
        user_id = uuid4()
        roles = ["nurse", "doctor"]
        
        mock_redis_client.get_json.return_value = roles
        
        result = await cache_service.get_user_roles(user_id)
        
        assert result == roles
        mock_redis_client.get_json.assert_called_once_with(
            CacheKeys.user_roles(user_id)
        )

    @pytest.mark.asyncio
    async def test_invalidate_user_permissions_success(self, cache_service, mock_redis_client):
        """Test invalidating user permissions cache."""
        user_id = uuid4()
        
        result = await cache_service.invalidate_user_permissions(user_id)
        
        assert result is True
        assert mock_redis_client.delete.call_count == 2


class TestRateLimitingOperations:
    """Test rate limiting operations."""

    @pytest.mark.asyncio
    async def test_increment_rate_limit_user_first_request(self, cache_service, mock_redis_client):
        """Test incrementing rate limit for first request."""
        user_id = uuid4()
        mock_redis_client.increment.return_value = 1
        
        result = await cache_service.increment_rate_limit(user_id=user_id)
        
        assert result == 1
        mock_redis_client.increment.assert_called_once()
        mock_redis_client.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_rate_limit_user_subsequent_request(self, cache_service, mock_redis_client):
        """Test incrementing rate limit for subsequent request."""
        user_id = uuid4()
        mock_redis_client.increment.return_value = 5
        
        result = await cache_service.increment_rate_limit(user_id=user_id)
        
        assert result == 5
        mock_redis_client.increment.assert_called_once()
        # expire should not be called for count > 1
        mock_redis_client.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_increment_rate_limit_ip(self, cache_service, mock_redis_client):
        """Test incrementing rate limit for IP address."""
        ip_address = "192.168.1.1"
        mock_redis_client.increment.return_value = 1
        
        result = await cache_service.increment_rate_limit(ip_address=ip_address)
        
        assert result == 1
        mock_redis_client.increment.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_rate_limit_count_user(self, cache_service, mock_redis_client):
        """Test getting rate limit count for user."""
        user_id = uuid4()
        mock_redis_client.get.return_value = "42"
        
        result = await cache_service.get_rate_limit_count(user_id=user_id)
        
        assert result == 42


class TestAccountLockoutOperations:
    """Test account lockout operations."""

    @pytest.mark.asyncio
    async def test_increment_login_attempts_first_attempt(self, cache_service, mock_redis_client):
        """Test incrementing login attempts for first failure."""
        user_id = uuid4()
        mock_redis_client.increment.return_value = 1
        
        result = await cache_service.increment_login_attempts(user_id)
        
        assert result == 1
        mock_redis_client.increment.assert_called_once()
        mock_redis_client.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_login_attempts(self, cache_service, mock_redis_client):
        """Test getting login attempts count."""
        user_id = uuid4()
        mock_redis_client.get.return_value = "5"
        
        result = await cache_service.get_login_attempts(user_id)
        
        assert result == 5

    @pytest.mark.asyncio
    async def test_reset_login_attempts(self, cache_service, mock_redis_client):
        """Test resetting login attempts."""
        user_id = uuid4()
        
        result = await cache_service.reset_login_attempts(user_id)
        
        assert result is True
        mock_redis_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_lock_account(self, cache_service, mock_redis_client):
        """Test locking user account."""
        user_id = uuid4()
        
        result = await cache_service.lock_account(user_id)
        
        assert result is True
        mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_account_locked_true(self, cache_service, mock_redis_client):
        """Test checking if account is locked."""
        user_id = uuid4()
        mock_redis_client.exists.return_value = True
        
        result = await cache_service.is_account_locked(user_id)
        
        assert result is True


class TestIdempotencyOperations:
    """Test idempotency operations."""

    @pytest.mark.asyncio
    async def test_check_idempotency_first_operation(self, cache_service, mock_redis_client):
        """Test idempotency check for first operation."""
        operation_type = "create_patient"
        key = "patient_123"
        mock_redis_client.set_if_not_exists.return_value = True
        
        result = await cache_service.check_idempotency(operation_type, key)
        
        assert result is True
        mock_redis_client.set_if_not_exists.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_idempotency_duplicate_operation(self, cache_service, mock_redis_client):
        """Test idempotency check for duplicate operation."""
        operation_type = "create_patient"
        key = "patient_123"
        mock_redis_client.set_if_not_exists.return_value = False
        
        result = await cache_service.check_idempotency(operation_type, key)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_idempotency(self, cache_service, mock_redis_client):
        """Test clearing idempotency key."""
        operation_type = "create_patient"
        key = "patient_123"
        
        result = await cache_service.clear_idempotency(operation_type, key)
        
        assert result is True
        mock_redis_client.delete.assert_called_once()


class TestHealthCheckOperations:
    """Test health check operations."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, cache_service, mock_redis_client):
        """Test health check when Redis is healthy."""
        mock_redis_client.ping.return_value = True
        
        result = await cache_service.health_check()
        
        assert result["status"] == "healthy"
        assert result["connected"] is True
        assert "operational" in result["message"]

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, cache_service, mock_redis_client):
        """Test health check when Redis is unhealthy."""
        mock_redis_client.ping.return_value = False
        
        result = await cache_service.health_check()
        
        assert result["status"] == "unhealthy"
        assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_health_check_exception(self, cache_service, mock_redis_client):
        """Test health check when Redis raises exception."""
        mock_redis_client.ping.side_effect = Exception("Connection failed")
        
        result = await cache_service.health_check()
        
        assert result["status"] == "unhealthy"
        assert result["connected"] is False
        assert "failed" in result["message"]


class TestUtilityOperations:
    """Test utility operations."""

    @pytest.mark.asyncio
    async def test_get_ttl_success(self, cache_service, mock_redis_client):
        """Test getting TTL for a key."""
        key = "test_key"
        mock_redis_client.ttl.return_value = 300
        
        result = await cache_service.get_ttl(key)
        
        assert result == 300

    @pytest.mark.asyncio
    async def test_exists_true(self, cache_service, mock_redis_client):
        """Test checking if key exists."""
        key = "test_key"
        mock_redis_client.exists.return_value = True
        
        result = await cache_service.exists(key)
        
        assert result is True


class TestTTLConfiguration:
    """Test TTL configuration."""

    def test_ttl_config_values(self, cache_service):
        """Test that TTL values match requirements."""
        # Session: 15 minutes = 900 seconds
        assert cache_service.ttl_config["session"] == settings.CACHE_TTL_SESSION
        
        # Patient: 5 minutes = 300 seconds
        assert cache_service.ttl_config["patient"] == settings.CACHE_TTL_PATIENT
        
        # Queue: 1 minute = 60 seconds
        assert cache_service.ttl_config["queue"] == settings.CACHE_TTL_QUEUE
        
        # Permission: 10 minutes = 600 seconds
        assert cache_service.ttl_config["permission"] == settings.CACHE_TTL_PERMISSION


class TestGracefulDegradation:
    """Test graceful degradation on Redis failures."""

    @pytest.mark.asyncio
    async def test_get_session_redis_failure(self, cache_service, mock_redis_client):
        """Test that get_session returns None on Redis failure."""
        token_hash = "test_token"
        # Mock returns None to simulate graceful degradation
        mock_redis_client.get_json.return_value = None
        
        # Should not raise exception, should return None
        result = await cache_service.get_session(token_hash)
        
        # The actual implementation in RedisClient handles this gracefully
        # by catching RedisError and returning None
        assert result is None

    @pytest.mark.asyncio
    async def test_set_session_redis_failure(self, cache_service, mock_redis_client):
        """Test that set_session returns False on Redis failure."""
        token_hash = "test_token"
        session_data = {"user_id": str(uuid4())}
        # Mock returns False to simulate graceful degradation
        mock_redis_client.set_json.return_value = False
        
        # Should not raise exception, should return False
        result = await cache_service.set_session(token_hash, session_data)
        
        # The actual implementation in RedisClient handles this gracefully
        # by catching RedisError and returning False
        assert result is False
