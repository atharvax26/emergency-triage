"""Authentication API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.client import RedisClient, get_redis
from app.core.auth.service import AuthService
from app.core.auth.password import validate_password_complexity, hash_password
from app.database.session import get_async_db
from app.schemas.auth import (
    LoginCredentials,
    TokenPair,
    AuthResult,
    RefreshTokenRequest,
    ChangePasswordRequest,
)
from app.utils.exceptions import (
    AuthenticationError,
    AccountLockedError,
    InvalidTokenError,
    PasswordComplexityError,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


# Dependency to get AuthService
async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    cache: Annotated[RedisClient, Depends(get_redis)]
) -> AuthService:
    """
    Dependency to get AuthService instance.
    
    Args:
        db: Database session
        cache: Redis client
        
    Returns:
        AuthService instance
    """
    return AuthService(db=db, cache=cache)


# Dependency to validate JWT token and get current user
async def get_current_user(
    authorization: Annotated[str, Header()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> dict:
    """
    Dependency to validate JWT token and extract current user info.
    
    Args:
        authorization: Authorization header with Bearer token
        auth_service: AuthService instance
        
    Returns:
        Dict with user_id, email, and roles
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        validation = await auth_service.validate_token(token)
        
        if not validation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=validation.error or "Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "user_id": validation.user_id,
            "email": validation.email,
            "roles": validation.roles or []
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/login",
    response_model=AuthResult,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user with email and password, return access and refresh tokens"
)
async def login(
    credentials: LoginCredentials,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> AuthResult:
    """
    Authenticate user and return tokens.
    
    Args:
        credentials: Login credentials (email and password)
        auth_service: AuthService instance
        
    Returns:
        AuthResult with user info and token pair
        
    Raises:
        HTTPException: 401 if credentials are invalid or account is locked
        HTTPException: 500 if authentication service fails
    """
    try:
        result = await auth_service.authenticate(credentials)
        return result
    except AccountLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        )


@router.post(
    "/refresh",
    response_model=TokenPair,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Generate new access token using refresh token"
)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> TokenPair:
    """
    Refresh access token using refresh token.
    
    Args:
        request: Refresh token request
        auth_service: AuthService instance
        
    Returns:
        New token pair (access and refresh tokens)
        
    Raises:
        HTTPException: 401 if refresh token is invalid or revoked
        HTTPException: 500 if token refresh fails
    """
    try:
        token_pair = await auth_service.refresh_token(request.refresh_token)
        return token_pair
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User logout",
    description="Logout user and revoke tokens"
)
async def logout(
    authorization: Annotated[str, Header()],
    current_user: Annotated[dict, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> dict:
    """
    Logout user and revoke tokens.
    
    Args:
        authorization: Authorization header with Bearer token
        current_user: Current authenticated user
        auth_service: AuthService instance
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 401 if token is invalid
        HTTPException: 500 if logout fails
    """
    try:
        token = authorization.replace("Bearer ", "")
        await auth_service.revoke_token(token)
        
        return {
            "message": "Successfully logged out",
            "user_id": str(current_user["user_id"])
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed",
        )


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get current authenticated user information"
)
async def get_me(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """
    Get current authenticated user information.
    
    Args:
        current_user: Current authenticated user from JWT token
        
    Returns:
        User information (user_id, email, roles)
        
    Raises:
        HTTPException: 401 if token is invalid
    """
    return {
        "user_id": str(current_user["user_id"]),
        "email": current_user["email"],
        "roles": current_user["roles"]
    }


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change password",
    description="Change user password"
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> dict:
    """
    Change user password.
    
    Args:
        request: Change password request with current and new password
        current_user: Current authenticated user
        auth_service: AuthService instance
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 401 if current password is incorrect
        HTTPException: 422 if new password doesn't meet complexity requirements
        HTTPException: 500 if password change fails
    """
    try:
        # Validate new password complexity
        is_valid, error_message = validate_password_complexity(request.new_password)
        if not is_valid:
            raise PasswordComplexityError(error_message)
        
        # Re-authenticate user with current password
        credentials = LoginCredentials(
            email=current_user["email"],
            password=request.current_password
        )
        
        try:
            await auth_service.authenticate(credentials)
        except (AuthenticationError, AccountLockedError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )
        
        # Update password in database
        from sqlalchemy import select, update
        from app.models.user import User
        
        user_id = current_user["user_id"]
        new_password_hash = hash_password(request.new_password)
        
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(password_hash=new_password_hash)
        )
        
        await auth_service.db.execute(stmt)
        await auth_service.db.commit()
        
        return {
            "message": "Password changed successfully",
            "user_id": str(user_id)
        }
        
    except PasswordComplexityError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed",
        )
