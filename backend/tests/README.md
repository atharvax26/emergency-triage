# Test Suite Documentation

## Overview

This comprehensive test suite provides production-grade testing infrastructure for the Backend System Foundation. It includes unit tests, integration tests, property-based tests, and security tests with a target code coverage of ≥85%.

## Test Structure

```
tests/
├── conftest.py                      # Pytest configuration and fixtures
├── fixtures/
│   ├── __init__.py
│   └── sample_data.py              # Sample data generators
├── unit/                           # Unit tests
│   ├── test_auth_modules.py
│   ├── test_audit_service.py
│   ├── test_patient_validators.py
│   ├── test_queue_validators.py
│   └── ...
├── integration/                    # Integration tests
│   ├── test_api_auth.py           # Authentication endpoints
│   ├── test_api_patients.py       # Patient endpoints
│   ├── test_api_queue.py          # Queue endpoints
│   ├── test_api_security.py       # Security tests
│   ├── test_health_endpoints.py   # Health check endpoints
│   ├── test_cache_integration.py  # Cache integration
│   └── test_transactional_workflows.py
└── README.md                       # This file
```

## Fixtures

### Database Fixtures

- **`test_engine`**: Session-scoped test database engine with automatic table creation/cleanup
- **`db_session`**: Function-scoped database session with automatic rollback after each test

### Redis Fixtures

- **`mock_redis`**: Mock Redis client with in-memory cache simulation
- Supports common operations: get, set, setex, delete, exists, ping, incrby, expire, ttl

### RBAC Fixtures (Role-Based Access Control)

#### Role Fixtures
- **`nurse_role`**: Nurse role with patient intake permissions
- **`doctor_role`**: Doctor role with full queue access
- **`admin_role`**: Admin role with all permissions

#### User Fixtures
- **`nurse_user`**: Test nurse user with nurse role
- **`doctor_user`**: Test doctor user with doctor role
- **`admin_user`**: Test admin user with admin role

#### Authentication Fixtures
- **`nurse_token`**: JWT access token for nurse user
- **`doctor_token`**: JWT access token for doctor user
- **`admin_token`**: JWT access token for admin user
- **`nurse_auth_headers`**: Authorization headers for nurse
- **`doctor_auth_headers`**: Authorization headers for doctor
- **`admin_auth_headers`**: Authorization headers for admin

### Sample Data Fixtures

- **`sample_patient`**: Single patient record
- **`sample_patients`**: Multiple patient records (3 patients)
- **`sample_queue_entry`**: Single queue entry
- **`sample_queue_entries`**: Multiple queue entries with different priorities (5 entries)
- **`sample_assignment`**: Patient-doctor assignment

### Client Fixtures

- **`client`**: AsyncClient with database and Redis overrides for testing

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Security tests only
pytest -m security

# Property-based tests only
pytest -m property
```

### Run Specific Test Files
```bash
# Authentication tests
pytest tests/integration/test_api_auth.py

# Patient tests
pytest tests/integration/test_api_patients.py

# Queue tests
pytest tests/integration/test_api_queue.py

# Security tests
pytest tests/integration/test_api_security.py
```

### Run with Coverage
```bash
# Generate coverage report
pytest --cov=app --cov-report=term-missing --cov-report=html

# View HTML coverage report
# Open htmlcov/index.html in browser
```

### Run Specific Tests
```bash
# Run single test
pytest tests/integration/test_api_auth.py::TestAuthenticationEndpoints::test_login_success

# Run tests matching pattern
pytest -k "test_login"
```

## Test Prerequisites

### Database Setup

Tests require a PostgreSQL test database. The test suite automatically:
1. Creates a test database (`triage_test_db`)
2. Creates all tables before tests
3. Drops all tables after tests
4. Rolls back transactions after each test

**Database Configuration:**
- Test database URL is derived from `DATABASE_URL` in settings
- Replaces `triage_db` with `triage_test_db`
- Uses `postgresql+asyncpg://` for async operations

### Redis Setup

Tests use a mock Redis client by default, so no Redis server is required for most tests. For integration tests that require real Redis:
- Start Redis server: `redis-server`
- Or use Docker: `docker run -d -p 6379:6379 redis:7-alpine`

### Environment Variables

