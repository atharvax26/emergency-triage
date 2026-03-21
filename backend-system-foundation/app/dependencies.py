"""Dependency injection for FastAPI endpoints."""

from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_async_db
from app.cache.client import RedisClient, get_redis
from app.core.unit_of_work import get_transactional_session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session dependency.
    
    Yields:
        AsyncSession: Database session
    """
    async for session in get_async_db():
        yield session


async def get_db_transactional() -> AsyncGenerator[AsyncSession, None]:
    """
    Get transactional database session dependency.
    
    This provides automatic transaction management:
    - Begins transaction on entry
    - Commits on successful exit
    - Rolls back on exception
    
    Use this for endpoints that perform multiple database operations
    that should be atomic.
    
    Yields:
        AsyncSession: Database session with active transaction
    """
    async for session in get_transactional_session():
        yield session


async def get_cache() -> RedisClient:
    """
    Get Redis cache client dependency.
    
    Returns:
        RedisClient: Redis client instance
    """
    return await get_redis()


# Additional dependencies will be added as services are implemented
# - get_current_user (authentication)
# - check_permissions (authorization)
# - rate_limiter (rate limiting)
