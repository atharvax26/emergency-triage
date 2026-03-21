"""Security hardening middleware for production-grade security."""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Implements:
    - Content-Security-Policy (CSP)
    - HTTP Strict Transport Security (HSTS)
    - X-Frame-Options
    - X-Content-Type-Options
    - Referrer-Policy
    - X-XSS-Protection (legacy browsers)
    - Permissions-Policy
    """
    
    def __init__(self, app: ASGIApp, enforce_https: bool = True):
        super().__init__(app)
        self.enforce_https = enforce_https
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Content-Security-Policy: Prevent XSS attacks
        # Strict policy: only allow resources from same origin
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "  # Allow inline styles for API docs
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        
        # HTTP Strict Transport Security: Force HTTPS for 1 year
        if self.enforce_https:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # X-Frame-Options: Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options: Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Referrer-Policy: Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # X-XSS-Protection: Enable XSS filter (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Permissions-Policy: Disable unnecessary browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        # Remove server header to avoid information disclosure
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


class SecureCookieMiddleware(BaseHTTPMiddleware):
    """
    Middleware to ensure all cookies are set with secure flags.
    
    Implements:
    - Secure flag (HTTPS only)
    - HttpOnly flag (no JavaScript access)
    - SameSite flag (CSRF protection)
    """
    
    def __init__(self, app: ASGIApp, enforce_https: bool = True):
        super().__init__(app)
        self.enforce_https = enforce_https
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Ensure cookies have secure flags."""
        response = await call_next(request)
        
        # Process Set-Cookie headers
        if "set-cookie" in response.headers:
            cookies = response.headers.getlist("set-cookie")
            response.headers.pop("set-cookie")
            
            for cookie in cookies:
                # Add secure flags if not present
                if self.enforce_https and "Secure" not in cookie:
                    cookie += "; Secure"
                
                if "HttpOnly" not in cookie:
                    cookie += "; HttpOnly"
                
                if "SameSite" not in cookie:
                    cookie += "; SameSite=Strict"
                
                response.headers.append("set-cookie", cookie)
        
        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect HTTP requests to HTTPS.
    
    Only active in production environments.
    """
    
    def __init__(self, app: ASGIApp, enabled: bool = False):
        super().__init__(app)
        self.enabled = enabled
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Redirect HTTP to HTTPS if enabled."""
        if self.enabled and request.url.scheme == "http":
            # Redirect to HTTPS
            https_url = request.url.replace(scheme="https")
            return Response(
                status_code=301,
                headers={"Location": str(https_url)}
            )
        
        return await call_next(request)
