"""RBAC authorization middleware for permission checking."""

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.core.auth.permissions import PermissionService
from app.database.session import AsyncSessionLocal
from app.cache.client import redis_client


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for RBAC authorization.
    
    Features:
    - Checks RBAC permissions for requested resource/action
    - Returns 403 for unauthorized requests
    - Integrates with PermissionService for permission checking
    - Extracts resource and action from request path and method
    - Skips authorization for public endpoints
    
    Resource/Action mapping:
    - GET /api/v1/patients -> resource=patient, action=read
    - POST /api/v1/patients -> resource=patient, action=create
    - PUT /api/v1/patients/{id} -> resource=patient, action=update
    - DELETE /api/v1/patients/{id} -> resource=patient, action=delete
    - POST /api/v1/queue/entries -> resource=queue, action=create
    - PUT /api/v1/queue/entries/{id}/assign -> resource=queue, action=assign
    
    Public endpoints (no authorization required):
    - Same as AuthenticationMiddleware.PUBLIC_PATHS
    - /api/v1/auth/* (authentication endpoints)
    
    Requires request.state.user_id to be set by AuthenticationMiddleware.
    """
    
    # Public endpoints that don't require authorization
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/health/ready",
        "/health/live",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    # Paths that start with these prefixes are public
    PUBLIC_PATH_PREFIXES = [
        "/api/v1/auth/",
    ]
    
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
        Process request and check authorization.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or endpoint handler
            
        Returns:
            HTTP response (403 if authorization fails, or response from next handler)
        """
        # Skip authorization for public endpoints
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Skip authorization for public path prefixes
        for prefix in self.PUBLIC_PATH_PREFIXES:
            if request.url.path.startswith(prefix):
                return await call_next(request)
        
        # Check if user is authenticated (should be set by AuthenticationMiddleware)
        if not hasattr(request.state, "user_id") or not request.state.user_id:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "authentication_required",
                    "message": "Authentication required for this endpoint"
                }
            )
        
        # Extract resource and action from request
        resource = self._extract_resource(request.url.path)
        action = self._extract_action(request.url.path, request.method)
        
        # Skip authorization if resource/action cannot be determined
        if not resource or not action:
            return await call_next(request)
        
        # Check permission using PermissionService
        try:
            async with AsyncSessionLocal() as db:
                permission_service = PermissionService(db, redis_client)
                has_permission = await permission_service.check_permission(
                    user_id=request.state.user_id,
                    resource=resource,
                    action=action
                )
                
                if not has_permission:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "insufficient_permissions",
                            "message": f"Insufficient permissions to {action} {resource}",
                            "required_permission": f"{resource}.{action}"
                        }
                    )
        
        except Exception as e:
            # Log error but don't expose internal details
            print(f"Authorization error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "authorization_check_failed",
                    "message": "Failed to check permissions"
                }
            )
        
        # Continue to next middleware/handler
        return await call_next(request)
    
    def _extract_resource(self, path: str) -> str:
        """
        Extract resource type from request path.
        
        Examples:
            /api/v1/patients -> patients
            /api/v1/patients/123 -> patients
            /api/v1/queue/entries -> queue
            /api/v1/users -> users
        
        Args:
            path: Request path
            
        Returns:
            Resource type (singular form)
        """
        # Remove leading/trailing slashes and split
        parts = path.strip("/").split("/")
        
        # Skip common prefixes
        filtered_parts = [
            p for p in parts
            if p not in {"api", "v1", "v2"}
        ]
        
        # Get first meaningful part
        if filtered_parts:
            resource = filtered_parts[0]
            
            # Convert plural to singular for consistency
            if resource.endswith("ies"):
                # entries -> entry
                return resource[:-3] + "y"
            elif resource.endswith("s"):
                # patients -> patient, users -> user
                return resource[:-1]
            
            return resource
        
        return ""
    
    def _extract_action(self, path: str, method: str) -> str:
        """
        Extract action from request path and method.
        
        Special cases:
            PUT /api/v1/queue/entries/{id}/assign -> assign
            PUT /api/v1/queue/entries/{id}/complete -> complete
        
        Default mapping:
            GET -> read
            POST -> create
            PUT/PATCH -> update
            DELETE -> delete
        
        Args:
            path: Request path
            method: HTTP method
            
        Returns:
            Action name
        """
        # Check for special action suffixes
        if "/assign" in path:
            return "assign"
        elif "/complete" in path:
            return "complete"
        elif "/cancel" in path:
            return "cancel"
        
        # Use default method mapping
        return self.METHOD_TO_ACTION.get(method, "read")