Create a `.env.test` file or use existing `.env.development`:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/triage_db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=test-secret-key-for-testing-only
ENVIRONMENT=dev
DEBUG=True
```

## Test Coverage Goals

- **Target Coverage**: ≥85%
- **Current Coverage**: Run `pytest --cov=app` to see current coverage
- **Coverage Reports**: 
  - Terminal: `--cov-report=term-missing`
  - HTML: `--cov-report=html` (opens in `htmlcov/index.html`)

### Coverage by Module

Priority areas for coverage:
1. **Core Business Logic**: 90%+ coverage
   - Authentication and authorization
   - Patient intake service
   - Queue engine
   - Audit engine

2. **API Endpoints**: 85%+ coverage
   - All REST endpoints
   - Request/response validation
   - Error handling

3. **Models and Schemas**: 95%+ coverage
   - Data validation
   - Model relationships
   - Schema serialization

4. **Utilities**: 80%+ coverage
   - Validators
   - Helpers
   - Exception handlers

## Writing New Tests

### Unit Test Example

```python
import pytest
from app.core.auth.password import hash_password, verify_password

@pytest.mark.unit
def test_password_hashing():
    """Test password hashing produces different hashes."""
    password = "SecurePass123!@#"
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    
    assert hash1 != hash2  # Different salts
    assert verify_password(password, hash1)
    assert verify_password(password, hash2)
```

### Integration Test Example

```python
import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_patient(
    client: AsyncClient,
    nurse_auth_headers: dict
):
    """Test creating a patient via API."""
    response = await client.post(
        "/api/v1/patients",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01",
            "gender": "male"
        },
        headers=nurse_auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "John"
    assert "mrn" in data
```

### Property-Based Test Example

```python
import pytest
from hypothesis import given, strategies as st
from app.core.auth.password import hash_password, verify_password

@pytest.mark.property
@given(st.text(min_size=12, max_size=128))
def test_password_verification_property(password):
    """Property: Any password can be verified against its hash."""
    password_hash = hash_password(password)
    assert verify_password(password, password_hash)
```

## Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit          # Unit test
@pytest.mark.integration   # Integration test
@pytest.mark.property      # Property-based test
@pytest.mark.security      # Security test
@pytest.mark.slow          # Slow-running test
@pytest.mark.asyncio       # Async test
```

## Continuous Integration

### CI Configuration

The test suite is designed for CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pytest --cov=app --cov-report=xml --cov-fail-under=85
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

### Pre-commit Hooks

Install pre-commit hooks to run tests before commits:

```bash
pre-commit install
```

## Troubleshooting

### Database Connection Errors

**Error**: `ConnectionRefusedError: [WinError 1225]`

**Solution**: 
1. Ensure PostgreSQL is running
2. Check database credentials in `.env`
3. Verify test database exists or can be created

### Redis Connection Errors

**Error**: `redis.exceptions.ConnectionError`

**Solution**:
1. Tests use mock Redis by default
2. For real Redis tests, ensure Redis is running
3. Check `REDIS_URL` in `.env`

### Import Errors

**Error**: `ImportError: cannot import name 'X'`

**Solution**:
1. Ensure all dependencies are installed: `pip install -r requirements-dev.txt`
2. Check Python path includes project root
3. Verify module structure matches imports

### Async Test Errors

**Error**: `RuntimeError: Event loop is closed`

**Solution**:
1. Use `@pytest.mark.asyncio` decorator
2. Ensure `pytest-asyncio` is installed
3. Check `asyncio_mode = auto` in `pytest.ini`

## Best Practices

1. **Test Isolation**: Each test should be independent and not rely on other tests
2. **Fixtures**: Use fixtures for common setup to avoid code duplication
3. **Descriptive Names**: Test names should clearly describe what is being tested
4. **Arrange-Act-Assert**: Follow AAA pattern for test structure
5. **Mock External Services**: Use mocks for external dependencies (Redis, external APIs)
6. **Test Edge Cases**: Include tests for boundary conditions and error cases
7. **Keep Tests Fast**: Unit tests should run in milliseconds, integration tests in seconds
8. **Clean Up**: Use fixtures with automatic cleanup to prevent test pollution

## Security Testing

Security tests verify:
- Authentication requirements
- Authorization enforcement
- SQL injection prevention
- XSS prevention
- Rate limiting
- CORS configuration
- Security headers
- Password handling
- Token validation

Run security tests:
```bash
pytest -m security -v
```

## Performance Testing

For performance testing:
1. Use `@pytest.mark.slow` for long-running tests
2. Exclude slow tests in CI: `pytest -m "not slow"`
3. Monitor test execution time: `pytest --durations=10`

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure tests pass: `pytest`
3. Check coverage: `pytest --cov=app`
4. Add integration tests for API endpoints
5. Add security tests for new permissions
6. Update this README if adding new test categories

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)
