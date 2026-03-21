"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator, Generator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient

from app.main import app
from app.database.base import Base
from app.config import settings
from app.dependencies import get_db_session, get_redis
from app.models.user import User, Role, Permission
from app.models.patient import Patient
from app.models.queue import QueueEntry, Assignment
from app.core.auth.password import hash_password
from app.core.auth.jwt import generate_access_token
from tests.fixtures.sample_data import (
    sample_user_data,
    sample_patient_data,
    sample_queue_entry_data,
    SAMPLE_PATIENTS
)


# Test database URL
TEST_DATABASE_URL = settings.DATABASE_URL.replace("triage_db", "triage_test_db")
TEST_ASYNC_DATABASE_URL = TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_ASYNC_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests with automatic rollback."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        # Start a transaction
        async with session.begin():
            yield session
            # Rollback happens automatically when exiting the context


@pytest.fixture
def mock_redis():
    """Create mock Redis client for testing."""
    mock = AsyncMock()
    
    # Mock common Redis operations
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=False)
    mock.ping = AsyncMock(return_value=True)
    mock.incrby = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.ttl = AsyncMock(return_value=300)
    
    # Create a dict to simulate cache storage
    cache_storage = {}
    
    async def mock_get(key: str):
        return cache_storage.get(key)
    
    async def mock_set(key: str, value: str, **kwargs):
        cache_storage[key] = value
        return True
    
    async def mock_setex(key: str, ttl: int, value: str):
        cache_storage[key] = value
        return True
    
    async def mock_delete(key: str):
        cache_storage.pop(key, None)
        return True
    
    async def mock_exists(key: str):
        return key in cache_storage
    
    mock.get = mock_get
    mock.set = mock_set
    mock.setex = mock_setex
    mock.delete = mock_delete
    mock.exists = mock_exists
    
    return mock


@pytest.fixture
async def client(db_session: AsyncSession, mock_redis) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database and Redis overrides."""
    
    async def override_get_db():
        yield db_session
    
    async def override_get_redis():
        return mock_redis
    
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


# ============================================================================
# RBAC Fixtures - Users with different roles
# ============================================================================

@pytest.fixture
async def nurse_role(db_session: AsyncSession) -> Role:
    """Create nurse role with permissions."""
    role = Role(
        name="nurse",
        description="Nurse role with patient intake permissions"
    )
    db_session.add(role)
    
    # Add nurse permissions
    permissions = [
        Permission(role=role, resource="patient", action="create"),
        Permission(role=role, resource="patient", action="read"),
        Permission(role=role, resource="patient", action="update"),
        Permission(role=role, resource="queue", action="create"),
        Permission(role=role, resource="queue", action="read"),
    ]
    for perm in permissions:
        db_session.add(perm)
    
    await db_session.flush()
    return role


@pytest.fixture
async def doctor_role(db_session: AsyncSession) -> Role:
    """Create doctor role with permissions."""
    role = Role(
        name="doctor",
        description="Doctor role with full queue access"
    )
    db_session.add(role)
    
    # Add doctor permissions
    permissions = [
        Permission(role=role, resource="patient", action="create"),
        Permission(role=role, resource="patient", action="read"),
        Permission(role=role, resource="patient", action="update"),
        Permission(role=role, resource="queue", action="create"),
        Permission(role=role, resource="queue", action="read"),
        Permission(role=role, resource="queue", action="update"),
        Permission(role=role, resource="queue", action="assign"),
        Permission(role=role, resource="queue", action="delete"),
    ]
    for perm in permissions:
        db_session.add(perm)
    
    await db_session.flush()
    return role


@pytest.fixture
async def admin_role(db_session: AsyncSession) -> Role:
    """Create admin role with all permissions."""
    role = Role(
        name="admin",
        description="Admin role with full system access"
    )
    db_session.add(role)
    
    # Add admin permissions (all resources, all actions)
    resources = ["patient", "queue", "user", "audit", "system"]
    actions = ["create", "read", "update", "delete", "assign"]
    
    for resource in resources:
        for action in actions:
            perm = Permission(role=role, resource=resource, action=action)
            db_session.add(perm)
    
    await db_session.flush()
    return role


@pytest.fixture
async def nurse_user(db_session: AsyncSession, nurse_role: Role) -> User:
    """Create test nurse user."""
    user_data = sample_user_data(role="nurse")
    user = User(
        email=user_data["email"],
        password_hash=hash_password(user_data["password"]),
        first_name=user_data["first_name"],
        last_name=user_data["last_name"],
        is_active=True
    )
    user.roles.append(nurse_role)
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def doctor_user(db_session: AsyncSession, doctor_role: Role) -> User:
    """Create test doctor user."""
    user_data = sample_user_data(role="doctor")
    user = User(
        email=user_data["email"],
        password_hash=hash_password(user_data["password"]),
        first_name=user_data["first_name"],
        last_name=user_data["last_name"],
        is_active=True
    )
    user.roles.append(doctor_role)
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession, admin_role: Role) -> User:
    """Create test admin user."""
    user_data = sample_user_data(role="admin")
    user = User(
        email=user_data["email"],
        password_hash=hash_password(user_data["password"]),
        first_name=user_data["first_name"],
        last_name=user_data["last_name"],
        is_active=True
    )
    user.roles.append(admin_role)
    db_session.add(user)
    await db_session.flush()
    return user


# ============================================================================
# Authenticated Client Fixtures
# ============================================================================

@pytest.fixture
def nurse_token(nurse_user: User) -> str:
    """Create JWT token for nurse user."""
    return generate_access_token(
        user_id=str(nurse_user.id),
        email=nurse_user.email,
        roles=["nurse"]
    )


@pytest.fixture
def doctor_token(doctor_user: User) -> str:
    """Create JWT token for doctor user."""
    return generate_access_token(
        user_id=str(doctor_user.id),
        email=doctor_user.email,
        roles=["doctor"]
    )


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Create JWT token for admin user."""
    return generate_access_token(
        user_id=str(admin_user.id),
        email=admin_user.email,
        roles=["admin"]
    )


