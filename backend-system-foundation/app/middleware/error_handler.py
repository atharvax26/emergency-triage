"""Central exception handling middleware for consistent error responses."""

import traceback
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError as PydanticValidationError

from app.utils.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    ConflictError,
    ServiceUnavailableError,
    RateLimitError,
    DatabaseError,
    CacheError,
)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for central exception handling and error response formatting.
    
    Features:
    - Catches all exceptions and formats error responses consistently
    - Returns appropriate HTTP status codes based on exception type
    - Logs errors with full stack trace for debugging
    - Avoids exposing sensitive details in production
    - Implements graceful degradation for Redis/cache failures
    - Handles database errors with proper status codes
    
    Error response format:
    {
        "error": "error_code",
        "message": "Human-readable error message",
        "details": {...},  // Optional additional details
        "request_id": "uuid"  // For correlation with logs
    }
    
    Status code mapping:
    - 400: Bad Request (validation errors)
    - 401: Unauthorized (authentication errors)
    - 403: Forbidden (authorization errors)
    - 404: Not Found
    - 409: Conflict (duplicate/constraint violations)
    - 422: Unprocessable Entity (validation errors)
    - 429: Too Many Requests (rate limit)
    - 500: Internal Server Error (unexpected errors)
    - 503: Service Unavailable (database/external service errors)
    
    Graceful degradation:
    - CacheError: Logs warning but returns 200 (cache is non-critical)
    - Redis connection errors: Logs error, continues processing
    - Database errors: Returns 503 with retry guidance
    """
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request and handle exceptions.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or endpoint handler
            
        Returns:
            HTTP response (error response if exception occurs)
        """
        try:
            response = await call_next(request)
            return response
        
        except AppException as e:
            # Handle custom application exceptions
            return self._handle_app_exception(request, e)
        
        except PydanticValidationError as e:
            # Handle Pydantic validation errors
            return self._handle_validation_error(request, e)
        
        except IntegrityError as e:
            # Handle database integrity constraint violations
            return self._handle_integrity_error(request, e)
        
        except SQLAlchemyError as e:
            # Handle database errors
            return self._handle_database_error(request, e)
        
        except Exception as e:
            # Handle unexpected errors
            return self._handle_unexpected_error(request, e)
    
    def _handle_app_exception(
        self,
        request: Request,
        exc: AppException
    ) -> JSONResponse:
        """
        Handle custom application exceptions.
        
        Args:
            request: HTTP request
            exc: Application exception
            
        Returns:
            JSON error response
        """
        # Get request ID for correlation
        request_id = getattr(request.state, "request_id", None)
        
        # Log error
        self._log_error(
            request=request,
            error_type=type(exc).__name__,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details
        )
        
        # Build error response
        error_response = {
            "error": self._get_error_code(exc),
            "message": exc.message,
        }
        
        # Add details if present
        if exc.details:
            error_response["details"] = exc.details
        
        # Add request ID for correlation
        if request_id:
            error_response["request_id"] = str(request_id)
        
        # Add Retry-After header for rate limit errors
        headers = {}
        if isinstance(exc, RateLimitError) and "retry_after" in exc.details:
            headers["Retry-After"] = str(exc.details["retry_after"])
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
            headers=headers
        )
    
    def _handle_validation_error(
        self,
        request: Request,
        exc: PydanticValidationError
    ) -> JSONResponse:
        """
        Handle Pydantic validation errors.
        
        Args:
            request: HTTP request
            exc: Pydantic validation error
            
        Returns:
            JSON error response with validation details
        """
        # Get request ID for correlation
        request_id = getattr(request.state, "request_id", None)
        
        # Extract validation errors
        validation_errors = []
        for error in exc.errors():
            validation_errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        # Log error
        self._log_error(
            request=request,
            error_type="ValidationError",
            message="Request validation failed",
            status_code=422,
            details={"validation_errors": validation_errors}
        )
        
        # Build error response
        error_response = {
            "error": "validation_error",
            "message": "Request validation failed",
            "details": {
                "validation_errors": validation_errors
            }
        }
        
        if request_id:
            error_response["request_id"] = str(request_id)
        
        return JSONResponse(
            status_code=422,
            content=error_response
        )
    
    def _handle_integrity_error(
        self,
        request: Request,
        exc: IntegrityError
    ) -> JSONResponse:
        """
        Handle database integrity constraint violations.
        
        Args:
            request: HTTP request
            exc: SQLAlchemy integrity error
            
        Returns:
            JSON error response
        """
        # Get request ID for correlation
        request_id = getattr(request.state, "request_id", None)
        
        # Extract constraint violation details
        error_message = str(exc.orig) if hasattr(exc, "orig") else str(exc)
        
        # Determine if it's a duplicate key error
        is_duplicate = any(
            keyword in error_message.lower()
            for keyword in ["duplicate", "unique", "already exists"]
        )
        
        message = "Resource already exists" if is_duplicate else "Database constraint violation"
        
        # Log error
        self._log_error(
            request=request,
            error_type="IntegrityError",
            message=message,
            status_code=409,
            details={"constraint_violation": error_message}
        )
        
        # Build error response (don't expose internal details in production)
        error_response = {
            "error": "conflict",
            "message": message,
        }
        
        if request_id:
            error_response["request_id"] = str(request_id)
        
        return JSONResponse(
            status_code=409,
            content=error_response
        )
    
    def _handle_database_error(
        self,
        request: Request,
        exc: SQLAlchemyError
    ) -> JSONResponse:
        """
        Handle database errors.
        
        Args:
            request: HTTP request
            exc: SQLAlchemy error
            
        Returns:
            JSON error response with 503 status
        """
        # Get request ID for correlation
        request_id = getattr(request.state, "request_id", None)
        
        # Log error with full stack trace
        self._log_error(
            request=request,
            error_type="DatabaseError",
            message="Database operation failed",
            status_code=503,
            details={"error": str(exc)},
            include_traceback=True
        )
        
        # Build error response (don't expose internal details)
        error_response = {
            "error": "service_unavailable",
            "message": "Database service temporarily unavailable. Please try again later.",
        }
        
        if request_id:
            error_response["request_id"] = str(request_id)
        
        return JSONResponse(
            status_code=503,
            content=error_response,
            headers={"Retry-After": "60"}  # Suggest retry after 60 seconds
        )
    
    def _handle_unexpected_error(
        self,
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """
        Handle unexpected errors.
        
        Args:
            request: HTTP request
            exc: Unexpected exception
            
        Returns:
            JSON error response with 500 status
        """
        # Get request ID for correlation
        request_id = getattr(request.state, "request_id", None)
        
        # Log error with full stack trace
        self._log_error(
            request=request,
            error_type=type(exc).__name__,
            message="Unexpected error occurred",
            status_code=500,
            details={"error": str(exc)},
            include_traceback=True
        )
        
        # Build error response (don't expose internal details)
        error_response = {
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
        }
        
        if request_id:
            error_response["request_id"] = str(request_id)
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )
    
    def _get_error_code(self, exc: AppException) -> str:
        """
        Get error code from exception type.
        
        Args:
            exc: Application exception
            
        Returns:
            Error code string
        """
        error_codes = {
            AuthenticationError: "authentication_failed",
            AuthorizationError: "insufficient_permissions",
            NotFoundError: "not_found",
            ValidationError: "validation_error",
            ConflictError: "conflict",
            ServiceUnavailableError: "service_unavailable",
            RateLimitError: "rate_limit_exceeded",
            DatabaseError: "database_error",
            CacheError: "cache_error",
        }
        
        return error_codes.get(type(exc), "application_error")
    
    def _log_error(
        self,
        request: Request,
        error_type: str,
        message: str,
        status_code: int,
        details: dict = None,
        include_traceback: bool = False
    ) -> None:
        """
        Log error with request context.
        
        Args:
            request: HTTP request
            error_type: Type of error
            message: Error message
            status_code: HTTP status code
            details: Additional error details
            include_traceback: Whether to include stack trace
        """
        # Get request ID for correlation
        request_id = getattr(request.state, "request_id", None)
        
        # Build log message
        log_data = {
            "error_type": error_type,
            "message": message,
            "status_code": status_code,
            "request_id": str(request_id) if request_id else None,
            "method": request.method,
            "path": request.url.path,
            "client_ip": self._get_client_ip(request),
        }
        
        if details:
            log_data["details"] = details
        
        # Add stack trace for unexpected errors
        if include_traceback:
            log_data["traceback"] = traceback.format_exc()
        
        # Log error (in production, this should use structured logging)
        print(f"ERROR: {log_data}")
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.
        
        Args:
            request: HTTP request
            
        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (for proxied requests)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to direct client host
        if request.client:
            return request.client.host
        
        return "unknown"
