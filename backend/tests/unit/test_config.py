"""Unit tests for configuration management."""

import pytest
from pydantic import ValidationError
from app.config import Settings


class TestSettingsValidation:
    """Test configuration validation."""

    def test_default_settings_valid(self):
        """Test that default settings are valid."""
        settings = Settings()
        assert settings.ENVIRONMENT == "dev"
        assert settings.DEBUG is True
        assert settings.APP_NAME == "Backend System Foundation"

    def test_environment_validation(self):
        """Test environment value validation."""
        # Valid environments
        for env in ["dev", "staging"]:
            settings = Settings(ENVIRONMENT=env)
            assert settings.ENVIRONMENT == env
        
        # Production environment (needs additional settings)
        settings = Settings(
            ENVIRONMENT="prod",
            DEBUG=False,
            ENFORCE_HTTPS=True,
            JWT_SECRET_KEY="a" * 32,
            JWT_ALGORITHM="RS256",
            TLS_MIN_VERSION="TLSv1.3",
            CORS_ORIGINS=["https://example.com"]
        )
        assert settings.ENVIRONMENT == "prod"

        # Invalid environment
        with pytest.raises(ValidationError) as exc_info:
            Settings(ENVIRONMENT="invalid")
        assert "pattern" in str(exc_info.value).lower() or "ENVIRONMENT must be one of" in str(exc_info.value)

    def test_database_url_validation(self):
        """Test database URL format validation."""
        # Valid URLs
        valid_urls = [
            "postgresql://user:pass@localhost:5432/db",
            "postgresql+asyncpg://user:pass@localhost:5432/db",
        ]
        for url in valid_urls:
            settings = Settings(DATABASE_URL=url)
            assert settings.DATABASE_URL == url

        # Invalid URL
        with pytest.raises(ValidationError) as exc_info:
            Settings(DATABASE_URL="mysql://localhost/db")
        assert "must start with 'postgresql://'" in str(exc_info.value)

    def test_redis_url_validation(self):
        """Test Redis URL format validation."""
        # Valid URLs
        valid_urls = [
            "redis://localhost:6379/0",
            "rediss://localhost:6379/0",
        ]
        for url in valid_urls:
            settings = Settings(REDIS_URL=url)
            assert settings.REDIS_URL == url

        # Invalid URL
        with pytest.raises(ValidationError) as exc_info:
            Settings(REDIS_URL="memcached://localhost:11211")
        assert "must start with 'redis://'" in str(exc_info.value)

    def test_pool_size_validation(self):
        """Test database pool size validation."""
        # Valid pool sizes
        settings = Settings(DB_POOL_SIZE=20, DB_POOL_MIN_SIZE=5)
        assert settings.DB_POOL_SIZE == 20
        assert settings.DB_POOL_MIN_SIZE == 5

        # Invalid: min > max
        with pytest.raises(ValidationError) as exc_info:
            Settings(DB_POOL_SIZE=10, DB_POOL_MIN_SIZE=20)
        assert "must be less than or equal to" in str(exc_info.value)

    def test_production_jwt_secret_validation(self):
        """Test JWT secret validation in production."""
        # Production with default secret should fail
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="prod",
                DEBUG=False,
                ENFORCE_HTTPS=True,
                JWT_SECRET_KEY="your-secret-key-change-in-production"
            )
        assert "must be changed from default" in str(exc_info.value)

        # Production with short secret should fail
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="prod",
                DEBUG=False,
                ENFORCE_HTTPS=True,
                JWT_SECRET_KEY="short"
            )
        assert "at least 32 characters" in str(exc_info.value)

        # Production with strong secret should pass
        settings = Settings(
            ENVIRONMENT="prod",
            DEBUG=False,
            ENFORCE_HTTPS=True,
            JWT_SECRET_KEY="a" * 32,
            JWT_ALGORITHM="RS256",
            TLS_MIN_VERSION="TLSv1.3",
            CORS_ORIGINS=["https://example.com"]
        )
        assert len(settings.JWT_SECRET_KEY) >= 32

    def test_production_cors_validation(self):
        """Test CORS validation in production."""
        # Production with wildcard should fail
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="prod",
                DEBUG=False,
                ENFORCE_HTTPS=True,
                JWT_SECRET_KEY="a" * 32,
                JWT_ALGORITHM="RS256",
                TLS_MIN_VERSION="TLSv1.3",
                CORS_ORIGINS=["*"]
            )
        assert "cannot contain wildcard" in str(exc_info.value)

        # Production with HTTP origin (non-localhost) should fail
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="prod",
                DEBUG=False,
                ENFORCE_HTTPS=True,
                JWT_SECRET_KEY="a" * 32,
                JWT_ALGORITHM="RS256",
                TLS_MIN_VERSION="TLSv1.3",
                CORS_ORIGINS=["http://example.com"]
            )
        assert "must use HTTPS" in str(exc_info.value)

        # Production with HTTPS origins should pass
        settings = Settings(
            ENVIRONMENT="prod",
            DEBUG=False,
            ENFORCE_HTTPS=True,
            JWT_SECRET_KEY="a" * 32,
            JWT_ALGORITHM="RS256",
            TLS_MIN_VERSION="TLSv1.3",
            CORS_ORIGINS=["https://example.com", "http://localhost:3000"]
        )
        assert "https://example.com" in settings.CORS_ORIGINS

    def test_production_settings_validation(self):
        """Test production-specific settings validation."""
        # Production with DEBUG=True should fail
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="prod",
                DEBUG=True,
                JWT_SECRET_KEY="a" * 32,
                JWT_ALGORITHM="RS256",
                TLS_MIN_VERSION="TLSv1.3",
                CORS_ORIGINS=["https://example.com"]
            )
        assert "DEBUG must be False in production" in str(exc_info.value)

        # Production without HTTPS enforcement should fail
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="prod",
                DEBUG=False,
                ENFORCE_HTTPS=False,
                JWT_SECRET_KEY="a" * 32,
                JWT_ALGORITHM="RS256",
                TLS_MIN_VERSION="TLSv1.3",
                CORS_ORIGINS=["https://example.com"]
            )
        assert "ENFORCE_HTTPS must be True in production" in str(exc_info.value)

        # Production with DB_ECHO=True should fail
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="prod",
                DEBUG=False,
                ENFORCE_HTTPS=True,
                DB_ECHO=True,
                JWT_SECRET_KEY="a" * 32,
                JWT_ALGORITHM="RS256",
                TLS_MIN_VERSION="TLSv1.3",
                CORS_ORIGINS=["https://example.com"]
            )
        assert "DB_ECHO must be False in production" in str(exc_info.value)

        # Production with DEBUG log level should fail
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="prod",
                DEBUG=False,
                ENFORCE_HTTPS=True,
                LOG_LEVEL="DEBUG",
                JWT_SECRET_KEY="a" * 32,
                JWT_ALGORITHM="RS256",
                TLS_MIN_VERSION="TLSv1.3",
                CORS_ORIGINS=["https://example.com"]
            )
        assert "LOG_LEVEL should not be DEBUG in production" in str(exc_info.value)