@pytest.fixture
def nurse_auth_headers(nurse_token: str) -> Dict[str, str]:
    """Create authorization headers for nurse."""
    return {"Authorization": f"Bearer {nurse_token}"}


@pytest.fixture
def doctor_auth_headers(doctor_token: str) -> Dict[str, str]:
    """Create authorization headers for doctor."""
    return {"Authorization": f"Bearer {doctor_token}"}


@pytest.fixture
def admin_auth_headers(admin_token: str) -> Dict[str, str]:
    """Create authorization headers for admin."""
    return {"Authorization": f"Bearer {admin_token}"}


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
async def sample_patient(db_session: AsyncSession) -> Patient:
    """Create sample patient."""
    patient_data = sample_patient_data()
    patient = Patient(**patient_data)
    db_session.add(patient)
    await db_session.flush()
    return patient


@pytest.fixture
async def sample_patients(db_session: AsyncSession) -> list[Patient]:
    """Create multiple sample patients."""
    patients = []
    for patient_data in SAMPLE_PATIENTS:
        patient = Patient(**patient_data)
        db_session.add(patient)
        patients.append(patient)
    await db_session.flush()
    return patients


@pytest.fixture
async def sample_queue_entry(db_session: AsyncSession, sample_patient: Patient) -> QueueEntry:
    """Create sample queue entry."""
    entry_data = sample_queue_entry_data(patient_id=str(sample_patient.id))
    entry = QueueEntry(**entry_data)
    db_session.add(entry)
    await db_session.flush()
    return entry


@pytest.fixture
async def sample_queue_entries(db_session: AsyncSession, sample_patients: list[Patient]) -> list[QueueEntry]:
    """Create multiple sample queue entries with different priorities."""
    entries = []
    priorities = [10, 8, 5, 3, 1]
    
    for i, patient in enumerate(sample_patients[:len(priorities)]):
        entry_data = sample_queue_entry_data(
            patient_id=str(patient.id),
            priority=priorities[i]
        )
        entry = QueueEntry(**entry_data)
        db_session.add(entry)
        entries.append(entry)
    
    await db_session.flush()
    return entries


@pytest.fixture
async def sample_assignment(
    db_session: AsyncSession,
    sample_queue_entry: QueueEntry,
    doctor_user: User
) -> Assignment:
    """Create sample assignment."""
    assignment = Assignment(
        queue_entry_id=sample_queue_entry.id,
        doctor_id=doctor_user.id,
        status="active"
    )
    db_session.add(assignment)
    
    # Update queue entry status
    sample_queue_entry.status = "assigned"
    
    await db_session.flush()
    return assignment
