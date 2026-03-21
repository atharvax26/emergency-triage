"""Redis client setup with connection pooling."""

import json
from typing import Any, Optional
from redis import asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings


class RedisClient:
    """Redis client wrapper with connection pooling and error handling."""

    def __init__(self):
        """Initialize Redis client."""
        self._redis: Optional[Redis] = None
        self._connection_pool: Optional[aioredis.ConnectionPool] = None

    async def connect(self):
        """Establish Redis connection with connection pooling."""
        try:
            self._connection_pool = aioredis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,
                encoding="utf-8",
            )
            self._redis = Redis(connection_pool=self._connection_pool)
            
            # Test connection
            await self._redis.ping()
            
        except RedisError as e:
            raise RuntimeError(f"Failed to connect to Redis: {e}")

    async def disconnect(self):
        """Close Redis connection gracefully."""
        if self._redis:
            await self._redis.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()

    async def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis.
        
        Args:
            key: Cache key
            
        Returns:
            Value if exists, None otherwise
        """
        try:
            return await self._redis.get(key)
        except RedisError:
            # Graceful degradation - return None on Redis failure
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in Redis with optional TTL.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if ttl:
                await self._redis.setex(key, ttl, value)
            else:
                await self._redis.set(key, value)
            return True
        except RedisError:
            # Graceful degradation - return False on Redis failure
            return False

    async def set_if_not_exists(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in Redis only if key doesn't exist (SETNX).
        
        This is an atomic operation useful for distributed locking
        and idempotency protection.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time to live in seconds
            
        Returns:
            True if key was set (didn't exist), False if key already exists
        """
        try:
            if ttl:
                # Use SET with NX and EX options
                result = await self._redis.set(key, value, nx=True, ex=ttl)
            else:
                # Use SETNX
                result = await self._redis.setnx(key, value)
            return bool(result)
        except RedisError:
            # Graceful degradation - return False on Redis failure
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from Redis.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._redis.delete(key)
            return True
        except RedisError:
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis.
        
        Args:
            key: Cache key
            
        Returns:
            True if exists, False otherwise
        """
        try:
            return await self._redis.exists(key) > 0
        except RedisError:
            return False

    async def get_json(self, key: str) -> Optional[dict]:
        """
        Get JSON value from Redis.
        
        Args:
            key: Cache key
            
        Returns:
            Parsed JSON dict if exists, None otherwise
        """
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(
        self,
        key: str,
        value: dict,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set JSON value in Redis.
        
        Args:
            key: Cache key
            value: Dict to store as JSON
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, ttl)
        except (TypeError, json.JSONEncodeError):
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment counter in Redis.
        
        Args:
            key: Cache key
            amount: Amount to increment by
            
        Returns:
            New value if successful, None otherwise
        """
        try:
            return await self._redis.incrby(key, amount)
        except RedisError:
            return None

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration on existing key.
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._redis.expire(key, ttl)
            return True
        except RedisError:
            return False

    async def ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for key.
        
        Args:
            key: Cache key
            
        Returns:
            Remaining TTL in seconds, None if key doesn't exist or no TTL
        """
        try:
            ttl = await self._redis.ttl(key)
            return ttl if ttl > 0 else None
        except RedisError:
            return None

    async def ping(self) -> bool:
        """
        Check Redis connectivity.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            await self._redis.ping()
            return True
        except RedisError:
            return False


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """
    Dependency for Redis client.
    
    Returns:
        RedisClient instance
    """
    return redis_client
