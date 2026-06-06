"""Centralized cache service with TTL management and invalidation logic."""

import json
from typing import Any, Optional, Dict, List
from uuid import UUID
from datetime import datetime

from app.cache.client import RedisClient
from app.cache.keys import CacheKeys
from app.config import settings


class CacheService:
    """
    Centralized cache service for managing Redis operations.
    
    Implements:
    - Consistent cache key patterns (cache:{domain}:{entity}:{id})
    - TTL management per domain
    - Cache invalidation rules
    - Graceful fallback on Redis failures
    """

    def __init__(self, redis_client: RedisClient):
        """
        Initialize cache service.
        
        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        
        # TTL configuration per domain (in seconds)
        self.ttl_config = {
            "session": settings.CACHE_TTL_SESSION,  # 15 minutes
            "patient": settings.CACHE_TTL_PATIENT,  # 5 minutes
            "queue": settings.CACHE_TTL_QUEUE,      # 1 minute
            "permission": settings.CACHE_TTL_PERMISSION,  # 10 minutes
        }

    # ==================== Session Cache Operations ====================

    async def get_session(self, token_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get session data from cache.
        
        Args:
            token_hash: Hashed token identifier
            
        Returns:
            Session data if exists, None otherwise
        """
        key = CacheKeys.session(token_hash)
        return await self.redis.get_json(key)

    async def set_session(
        self,
        token_hash: str,
        session_data: Dict[str, Any]
    ) -> bool:
        """
        Store session data in cache with TTL.
        
        Args:
            token_hash: Hashed token identifier
            session_data: Session data to cache
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.session(token_hash)
        ttl = self.ttl_config["session"]
        return await self.redis.set_json(key, session_data, ttl)

    async def delete_session(self, token_hash: str) -> bool:
        """
        Delete session from cache.
        
        Args:
            token_hash: Hashed token identifier
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.session(token_hash)
        return await self.redis.delete(key)

    async def is_token_revoked(self, token_hash: str) -> bool:
        """
        Check if token is revoked.
        
        Args:
            token_hash: Hashed token identifier
            
        Returns:
            True if revoked, False otherwise
        """
        key = CacheKeys.revoked_token(token_hash)
        return await self.redis.exists(key)

    async def revoke_token(self, token_hash: str, ttl: int) -> bool:
        """
        Add token to revocation list.
        
        Args:
            token_hash: Hashed token identifier
            ttl: Time until token would naturally expire
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.revoked_token(token_hash)
        # Store with TTL matching token expiration
        return await self.redis.set(key, "revoked", ttl)

    # ==================== Patient Cache Operations ====================

    async def get_patient(self, patient_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get patient data from cache.
        
        Args:
            patient_id: Patient UUID
            
        Returns:
            Patient data if exists, None otherwise
        """
        key = CacheKeys.patient(patient_id)
        return await self.redis.get_json(key)

    async def set_patient(
        self,
        patient_id: UUID,
        patient_data: Dict[str, Any]
    ) -> bool:
        """
        Store patient data in cache with TTL.
        
        Args:
            patient_id: Patient UUID
            patient_data: Patient data to cache
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.patient(patient_id)
        ttl = self.ttl_config["patient"]
        return await self.redis.set_json(key, patient_data, ttl)

    async def delete_patient(self, patient_id: UUID) -> bool:
        """
        Delete patient from cache (invalidation).
        
        Args:
            patient_id: Patient UUID
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.patient(patient_id)
        return await self.redis.delete(key)

    async def get_patient_by_mrn(self, mrn: str) -> Optional[Dict[str, Any]]:
        """
        Get patient data by MRN from cache.
        
        Args:
            mrn: Medical Record Number
            
        Returns:
            Patient data if exists, None otherwise
        """
        key = CacheKeys.patient_by_mrn(mrn)
        return await self.redis.get_json(key)

    async def set_patient_by_mrn(
        self,
        mrn: str,
        patient_data: Dict[str, Any]
    ) -> bool:
        """
        Store patient data by MRN in cache with TTL.
        
        Args:
            mrn: Medical Record Number
            patient_data: Patient data to cache
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.patient_by_mrn(mrn)
        ttl = self.ttl_config["patient"]
        return await self.redis.set_json(key, patient_data, ttl)

    async def invalidate_patient(self, patient_id: UUID, mrn: Optional[str] = None) -> bool:
        """
        Invalidate all patient cache entries.
        
        This is called when patient data is updated to ensure cache consistency.
        
        Args:
            patient_id: Patient UUID
            mrn: Optional MRN to also invalidate MRN-based cache
            
        Returns:
            True if all invalidations successful, False otherwise
        """
        success = await self.delete_patient(patient_id)
        
        if mrn:
            mrn_success = await self.redis.delete(CacheKeys.patient_by_mrn(mrn))
            success = success and mrn_success
        
        return success

    # ==================== Queue Cache Operations ====================

    async def get_queue_entry(self, entry_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get queue entry from cache.
        
        Args:
            entry_id: Queue entry UUID
            
        Returns:
            Queue entry data if exists, None otherwise
        """
        key = CacheKeys.queue_entry(entry_id)
        return await self.redis.get_json(key)

    async def set_queue_entry(
        self,
        entry_id: UUID,
        entry_data: Dict[str, Any]
    ) -> bool:
        """
        Store queue entry in cache with TTL.
        
        Args:
            entry_id: Queue entry UUID
            entry_data: Queue entry data to cache
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.queue_entry(entry_id)
        ttl = self.ttl_config["queue"]
        return await self.redis.set_json(key, entry_data, ttl)

    async def delete_queue_entry(self, entry_id: UUID) -> bool:
        """
        Delete queue entry from cache.
        
        Args:
            entry_id: Queue entry UUID
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.queue_entry(entry_id)
        return await self.redis.delete(key)

    async def get_active_queue(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get active queue state from cache.
        
        Returns:
            List of queue entries if exists, None otherwise
        """
        key = CacheKeys.active_queue()
        data = await self.redis.get_json(key)
        return data if data else None

    async def set_active_queue(self, queue_data: List[Dict[str, Any]]) -> bool:
        """
        Store active queue state in cache with TTL.
        
        Args:
            queue_data: List of queue entries
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.active_queue()
        ttl = self.ttl_config["queue"]
        return await self.redis.set_json(key, queue_data, ttl)

    async def get_queue_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get queue statistics from cache.
        
        Returns:
            Queue statistics if exists, None otherwise
        """
        key = CacheKeys.queue_stats()
        return await self.redis.get_json(key)

    async def set_queue_stats(self, stats_data: Dict[str, Any]) -> bool:
        """
        Store queue statistics in cache with short TTL.
        
        Args:
            stats_data: Queue statistics
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.queue_stats()
        # Queue stats have shorter TTL (30 seconds as per requirements)
        ttl = 30
        return await self.redis.set_json(key, stats_data, ttl)

    async def invalidate_queue(self) -> bool:
        """
        Invalidate all queue cache entries.
        
        This is called when queue state changes to ensure cache consistency.
        
        Returns:
            True if all invalidations successful, False otherwise
        """
        keys_to_delete = [
            CacheKeys.active_queue(),
            CacheKeys.queue_stats()
        ]
        
        success = True
        for key in keys_to_delete:
            result = await self.redis.delete(key)
            success = success and result
        
        return success

    # ==================== Permission Cache Operations ====================

    async def get_user_permissions(self, user_id: UUID) -> Optional[List[Dict[str, Any]]]:
        """
        Get user permissions from cache.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of permissions if exists, None otherwise
        """
        key = CacheKeys.user_permissions(user_id)
        data = await self.redis.get_json(key)
        return data if data else None

    async def set_user_permissions(
        self,
        user_id: UUID,
        permissions: List[Dict[str, Any]]
    ) -> bool:
        """
        Store user permissions in cache with TTL.
        
        Args:
            user_id: User UUID
            permissions: List of permissions
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.user_permissions(user_id)
        ttl = self.ttl_config["permission"]
        return await self.redis.set_json(key, permissions, ttl)

    async def delete_user_permissions(self, user_id: UUID) -> bool:
        """
        Delete user permissions from cache.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.user_permissions(user_id)
        return await self.redis.delete(key)

    async def get_user_roles(self, user_id: UUID) -> Optional[List[str]]:
        """
        Get user roles from cache.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of role names if exists, None otherwise
        """
        key = CacheKeys.user_roles(user_id)
        data = await self.redis.get_json(key)
        return data if data else None

    async def set_user_roles(
        self,
        user_id: UUID,
        roles: List[str]
    ) -> bool:
        """
        Store user roles in cache with TTL.
        
        Args:
            user_id: User UUID
            roles: List of role names
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.user_roles(user_id)
        ttl = self.ttl_config["permission"]
        return await self.redis.set_json(key, roles, ttl)

    async def delete_user_roles(self, user_id: UUID) -> bool:
        """
        Delete user roles from cache.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.user_roles(user_id)
        return await self.redis.delete(key)

    async def invalidate_user_permissions(self, user_id: UUID) -> bool:
        """
        Invalidate all permission-related cache for a user.
        
        This is called when user roles or permissions change.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if all invalidations successful, False otherwise
        """
        perm_success = await self.delete_user_permissions(user_id)
        role_success = await self.delete_user_roles(user_id)
        
        return perm_success and role_success

    # ==================== Rate Limiting Operations ====================

    async def increment_rate_limit(
        self,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None
    ) -> Optional[int]:
        """
        Increment rate limit counter.
        
        Args:
            user_id: Optional user UUID
            ip_address: Optional IP address
            
        Returns:
            Current count if successful, None otherwise
        """
        if user_id:
            key = CacheKeys.rate_limit_user(user_id)
            ttl = 60  # 1 minute window
        elif ip_address:
            key = CacheKeys.rate_limit_ip(ip_address)
            ttl = 60  # 1 minute window
        else:
            return None
        
        count = await self.redis.increment(key)
        
        if count == 1:
            # First request in window, set expiration
            await self.redis.expire(key, ttl)
        
        return count

    async def get_rate_limit_count(
        self,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None
    ) -> int:
        """
        Get current rate limit count.
        
        Args:
            user_id: Optional user UUID
            ip_address: Optional IP address
            
        Returns:
            Current count, 0 if not found
        """
        if user_id:
            key = CacheKeys.rate_limit_user(user_id)
        elif ip_address:
            key = CacheKeys.rate_limit_ip(ip_address)
        else:
            return 0
        
        value = await self.redis.get(key)
        return int(value) if value else 0

    # ==================== Account Lockout Operations ====================

    async def increment_login_attempts(self, user_id: UUID) -> Optional[int]:
        """
        Increment failed login attempts counter.
        
        Args:
            user_id: User UUID
            
        Returns:
            Current attempt count if successful, None otherwise
        """
        key = CacheKeys.login_attempts(user_id)
        count = await self.redis.increment(key)
        
        if count == 1:
            # First failed attempt, set expiration to lockout duration
            ttl = settings.ACCOUNT_LOCKOUT_MINUTES * 60
            await self.redis.expire(key, ttl)
        
        return count

    async def get_login_attempts(self, user_id: UUID) -> int:
        """
        Get current failed login attempts count.
        
        Args:
            user_id: User UUID
            
        Returns:
            Current attempt count, 0 if not found
        """
        key = CacheKeys.login_attempts(user_id)
        value = await self.redis.get(key)
        return int(value) if value else 0

    async def reset_login_attempts(self, user_id: UUID) -> bool:
        """
        Reset failed login attempts counter.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.login_attempts(user_id)
        return await self.redis.delete(key)

    async def lock_account(self, user_id: UUID) -> bool:
        """
        Lock user account.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if successful, False otherwise
        """
        key = CacheKeys.account_locked(user_id)
        ttl = settings.ACCOUNT_LOCKOUT_MINUTES * 60
        return await self.redis.set(key, "locked", ttl)

    async def is_account_locked(self, user_id: UUID) -> bool:
        """
        Check if account is locked.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if locked, False otherwise
        """
        key = CacheKeys.account_locked(user_id)
        return await self.redis.exists(key)

    # ==================== Idempotency Operations ====================

    async def check_idempotency(
        self,
        operation_type: str,
        key: str,
        ttl: int = 300
    ) -> bool:
        """
        Check and set idempotency key atomically.
        
        This prevents duplicate operations by using Redis SETNX.
        
        Args:
            operation_type: Type of operation (e.g., 'create_patient', 'add_to_queue')
            key: Unique identifier for the operation
            ttl: Time to live in seconds (default 5 minutes)
            
        Returns:
            True if operation should proceed (key was set), False if duplicate
        """
        cache_key = CacheKeys.idempotency_key(operation_type, key)
        timestamp = datetime.utcnow().isoformat()
        
        # Atomic set-if-not-exists
        return await self.redis.set_if_not_exists(cache_key, timestamp, ttl)

    async def clear_idempotency(self, operation_type: str, key: str) -> bool:
        """
        Clear idempotency key.
        
        Args:
            operation_type: Type of operation
            key: Unique identifier for the operation
            
        Returns:
            True if successful, False otherwise
        """
        cache_key = CacheKeys.idempotency_key(operation_type, key)
        return await self.redis.delete(cache_key)

    # ==================== Health Check Operations ====================

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Redis health and connectivity.
        
        Returns:
            Health status dictionary
        """
        try:
            is_connected = await self.redis.ping()
            
            return {
                "status": "healthy" if is_connected else "unhealthy",
                "connected": is_connected,
                "message": "Redis is operational" if is_connected else "Redis connection failed"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "message": f"Redis health check failed: {str(e)}"
            }

    # ==================== Utility Operations ====================

    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for a key.
        
        Args:
            key: Cache key
            
        Returns:
            Remaining TTL in seconds, None if key doesn't exist or no TTL
        """
        return await self.redis.ttl(key)

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if exists, False otherwise
        """
        return await self.redis.exists(key)

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        WARNING: Use with caution in production.
        
        Args:
            pattern: Key pattern (e.g., 'cache:patient:*')
            
        Returns:
            Number of keys deleted
        """
        # This is a placeholder - actual implementation would need
        # to use SCAN to avoid blocking Redis
        # For now, return 0 as this is a dangerous operation
        return 0


# Dependency injection helper
async def get_cache_service(redis_client: RedisClient) -> CacheService:
    """
    Get cache service instance.
    
    Args:
        redis_client: Redis client instance
        
    Returns:
        CacheService instance
    """
    return CacheService(redis_client)