class TestSettingsProperties:
    """Test configuration properties."""

    def test_is_production(self):
        """Test is_production property."""
        assert Settings(ENVIRONMENT="prod", DEBUG=False, ENFORCE_HTTPS=True, 
                       JWT_SECRET_KEY="a"*32, JWT_ALGORITHM="RS256", 
                       TLS_MIN_VERSION="TLSv1.3", 
                       CORS_ORIGINS=["https://example.com"]).is_production
        assert not Settings(ENVIRONMENT="dev").is_production
        assert not Settings(ENVIRONMENT="staging").is_production

    def test_is_development(self):
        """Test is_development property."""
        assert Settings(ENVIRONMENT="dev").is_development
        assert not Settings(ENVIRONMENT="staging").is_development
        assert not Settings(ENVIRONMENT="prod", DEBUG=False, ENFORCE_HTTPS=True,
                           JWT_SECRET_KEY="a"*32, JWT_ALGORITHM="RS256",
                           TLS_MIN_VERSION="TLSv1.3",
                           CORS_ORIGINS=["https://example.com"]).is_development

    def test_is_staging(self):
        """Test is_staging property."""
        assert Settings(ENVIRONMENT="staging").is_staging
        assert not Settings(ENVIRONMENT="dev").is_staging
        assert not Settings(ENVIRONMENT="prod", DEBUG=False, ENFORCE_HTTPS=True,
                           JWT_SECRET_KEY="a"*32, JWT_ALGORITHM="RS256",
                           TLS_MIN_VERSION="TLSv1.3",
                           CORS_ORIGINS=["https://example.com"]).is_staging

    def test_should_enforce_https(self):
        """Test should_enforce_https property."""
        # Production should enforce HTTPS
        prod_settings = Settings(
            ENVIRONMENT="prod",
            DEBUG=False,
            ENFORCE_HTTPS=True,
            JWT_SECRET_KEY="a" * 32,
            JWT_ALGORITHM="RS256",
            TLS_MIN_VERSION="TLSv1.3",
            CORS_ORIGINS=["https://example.com"]
        )
        assert prod_settings.should_enforce_https

        # Development with explicit HTTPS enforcement
        dev_settings = Settings(ENVIRONMENT="dev", ENFORCE_HTTPS=True)
        assert dev_settings.should_enforce_https

        # Development without HTTPS enforcement
        dev_settings_no_https = Settings(ENVIRONMENT="dev", ENFORCE_HTTPS=False)
        assert not dev_settings_no_https.should_enforce_https


