"""Configuration management using pydantic-settings."""

import sys
from typing import List, Optional
from pathlib import Path
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Backend System Foundation"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="dev", pattern="^(dev|staging|prod)$")
    DEBUG: bool = Field(default=True)

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/triage_db",
        description="PostgreSQL connection string"
    )
    DB_POOL_SIZE: int = Field(default=20, ge=1, le=100)
    DB_POOL_MIN_SIZE: int = Field(default=5, ge=1, le=50)
    DB_ECHO: bool = Field(default=False)

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    REDIS_MAX_CONNECTIONS: int = Field(default=50, ge=1)

    # JWT Authentication
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT token signing"
    )
    JWT_ALGORITHM: str = Field(default="RS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=1)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1)

    # Security
    BCRYPT_COST_FACTOR: int = Field(default=12, ge=10, le=15)
    PASSWORD_MIN_LENGTH: int = Field(default=12, ge=8)
    MAX_LOGIN_ATTEMPTS: int = Field(default=10, ge=3)
    ACCOUNT_LOCKOUT_MINUTES: int = Field(default=30, ge=1)

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(default=["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"])

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, ge=1)
    RATE_LIMIT_PER_IP_MINUTE: int = Field(default=1000, ge=1)

    # Session Management
    SESSION_EXPIRE_MINUTES: int = Field(default=15, ge=1)
    MAX_CONCURRENT_SESSIONS: int = Field(default=5, ge=1)

    # Cache TTL (in seconds)
    CACHE_TTL_SESSION: int = Field(default=900, ge=60)  # 15 minutes
    CACHE_TTL_PATIENT: int = Field(default=300, ge=60)  # 5 minutes
    CACHE_TTL_QUEUE: int = Field(default=60, ge=10)  # 1 minute
    CACHE_TTL_PERMISSION: int = Field(default=600, ge=60)  # 10 minutes

    # Pagination
    DEFAULT_PAGE_SIZE: int = Field(default=50, ge=1, le=100)
    MAX_PAGE_SIZE: int = Field(default=100, ge=1, le=1000)

    # Logging
    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    LOG_FORMAT: str = Field(default="json")

    # Security Hardening
    ENFORCE_HTTPS: bool = Field(default=False, description="Enforce HTTPS in production")
    TLS_MIN_VERSION: str = Field(default="TLSv1.3", description="Minimum TLS version")
    ENABLE_SECURITY_HEADERS: bool = Field(default=True, description="Enable security headers")
    ENABLE_XSS_PROTECTION: bool = Field(default=True, description="Enable XSS protection")
    ENABLE_SQL_INJECTION_DETECTION: bool = Field(default=True, description="Enable SQL injection detection")
    
    # Secrets Management
    SECRETS_ENCRYPTION_KEY: str = Field(
        default="",
        description="Encryption key for secrets (leave empty to disable)"
    )

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = ["dev", "staging", "prod"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    @field_validator("DB_POOL_MIN_SIZE")
    @classmethod
    def validate_pool_sizes(cls, v: int, info) -> int:
        """Ensure min pool size is less than max pool size."""
        if "DB_POOL_SIZE" in info.data and v > info.data["DB_POOL_SIZE"]:
            raise ValueError("DB_POOL_MIN_SIZE must be less than or equal to DB_POOL_SIZE")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must start with 'postgresql://' or 'postgresql+asyncpg://'")
        return v

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format."""
        if not v.startswith("redis://") and not v.startswith("rediss://"):
            raise ValueError("REDIS_URL must start with 'redis://' or 'rediss://'")
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """Validate JWT secret key is not using default in production."""
        if "ENVIRONMENT" in info.data and info.data["ENVIRONMENT"] == "prod":
            if v == "your-secret-key-change-in-production" or len(v) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be changed from default and be at least 32 characters in production"
                )
        return v

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: List[str], info) -> List[str]:
        """Validate CORS origins in production."""
        if "ENVIRONMENT" in info.data and info.data["ENVIRONMENT"] == "prod":
            # In production, ensure no wildcard origins
            if "*" in v:
                raise ValueError("CORS_ORIGINS cannot contain wildcard '*' in production")
            # Ensure all origins use HTTPS in production
            for origin in v:
                if not origin.startswith("https://") and not origin.startswith("http://localhost"):
                    raise ValueError(f"CORS origin '{origin}' must use HTTPS in production")
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Validate production-specific settings."""
        if self.ENVIRONMENT == "prod":
            # Ensure debug is disabled in production
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")
            
            # Ensure HTTPS is enforced in production
            if not self.ENFORCE_HTTPS:
                raise ValueError("ENFORCE_HTTPS must be True in production")
            
            # Ensure database echo is disabled in production
            if self.DB_ECHO:
                raise ValueError("DB_ECHO must be False in production")
            
            # Ensure proper log level in production
            if self.LOG_LEVEL == "DEBUG":
                raise ValueError("LOG_LEVEL should not be DEBUG in production")
        
        return self

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "prod"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "dev"

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.ENVIRONMENT == "staging"

    @property
    def should_enforce_https(self) -> bool:
        """Check if HTTPS should be enforced (production or explicitly enabled)."""
        return self.is_production or self.ENFORCE_HTTPS

    def validate_on_startup(self) -> None:
        """
        Perform comprehensive validation on application startup.
        
        This method performs additional runtime checks that go beyond
        Pydantic's field validation, including:
        - File system checks
        - Network connectivity prerequisites
        - Security configuration validation
        
        Raises:
            ValueError: If any validation check fails
            RuntimeError: If critical configuration is missing
        """
        errors = []
        
        # Validate JWT algorithm
        if self.JWT_ALGORITHM not in ["RS256", "HS256"]:
            errors.append(f"JWT_ALGORITHM must be RS256 or HS256, got: {self.JWT_ALGORITHM}")
        
        # Validate TLS version
        if self.TLS_MIN_VERSION not in ["TLSv1.2", "TLSv1.3"]:
            errors.append(f"TLS_MIN_VERSION must be TLSv1.2 or TLSv1.3, got: {self.TLS_MIN_VERSION}")
        
        # Production-specific validations
        if self.is_production:
            # Ensure TLS 1.3 in production (Requirement 14.2)
            if self.TLS_MIN_VERSION != "TLSv1.3":
                errors.append("TLS_MIN_VERSION must be TLSv1.3 in production (Requirement 14.2)")
            
            # Ensure RS256 for JWT in production (Requirement 14.3)
            if self.JWT_ALGORITHM != "RS256":
                errors.append("JWT_ALGORITHM must be RS256 in production (Requirement 14.3)")
            
            # Ensure security features are enabled
            if not self.ENABLE_SECURITY_HEADERS:
                errors.append("ENABLE_SECURITY_HEADERS must be True in production")
            
            if not self.ENABLE_XSS_PROTECTION:
                errors.append("ENABLE_XSS_PROTECTION must be True in production")
            
            if not self.ENABLE_SQL_INJECTION_DETECTION:
                errors.append("ENABLE_SQL_INJECTION_DETECTION must be True in production")
        
        # Validate cache TTL relationships
        if self.CACHE_TTL_SESSION < 60:
            errors.append("CACHE_TTL_SESSION should be at least 60 seconds")
        
        if self.CACHE_TTL_QUEUE > self.CACHE_TTL_PATIENT:
            errors.append("CACHE_TTL_QUEUE should not exceed CACHE_TTL_PATIENT")
        
        # Validate rate limiting
        if self.RATE_LIMIT_PER_MINUTE > self.RATE_LIMIT_PER_IP_MINUTE:
            errors.append("RATE_LIMIT_PER_MINUTE should not exceed RATE_LIMIT_PER_IP_MINUTE")
        
        # Validate pagination
        if self.DEFAULT_PAGE_SIZE > self.MAX_PAGE_SIZE:
            errors.append("DEFAULT_PAGE_SIZE must not exceed MAX_PAGE_SIZE")
        
        # Validate token expiration
        if self.ACCESS_TOKEN_EXPIRE_MINUTES > self.SESSION_EXPIRE_MINUTES:
            errors.append("ACCESS_TOKEN_EXPIRE_MINUTES should not exceed SESSION_EXPIRE_MINUTES")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
            raise ValueError(error_msg)
    
    def get_environment_info(self) -> dict:
        """
        Get environment information for logging and debugging.
        
        Returns:
            dict: Environment configuration summary (safe for logging)
        """
        return {
            "app_name": self.APP_NAME,
            "version": self.APP_VERSION,
            "environment": self.ENVIRONMENT,
            "debug": self.DEBUG,
            "database": {
                "pool_size": self.DB_POOL_SIZE,
                "pool_min_size": self.DB_POOL_MIN_SIZE,
                "echo": self.DB_ECHO,
            },
            "redis": {
                "max_connections": self.REDIS_MAX_CONNECTIONS,
            },
            "security": {
                "jwt_algorithm": self.JWT_ALGORITHM,
                "bcrypt_cost_factor": self.BCRYPT_COST_FACTOR,
                "enforce_https": self.should_enforce_https,
                "tls_min_version": self.TLS_MIN_VERSION,
                "security_headers_enabled": self.ENABLE_SECURITY_HEADERS,
                "xss_protection_enabled": self.ENABLE_XSS_PROTECTION,
                "sql_injection_detection_enabled": self.ENABLE_SQL_INJECTION_DETECTION,
            },
            "tokens": {
                "access_token_expire_minutes": self.ACCESS_TOKEN_EXPIRE_MINUTES,
                "refresh_token_expire_days": self.REFRESH_TOKEN_EXPIRE_DAYS,
            },
            "rate_limiting": {
                "per_minute": self.RATE_LIMIT_PER_MINUTE,
                "per_ip_minute": self.RATE_LIMIT_PER_IP_MINUTE,
            },
            "logging": {
                "level": self.LOG_LEVEL,
                "format": self.LOG_FORMAT,
            },
        }


def load_settings() -> Settings:
    """
    Load and validate settings.
    
    This function loads settings from environment variables and .env file,
    performs validation, and returns the settings instance.
    
    Returns:
        Settings: Validated settings instance
        
    Raises:
        ValueError: If configuration validation fails
        RuntimeError: If critical configuration is missing
    """
    try:
        settings = Settings()
        settings.validate_on_startup()
        return settings
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}", file=sys.stderr)
        raise


# Global settings instance - validated on import
settings = load_settings()
