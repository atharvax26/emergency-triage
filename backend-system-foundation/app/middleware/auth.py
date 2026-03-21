"""JWT authentication middleware for request authentication."""

from typing import Callable
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.core.auth.service import AuthService
from app.database.session import AsyncSessionLocal
from app.cache.client import redis_client


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for JWT authentication.
    
    Features:
    - Extracts JWT from Authorization header (Bearer token)
    - Validates token using AuthService
    - Checks token revocation status
    - Attaches user info to request.state for downstream use
    - Returns 401 for unauthenticated requests
    - Skips authentication for public endpoints
    
    Public endpoints (no authentication required):
    - /health, /health/ready, /health/live
    - /, /docs, /redoc, /openapi.json
    - /api/v1/auth/login, /api/v1/auth/register, /api/v1/auth/refresh
    
    After successful authentication, request.state contains:
    - user_id: UUID of authenticated user
    - email: User email
    - roles: List of user roles
    - token: Original JWT token
    """
    
    # Public endpoints that don't require authentication
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/health/ready",
        "/health/live",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
    }
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request and authenticate user.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or endpoint handler
            
        Returns:
            HTTP response (401 if authentication fails, or response from next handler)
        """
        # Skip authentication for public endpoints
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Extract Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "authentication_required",
                    "message": "Authorization header is required"
                }
            )
        
        # Parse Bearer token
        parts = auth_header.split()
        
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                status_code=401,
                content={
                    "error": "invalid_authorization_header",
                    "message": "Authorization header must be 'Bearer <token>'"
                }
            )
        
        token = parts[1]
        
        # Validate token using AuthService
        try:
            async with AsyncSessionLocal() as db:
                auth_service = AuthService(db, redis_client)
                validation_result = await auth_service.validate_token(token)
                
                if not validation_result.is_valid:
                    return JSONResponse(
                        status_code=401,
                        content={
                            "error": "invalid_token",
                            "message": validation_result.error or "Token validation failed"
                        }
                    )
                
                # Attach user info to request state
                request.state.user_id = validation_result.user_id
                request.state.email = validation_result.email
                request.state.roles = validation_result.roles or []
                request.state.token = token
                
                # For backward compatibility with audit middleware
                request.state.user = {
                    "user_id": validation_result.user_id,
                    "email": validation_result.email,
                    "roles": validation_result.roles or []
                }
        
        except Exception as e:
            # Log error but don't expose internal details
            print(f"Authentication error: {e}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "authentication_failed",
                    "message": "Authentication failed"
                }
            )
        
        # Continue to next middleware/handler
        return await call_next(request)