class TestStartupValidation:
    """Test startup validation."""

    def test_validate_on_startup_success(self):
        """Test successful startup validation."""
        settings = Settings(ENVIRONMENT="dev")
        # Should not raise any exception
        settings.validate_on_startup()

    def test_validate_on_startup_invalid_jwt_algorithm(self):
        """Test startup validation with invalid JWT algorithm."""
        settings = Settings(ENVIRONMENT="dev", JWT_ALGORITHM="HS512")
        with pytest.raises(ValueError) as exc_info:
            settings.validate_on_startup()
        assert "JWT_ALGORITHM must be RS256 or HS256" in str(exc_info.value)

    def test_validate_on_startup_invalid_tls_version(self):
        """Test startup validation with invalid TLS version."""
        settings = Settings(ENVIRONMENT="dev", TLS_MIN_VERSION="TLSv1.1")
        with pytest.raises(ValueError) as exc_info:
            settings.validate_on_startup()
        assert "TLS_MIN_VERSION must be TLSv1.2 or TLSv1.3" in str(exc_info.value)

    def test_validate_on_startup_production_tls_requirement(self):
        """Test startup validation enforces TLS 1.3 in production."""
        settings = Settings(
            ENVIRONMENT="prod",
            DEBUG=False,
            ENFORCE_HTTPS=True,
            TLS_MIN_VERSION="TLSv1.2",
            JWT_SECRET_KEY="a" * 32,
            JWT_ALGORITHM="RS256",
            CORS_ORIGINS=["https://example.com"]
        )
        with pytest.raises(ValueError) as exc_info:
            settings.validate_on_startup()
        assert "TLS_MIN_VERSION must be TLSv1.3 in production" in str(exc_info.value)
        assert "Requirement 14.2" in str(exc_info.value)

    def test_validate_on_startup_production_jwt_requirement(self):
        """Test startup validation enforces RS256 in production."""
        settings = Settings(
            ENVIRONMENT="prod",
            DEBUG=False,
            ENFORCE_HTTPS=True,
            TLS_MIN_VERSION="TLSv1.3",
            JWT_SECRET_KEY="a" * 32,
            JWT_ALGORITHM="HS256",
            CORS_ORIGINS=["https://example.com"]
        )
        with pytest.raises(ValueError) as exc_info:
            settings.validate_on_startup()
        assert "JWT_ALGORITHM must be RS256 in production" in str(exc_info.value)
        assert "Requirement 14.3" in str(exc_info.value)

    def test_validate_on_startup_cache_ttl(self):
        """Test startup validation for cache TTL."""
        # This should fail at Pydantic field validation level, not startup validation
        # CACHE_TTL_SESSION has ge=60 constraint
        with pytest.raises(ValidationError) as exc_info:
            Settings(ENVIRONMENT="dev", CACHE_TTL_SESSION=30)
        assert "greater than or equal to 60" in str(exc_info.value)

    def test_validate_on_startup_pagination(self):
        """Test startup validation for pagination."""
        # This should fail at Pydantic field validation level, not startup validation
        # DEFAULT_PAGE_SIZE has le=100 constraint
        with pytest.raises(ValidationError) as exc_info:
            Settings(ENVIRONMENT="dev", DEFAULT_PAGE_SIZE=200, MAX_PAGE_SIZE=100)
        assert "less than or equal to 100" in str(exc_info.value)


class TestEnvironmentInfo:
    """Test environment info retrieval."""

    def test_get_environment_info(self):
        """Test get_environment_info returns correct structure."""
        settings = Settings(ENVIRONMENT="dev")
        info = settings.get_environment_info()

        # Check structure
        assert "app_name" in info
        assert "version" in info
        assert "environment" in info
        assert "debug" in info
        assert "database" in info
        assert "redis" in info
        assert "security" in info
        assert "tokens" in info
        assert "rate_limiting" in info
        assert "logging" in info

        # Check values
        assert info["environment"] == "dev"
        assert info["app_name"] == "Backend System Foundation"
        assert isinstance(info["debug"], bool)
        assert isinstance(info["database"]["pool_size"], int)
        assert isinstance(info["security"]["jwt_algorithm"], str)

    def test_get_environment_info_no_secrets(self):
        """Test that environment info doesn't expose secrets."""
        settings = Settings(
            ENVIRONMENT="dev",
            JWT_SECRET_KEY="super-secret-key",
            DATABASE_URL="postgresql://user:password@localhost/db"
        )
        info = settings.get_environment_info()

        # Ensure secrets are not in the info
        info_str = str(info)
        assert "super-secret-key" not in info_str
        assert "password" not in info_str
