"""Transactional authentication service methods.

This module demonstrates how to refactor authentication service methods
to use the Unit of Work pattern for atomic multi-step operations.

Requirements: 19.4, 19.5
"""

from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.cache.client import RedisClient
from app.cache.keys import CacheKeys
from app.config import settings
from app.core.auth.jwt import generate_access_token, generate_refresh_token
from app.core.auth.password import verify_password
from app.core.idempotency import IdempotencyManager
from app.core.unit_of_work import UnitOfWork
from app.models.user import User, Session, UserRole
from app.schemas.auth import LoginCredentials, AuthResult, TokenPair
from app.utils.exceptions import (
    AuthenticationError,
    AccountLockedError,
)


class TransactionalAuthService:
    """
    Authentication service with transactional operations.
    
    This demonstrates the refactored approach using Unit of Work pattern
    for atomic multi-step operations.
    
    Requirements: 19.4, 19.5
    """
    
    def __init__(self, cache: RedisClient):
        """
        Initialize TransactionalAuthService.
        
        Args:
            cache: Redis cache client
        """
        self.cache = cache
    
    async def authenticate_atomic(
        self,
        credentials: LoginCredentials,
        idempotency_key: str = None
    ) -> AuthResult:
        """
        Authenticate user with atomic transaction handling.
        
        This method demonstrates the refactored approach:
        1. All database operations are wrapped in a single UnitOfWork
        2. Session creation and user lookup are atomic
        3. Rollback happens automatically on any failure
        4. Optional idempotency protection for duplicate requests
        
        Args:
            credentials: Login credentials (email, password)
            idempotency_key: Optional idempotency key for duplicate prevention
            
        Returns:
            AuthResult with user info and token pair
            
        Raises:
            AuthenticationError: If credentials are invalid
            AccountLockedError: If account is locked due to failed attempts
            
        Requirements: 1.1, 1.2, 1.7, 3.1, 19.4, 19.5
        """
        # Check idempotency if key provided
        if idempotency_key:
            manager = IdempotencyManager(self.cache)
            existing_result = await manager.get_result(
                idempotency_key,
                "authenticate"
            )
            if existing_result:
                return AuthResult(**existing_result)
            
            # Acquire idempotency lock
            can_proceed = await manager.check_and_set(
                idempotency_key,
                "authenticate"
            )
            if not can_proceed:
                # Another request is processing
                raise AuthenticationError("Authentication request already in progress")
        
        # Check if account is locked
        user_id_for_lock = await self._get_user_id_by_email(credentials.email)
        if user_id_for_lock:
            if await self._is_account_locked(user_id_for_lock):
                raise AccountLockedError(
                    f"Account locked due to too many failed login attempts. "
                    f"Try again in {settings.ACCOUNT_LOCKOUT_MINUTES} minutes."
                )
        
        # Use Unit of Work for atomic transaction
        async with UnitOfWork() as uow:
            # Get user from database
            stmt = select(User).where(
                User.email == credentials.email,
                User.is_active == True
            ).options(
                selectinload(User.user_roles).selectinload(UserRole.role)
            )
            result = await uow.session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                # Track failed attempt even if user doesn't exist
                if user_id_for_lock:
                    await self._track_failed_login(user_id_for_lock)
                raise AuthenticationError("Invalid email or password")
            
            # Verify password
            if not verify_password(credentials.password, user.password_hash):
                await self._track_failed_login(user.id)
                raise AuthenticationError("Invalid email or password")
            
            # Clear failed login attempts on successful authentication
            await self._clear_failed_login_attempts(user.id)
            
            # Get user roles
            roles = [ur.role.name for ur in user.user_roles]
            
            # Generate tokens
            access_token = generate_access_token(
                user_id=str(user.id),
                email=user.email,
                roles=roles
            )
            refresh_token, token_id = generate_refresh_token(user_id=str(user.id))
            
            # Create session in database (within transaction)
            token_hash = self._hash_token(refresh_token)
            session = Session(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.utcnow() + timedelta(
                    days=settings.REFRESH_TOKEN_EXPIRE_DAYS
                )
            )
            uow.session.add(session)
            
            # Flush to get session ID before commit
            await uow.session.flush()
            
            # Transaction commits automatically on context exit
        
        # After successful transaction, update cache
        await self._store_session_in_cache(
            token_hash=token_hash,
            user_id=user.id,
            email=user.email,
            roles=roles
        )
        
        # Track user sessions for concurrent session limit
        await self._track_user_session(user.id, token_hash)
        
        # Create response
        token_pair = TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
        result = AuthResult(
            user_id=user.id,
            email=user.email,
            roles=roles,
            tokens=token_pair
        )
        
        # Store result for idempotency
        if idempotency_key:
            manager = IdempotencyManager(self.cache)
            await manager.store_result(
                idempotency_key,
                "authenticate",
                result.model_dump()
            )
        
        return result
    
    async def _get_user_id_by_email(self, email: str) -> UUID:
        """Get user ID by email (outside transaction)."""
        async with UnitOfWork() as uow:
            stmt = select(User.id).where(User.email == email)
            result = await uow.session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def _is_account_locked(self, user_id: UUID) -> bool:
        """Check if account is locked."""
        locked_key = CacheKeys.account_locked(user_id)
        return await self.cache.exists(locked_key)
    
    async def _track_failed_login(self, user_id: UUID) -> None:
        """Track failed login attempt."""
        attempts_key = CacheKeys.login_attempts(user_id)
        attempts = await self.cache.increment(attempts_key)
        
        if attempts == 1:
            await self.cache.expire(
                attempts_key,
                settings.ACCOUNT_LOCKOUT_MINUTES * 60
            )
        
        if attempts >= settings.MAX_LOGIN_ATTEMPTS:
            locked_key = CacheKeys.account_locked(user_id)
            await self.cache.set(
                locked_key,
                "1",
                ttl=settings.ACCOUNT_LOCKOUT_MINUTES * 60
            )
    
    async def _clear_failed_login_attempts(self, user_id: UUID) -> None:
        """Clear failed login attempts counter."""
        attempts_key = CacheKeys.login_attempts(user_id)
        await self.cache.delete(attempts_key)
    
    async def _store_session_in_cache(
        self,
        token_hash: str,
        user_id: UUID,
        email: str,
        roles: List[str]
    ) -> None:
        """Store session data in Redis cache."""
        session_key = CacheKeys.session(token_hash)
        session_data = {
            "user_id": str(user_id),
            "email": email,
            "roles": roles
        }
        await self.cache.set_json(
            session_key,
            session_data,
            ttl=settings.CACHE_TTL_SESSION
        )
    
    async def _track_user_session(self, user_id: UUID, token_hash: str) -> None:
        """Track user session for concurrent session limit."""
        sessions_key = CacheKeys.user_sessions(user_id)
        
        sessions_json = await self.cache.get(sessions_key)
        if sessions_json:
            import json
            sessions = json.loads(sessions_json)
        else:
            sessions = []
        
        sessions.append(token_hash)
        
        if len(sessions) > settings.MAX_CONCURRENT_SESSIONS:
            oldest_token_hash = sessions.pop(0)
            # Note: Would need to revoke oldest session here
        
        import json
        await self.cache.set(
            sessions_key,
            json.dumps(sessions),
            ttl=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )
    
    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash token for storage."""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()
