"""Audit logging middleware for automatic request tracking."""

import asyncio
from typing import Callable
from uuid import UUID, uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.audit.service import AuditEngine
from app.database.session import AsyncSessionLocal


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic audit logging of all authenticated API requests.
    
    Features:
    - Captures all authenticated API requests automatically
    - Extracts request metadata (endpoint, method, status_code, ip_address, user_agent)
    - Generates unique request_id for each request (UUID)
    - Logs action to AuditEngine asynchronously after response
    - Handles both successful and failed requests
    - Extracts user info from request state (set by auth middleware)
    - Maps HTTP methods to actions (GET=read, POST=create, PUT=update, DELETE=delete)
    - Skips health check endpoints (/health, /health/ready, /health/live)
    
    The middleware adds a request_id to request.state for correlation tracking
    and logs the request asynchronously to avoid blocking the response.
    """
    
    # Endpoints to skip audit logging
    SKIP_PATHS = {
        "/health",
        "/health/ready",
        "/health/live",
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    # HTTP method to action mapping
    METHOD_TO_ACTION = {
        "GET": "read",
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request and log to audit system.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or endpoint handler
            
        Returns:
            HTTP response
        """
        # Generate unique request ID
        request_id = uuid4()
        request.state.request_id = request_id
        
        # Skip audit logging for excluded paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        
        # Process request
        response = await call_next(request)
        
        # Log asynchronously (fire and forget)
        asyncio.create_task(
            self._log_request(request, response, request_id)
        )
        
        return response
    
    async def _log_request(
        self,
        request: Request,
        response: Response,
        request_id: UUID,
    ) -> None:
        """
        Log request to audit system asynchronously.
        
        Args:
            request: HTTP request
            response: HTTP response
            request_id: Unique request identifier
        """
        try:
            # Extract user info from request state (set by auth dependency)
            user_id = None
            if hasattr(request.state, "user"):
                user_info = request.state.user
                if isinstance(user_info, dict):
                    user_id = user_info.get("user_id")
                elif hasattr(user_info, "user_id"):
                    user_id = user_info.user_id
            
            # Extract IP address
            ip_address = self._get_client_ip(request)
            
            # Extract user agent
            user_agent = request.headers.get("user-agent", "unknown")
            
            # Map HTTP method to action
            action = self.METHOD_TO_ACTION.get(request.method, "unknown")
            
            # Extract resource type from path
            resource_type = self._extract_resource_type(request.url.path)
            
            # Determine status
            status = "success" if 200 <= response.status_code < 400 else "failure"
            
            # Build metadata
            metadata = {
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "query_params": dict(request.query_params) if request.query_params else None,
            }
            
            # Create database session and log action
            async with AsyncSessionLocal() as db:
                audit_engine = AuditEngine(db)
                await audit_engine.log_action(
                    user_id=user_id,
                    action=f"{resource_type}.{action}",
                    resource_type=resource_type,
                    status=status,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_id=request_id,
                    metadata=metadata,
                )
        
        except Exception as e:
            # Log error but don't fail the request
            # In production, this should use proper logging
            print(f"Audit logging failed: {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.
        
        Checks X-Forwarded-For header first (for proxied requests),
        then falls back to direct client host.
        
        Args:
            request: HTTP request
            
        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (for proxied requests)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to direct client host
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _extract_resource_type(self, path: str) -> str:
        """
        Extract resource type from request path.
        
        Examples:
            /api/v1/patients -> patients
            /api/v1/patients/123 -> patients
            /api/v1/queue/entries -> queue
            /auth/login -> auth
        
        Args:
            path: Request path
            
        Returns:
            Resource type
        """
        # Remove leading/trailing slashes and split
        parts = path.strip("/").split("/")
        
        # Skip common prefixes
        filtered_parts = [
            p for p in parts
            if p not in {"api", "v1", "v2"}
        ]
        
        # Return first meaningful part or "unknown"
        if filtered_parts:
            return filtered_parts[0]
        
        return "unknown"
