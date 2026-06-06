"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.session import init_db, close_db
from app.cache.client import redis_client
from app.middleware.audit import AuditMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.auth import AuthenticationMiddleware
from app.middleware.authorization import AuthorizationMiddleware
from app.middleware.security import (
    SecurityHeadersMiddleware,
    SecureCookieMiddleware,
    HTTPSRedirectMiddleware
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Environment: {settings.ENVIRONMENT}")
    
    # Display configuration summary
    env_info = settings.get_environment_info()
    print("\n📋 Configuration Summary:")
    print(f"  Environment: {env_info['environment']}")
    print(f"  Debug Mode: {env_info['debug']}")
    print(f"  Security:")
    print(f"    - JWT Algorithm: {env_info['security']['jwt_algorithm']}")
    print(f"    - TLS Version: {env_info['security']['tls_min_version']}")
    print(f"    - HTTPS Enforced: {env_info['security']['enforce_https']}")
    print(f"    - Security Headers: {env_info['security']['security_headers_enabled']}")
    print(f"  Database Pool: {env_info['database']['pool_min_size']}-{env_info['database']['pool_size']} connections")
    print(f"  Rate Limiting: {env_info['rate_limiting']['per_minute']}/min per user")
    print(f"  Log Level: {env_info['logging']['level']}")
    
    # Initialize database
    try:
        await init_db()
        print("\n✓ Database connected")
    except Exception as e:
        print(f"\n✗ Database connection failed: {e}")
        raise
    
    # Initialize Redis
    try:
        await redis_client.connect()
        print("✓ Redis connected")
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        raise
    
    print(f"\n🚀 {settings.APP_NAME} is ready!\n")
    
    yield
    
    # Shutdown
    print("\nShutting down...")
    await close_db()
    await redis_client.disconnect()
    print("✓ Connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade backend infrastructure for Emergency Triage AI System",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Apply middleware stack in correct order (last added = first executed)
# Execution order: HTTPS Redirect -> CORS -> Security Headers -> Secure Cookies -> Error Handler -> Rate Limit -> Auth -> Authorization -> Audit

# 1. Audit logging (innermost - executes last)
app.add_middleware(AuditMiddleware)

# 2. Authorization (RBAC permission checking)
app.add_middleware(AuthorizationMiddleware)

# 3. Authentication (JWT validation)
app.add_middleware(AuthenticationMiddleware)

# 4. Rate limiting (per user/IP)
app.add_middleware(RateLimitMiddleware)

# 5. Error handler (catches all exceptions)
app.add_middleware(ErrorHandlerMiddleware)

# 6. Secure cookies (ensure all cookies have secure flags)
app.add_middleware(SecureCookieMiddleware, enforce_https=settings.should_enforce_https)

# 7. Security headers (CSP, HSTS, X-Frame-Options, etc.)
if settings.ENABLE_SECURITY_HEADERS:
    app.add_middleware(SecurityHeadersMiddleware, enforce_https=settings.should_enforce_https)

# 8. CORS (outermost - executes first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# 9. HTTPS redirect (only in production or when explicitly enabled)
if settings.should_enforce_https:
    app.add_middleware(HTTPSRedirectMiddleware, enabled=True)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running"
    }


# Register API routers
from app.api.v1 import auth, users, patients, queue, audit, ml
from app.api import health

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(patients.router, prefix="/api/v1")
app.include_router(queue.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(ml.router, prefix="/api/v1")
app.include_router(health.router)
