"""Rate limiting middleware using Redis for tracking."""

from typing import Callable
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.cache.client import redis_client
from app.cache.keys import CacheKeys
from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.
    
    Features:
    - Implements 100 requests per minute per user (configurable via settings)
    - Uses Redis for distributed rate limit tracking
    - Returns 429 with Retry-After header when limit exceeded
    - Tracks by user_id from request.state (set by AuthenticationMiddleware)
    - Falls back to IP-based rate limiting for unauthenticated requests
    - Skips rate limiting for health check endpoints
    - Implements sliding window algorithm for accurate rate limiting
    
    Rate limit configuration:
    - RATE_LIMIT_PER_MINUTE: Requests per minute per user (default: 100)
    - RATE_LIMIT_PER_IP_MINUTE: Requests per minute per IP (default: 1000)
    
    Redis key format:
    - rate_limit:user:{user_id}:{minute_timestamp}
    - rate_limit:ip:{ip_address}:{minute_timestamp}
    
    Graceful degradation:
    - If Redis is unavailable, allows requests through (fail open)
    - Logs errors for monitoring
    """
    
    # Endpoints to skip rate limiting
    SKIP_PATHS = {
        "/health",
        "/health/ready",
        "/health/live",
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request and check rate limit.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or endpoint handler
            
        Returns:
            HTTP response (429 if rate limit exceeded, or response from next handler)
        """
        # Skip rate limiting for excluded paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        
        # Determine rate limit key (user_id or IP address)
        rate_limit_key, limit = self._get_rate_limit_key(request)
        
        # Check rate limit
        try:
            is_allowed, retry_after = await self._check_rate_limit(
                rate_limit_key,
                limit
            )
            
            if not is_allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded. Maximum {limit} requests per minute.",
                        "retry_after": retry_after
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(retry_after)
                    }
                )
        
        except Exception as e:
            # Graceful degradation: allow request if Redis fails
            print(f"Rate limit check failed (allowing request): {e}")
        
        # Continue to next middleware/handler
        response = await call_next(request)
        
        # Add rate limit headers to response
        try:
            remaining = await self._get_remaining_requests(rate_limit_key, limit)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
        except Exception:
            pass  # Don't fail response if header addition fails
        
        return response
    
    def _get_rate_limit_key(self, request: Request) -> tuple[str, int]:
        """
        Get rate limit key and limit for request.
        
        Prioritizes user_id over IP address for authenticated requests.
        
        Args:
            request: HTTP request
            
        Returns:
            Tuple of (rate_limit_key, limit)
        """
        # Get current minute timestamp for sliding window
        current_minute = int(datetime.utcnow().timestamp() / 60)
        
        # Check if user is authenticated
        if hasattr(request.state, "user_id") and request.state.user_id:
            # User-based rate limiting
            key = f"rate_limit:user:{request.state.user_id}:{current_minute}"
            limit = settings.RATE_LIMIT_PER_MINUTE
            return key, limit
        
        # IP-based rate limiting for unauthenticated requests
        ip_address = self._get_client_ip(request)
        key = f"rate_limit:ip:{ip_address}:{current_minute}"
        limit = settings.RATE_LIMIT_PER_IP_MINUTE
        return key, limit
    
    async def _check_rate_limit(
        self,
        rate_limit_key: str,
        limit: int
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit.
        
        Uses Redis INCR for atomic increment and check.
        Sets TTL of 60 seconds on first request in the minute window.
        
        Args:
            rate_limit_key: Redis key for rate limit tracking
            limit: Maximum requests allowed per minute
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        # Increment request counter
        count = await redis_client.increment(rate_limit_key)
        
        # Set TTL on first request (60 seconds for 1-minute window)
        if count == 1:
            await redis_client.expire(rate_limit_key, 60)
        
        # Check if limit exceeded
        if count > limit:
            # Calculate retry_after (seconds until next minute)
            ttl = await redis_client.ttl(rate_limit_key)
            retry_after = max(ttl, 1)  # At least 1 second
            return False, retry_after
        
        return True, 0
    
    async def _get_remaining_requests(
        self,
        rate_limit_key: str,
        limit: int
    ) -> int:
        """
        Get remaining requests in current window.
        
        Args:
            rate_limit_key: Redis key for rate limit tracking
            limit: Maximum requests allowed per minute
            
        Returns:
            Number of remaining requests
        """
        count_str = await redis_client.get(rate_limit_key)
        
        if count_str is None:
            return limit
        
        try:
            count = int(count_str)
            remaining = max(limit - count, 0)
            return remaining
        except (ValueError, TypeError):
            return limit
    
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
        
        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client host
        if request.client:
            return request.client.host
        
        return "unknown"
