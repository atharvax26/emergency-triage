"""Custom exception classes for the application."""

from typing import Any, Optional


class AppException(Exception):
    """Base exception class for application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None
    ):
        """
        Initialize application exception.
        
        Args:
            message: Error message
            status_code: HTTP status code
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppException):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed", details: Optional[dict] = None):
        super().__init__(message, status_code=401, details=details)


class AuthorizationError(AppException):
    """Authorization failed - insufficient permissions."""

    def __init__(self, message: str = "Insufficient permissions", details: Optional[dict] = None):
        super().__init__(message, status_code=403, details=details)


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found", details: Optional[dict] = None):
        super().__init__(message, status_code=404, details=details)


class ValidationError(AppException):
    """Data validation failed."""

    def __init__(self, message: str = "Validation failed", details: Optional[dict] = None):
        super().__init__(message, status_code=422, details=details)


class ConflictError(AppException):
    """Resource conflict - duplicate or constraint violation."""

    def __init__(self, message: str = "Resource conflict", details: Optional[dict] = None):
        super().__init__(message, status_code=409, details=details)


class ServiceUnavailableError(AppException):
    """Service temporarily unavailable."""

    def __init__(self, message: str = "Service unavailable", details: Optional[dict] = None):
        super().__init__(message, status_code=503, details=details)


class RateLimitError(AppException):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[dict] = None
    ):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, status_code=429, details=details)


class AccountLockedError(AuthenticationError):
    """Account is locked due to too many failed login attempts."""

    def __init__(
        self,
        message: str = "Account locked due to too many failed login attempts",
        lockout_minutes: Optional[int] = None,
        details: Optional[dict] = None
    ):
        details = details or {}
        if lockout_minutes:
            details["lockout_minutes"] = lockout_minutes
        super().__init__(message, details=details)


class TokenExpiredError(AuthenticationError):
    """JWT token has expired."""

    def __init__(self, message: str = "Token has expired", details: Optional[dict] = None):
        super().__init__(message, details=details)


class TokenRevokedError(AuthenticationError):
    """JWT token has been revoked."""

    def __init__(self, message: str = "Token has been revoked", details: Optional[dict] = None):
        super().__init__(message, details=details)


class InvalidTokenError(AuthenticationError):
    """JWT token is invalid."""

    def __init__(self, message: str = "Invalid token", details: Optional[dict] = None):
        super().__init__(message, details=details)


class DatabaseError(ServiceUnavailableError):
    """Database operation failed."""

    def __init__(self, message: str = "Database error", details: Optional[dict] = None):
        super().__init__(message, details=details)


class CacheError(AppException):
    """Cache operation failed (non-critical)."""

    def __init__(self, message: str = "Cache error", details: Optional[dict] = None):
        # Cache errors are warnings, not failures
        super().__init__(message, status_code=200, details=details)


class PasswordComplexityError(ValidationError):
    """Password does not meet complexity requirements."""

    def __init__(
        self,
        message: str = "Password does not meet complexity requirements",
        details: Optional[dict] = None
    ):
        super().__init__(message, details=details)
