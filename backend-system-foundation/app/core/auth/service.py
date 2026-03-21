"""Authentication service implementation."""

import hashlib
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.cache.client import RedisClient
from app.cache.keys import CacheKeys
from app.config import settings
from app.core.auth.jwt import (
    generate_access_token,
    generate_refresh_token,
    validate_token,
    get_token_type,
    get_token_jti,
)
from app.core.auth.password import hash_password, verify_password, validate_password_complexity
from app.models.user import User, Session, UserRole, Role
from app.schemas.auth import LoginCredentials, AuthResult, TokenPair, TokenValidation
from app.utils.exceptions import (
    AuthenticationError,
    AccountLockedError,
    InvalidTokenError,
    PasswordComplexityError,
    ConflictError,
)


class AuthService:
    """
    Authentication service for user login, token management, and session handling.
    
    Responsibilities:
        - User authentication with credentials
        - JWT token generation and validation
        - Token refresh and revocation
        - Session management via Redis
        - Account lockout after failed attempts
        - Password validation and hashing
    """
    
    def __init__(self, db: AsyncSession, cache: RedisClient):
        """
        Initialize AuthService.
        
        Args:
            db: Database session
            cache: Redis cache client
        """
        self.db = db
        self.cache = cache
    
    async def authenticate(self, credentials: LoginCredentials) -> AuthResult:
        """
        Authenticate user with email and password.
        
        Args:
            credentials: Login credentials (email, password)
            
        Returns:
            AuthResult with user info and token pair
            
        Raises:
            AuthenticationError: If credentials are invalid
            AccountLockedError: If account is locked due to failed attempts
            
        Requirements: 1.1, 1.2, 1.7, 3.1
        """
        # Check if account is locked
        user_id_for_lock = await self._get_user_id_by_email(credentials.email)
        if user_id_for_lock:
            if await self._is_account_locked(user_id_for_lock):
                raise AccountLockedError(
                    f"Account locked due to too many failed login attempts. "
                    f"Try again in {settings.ACCOUNT_LOCKOUT_MINUTES} minutes."
                )
        
        # Get user from database
        stmt = select(User).where(
            User.email == credentials.email,
            User.is_active == True
        ).options(
            selectinload(User.user_roles).selectinload(UserRole.role)
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            # Track failed attempt even if user doesn't exist (prevent enumeration)
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
        
        # Create session in database
        token_hash = self._hash_token(refresh_token)
        session = Session(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        try:
            self.db.add(session)
            await self.db.commit()
        except IntegrityError as e:
            await self.db.rollback()
            # This should be extremely rare - token_hash collision
            # The unique constraint on token_hash prevents duplicate sessions
            if "token_hash" in str(e.orig) or "uq_sessions_token_hash" in str(e.orig):
                raise ConflictError(
                    message="Session token conflict. Please try again.",
                    details={"error": "token_hash_collision"}
                )
            raise
        
        # Store session in Redis cache
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
        
        return AuthResult(
            user_id=user.id,
            email=user.email,
            roles=roles,
            tokens=token_pair
        )
    
    async def validate_token(self, token: str) -> TokenValidation:
        """
        Validate JWT token and extract claims.
        
        Args:
            token: JWT token to validate
            
        Returns:
            TokenValidation with validation result and user info
            
        Requirements: 1.3, 3.4
        """
        # Validate token signature and expiration
        claims = validate_token(token)
        
        if not claims:
            return TokenValidation(
                is_valid=False,
                error="Invalid or expired token"
            )
        
        # Check if token is revoked
        token_hash = self._hash_token(token)
        if await self._is_token_revoked(token_hash):
            return TokenValidation(
                is_valid=False,
                error="Token has been revoked"
            )
        
        # Extract user info from claims
        user_id = claims.get("sub")
        email = claims.get("email")
        roles = claims.get("roles", [])
        
        return TokenValidation(
            is_valid=True,
            user_id=UUID(user_id) if user_id else None,
            email=email,
            roles=roles
        )
    
    async def refresh_token(self, refresh_token: str) -> TokenPair:
        """
        Generate new access token using refresh token.
        
        Args:
            refresh_token: JWT refresh token
            
        Returns:
            New token pair (access + refresh tokens)
            
        Raises:
            InvalidTokenError: If refresh token is invalid or revoked
            
        Requirements: 1.4
        """
        # Validate refresh token
        claims = validate_token(refresh_token)
        
        if not claims or get_token_type(refresh_token) != "refresh":
            raise InvalidTokenError("Invalid refresh token")
        
        # Check if token is revoked
        token_hash = self._hash_token(refresh_token)
        if await self._is_token_revoked(token_hash):
            raise InvalidTokenError("Refresh token has been revoked")
        
        # Get user from database
        user_id = UUID(claims.get("sub"))
        stmt = select(User).where(
            User.id == user_id,
            User.is_active == True
        ).options(
            selectinload(User.user_roles).selectinload(UserRole.role)
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise InvalidTokenError("User not found or inactive")
        
        # Get user roles
        roles = [ur.role.name for ur in user.user_roles]
        
        # Generate new tokens
        new_access_token = generate_access_token(
            user_id=str(user.id),
            email=user.email,
            roles=roles
        )
        new_refresh_token, new_token_id = generate_refresh_token(user_id=str(user.id))
        
        # Revoke old refresh token
        await self.revoke_token(refresh_token)
        
        # Create new session in database
        new_token_hash = self._hash_token(new_refresh_token)
        session = Session(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        self.db.add(session)
        await self.db.commit()
        
        # Store new session in Redis cache
        await self._store_session_in_cache(
            token_hash=new_token_hash,
            user_id=user.id,
            email=user.email,
            roles=roles
        )
        
        # Track new session
        await self._track_user_session(user.id, new_token_hash)
        
        return TokenPair(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke token by adding it to Redis revocation list.
        
        Args:
            token: JWT token to revoke
            
        Returns:
            True if token was revoked successfully
            
        Requirements: 1.5, 3.6
        """
        token_hash = self._hash_token(token)
        
        # Add to revocation list in Redis
        revoke_key = CacheKeys.revoked_token(token_hash)
        
        # Set TTL based on token type
        claims = validate_token(token)
        if claims:
            exp = claims.get("exp")
            if exp:
                # Calculate remaining TTL
                ttl = int(exp - datetime.utcnow().timestamp())
                if ttl > 0:
                    await self.cache.set(revoke_key, "1", ttl=ttl)
        
        # Delete session from database
        stmt = select(Session).where(Session.token_hash == token_hash)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if session:
            await self.db.delete(session)
            await self.db.commit()
            
            # Remove from user sessions tracking
            await self._remove_user_session(session.user_id, token_hash)
        
        # Delete session from cache
        session_key = CacheKeys.session(token_hash)
        await self.cache.delete(session_key)
        
        return True
    
    async def _track_failed_login(self, user_id: UUID) -> None:
        """
        Track failed login attempt and lock account if threshold exceeded.
        
        Args:
            user_id: User ID
            
        Requirements: 1.7
        """
        attempts_key = CacheKeys.login_attempts(user_id)
        
        # Increment failed attempts counter
        attempts = await self.cache.increment(attempts_key)
        
        if attempts == 1:
            # Set TTL on first attempt (reset after lockout period)
            await self.cache.expire(
                attempts_key,
                settings.ACCOUNT_LOCKOUT_MINUTES * 60
            )
        
        # Lock account if threshold exceeded
        if attempts >= settings.MAX_LOGIN_ATTEMPTS:
            locked_key = CacheKeys.account_locked(user_id)
            await self.cache.set(
                locked_key,
                "1",
                ttl=settings.ACCOUNT_LOCKOUT_MINUTES * 60
            )
    
    async def _is_account_locked(self, user_id: UUID) -> bool:
        """
        Check if account is locked.
        
        Args:
            user_id: User ID
            
        Returns:
            True if account is locked, False otherwise
        """
        locked_key = CacheKeys.account_locked(user_id)
        return await self.cache.exists(locked_key)
    
    async def _clear_failed_login_attempts(self, user_id: UUID) -> None:
        """
        Clear failed login attempts counter.
        
        Args:
            user_id: User ID
        """
        attempts_key = CacheKeys.login_attempts(user_id)
        await self.cache.delete(attempts_key)
    
    async def _is_token_revoked(self, token_hash: str) -> bool:
        """
        Check if token is in revocation list.
        
        Args:
            token_hash: Hashed token
            
        Returns:
            True if token is revoked, False otherwise
        """
        revoke_key = CacheKeys.revoked_token(token_hash)
        return await self.cache.exists(revoke_key)
    
    async def _store_session_in_cache(
        self,
        token_hash: str,
        user_id: UUID,
        email: str,
        roles: List[str]
    ) -> None:
        """
        Store session data in Redis cache.
        
        Args:
            token_hash: Hashed token
            user_id: User ID
            email: User email
            roles: User roles
        """
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
        """
        Track user session for concurrent session limit enforcement.
        
        Args:
            user_id: User ID
            token_hash: Hashed token
            
        Requirements: 3.5
        """
        sessions_key = CacheKeys.user_sessions(user_id)
        
        # Get current sessions
        sessions_json = await self.cache.get(sessions_key)
        if sessions_json:
            import json
            sessions = json.loads(sessions_json)
        else:
            sessions = []
        
        # Add new session
        sessions.append(token_hash)
        
        # Enforce concurrent session limit
        if len(sessions) > settings.MAX_CONCURRENT_SESSIONS:
            # Remove oldest session
            oldest_token_hash = sessions.pop(0)
            await self.revoke_token(oldest_token_hash)
        
        # Update sessions list
        import json
        await self.cache.set(
            sessions_key,
            json.dumps(sessions),
            ttl=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )
    
    async def _remove_user_session(self, user_id: UUID, token_hash: str) -> None:
        """
        Remove session from user sessions tracking.
        
        Args:
            user_id: User ID
            token_hash: Hashed token
        """
        sessions_key = CacheKeys.user_sessions(user_id)
        
        # Get current sessions
        sessions_json = await self.cache.get(sessions_key)
        if sessions_json:
            import json
            sessions = json.loads(sessions_json)
            
            # Remove session
            if token_hash in sessions:
                sessions.remove(token_hash)
                
                # Update sessions list
                await self.cache.set(
                    sessions_key,
                    json.dumps(sessions),
                    ttl=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
                )
    
    async def _get_user_id_by_email(self, email: str) -> Optional[UUID]:
        """
        Get user ID by email.
        
        Args:
            email: User email
            
        Returns:
            User ID if found, None otherwise
        """
        stmt = select(User.id).where(User.email == email)
        result = await self.db.execute(stmt)
        user_id = result.scalar_one_or_none()
        return user_id
    
    @staticmethod
    def _hash_token(token: str) -> str:
        """
        Hash token for storage and revocation checking.
        
        Args:
            token: JWT token
            
        Returns:
            SHA256 hash of token
        """
        return hashlib.sha256(token.encode()).hexdigest()
