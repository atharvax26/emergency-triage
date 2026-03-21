"""Unit tests for permission checking module."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.auth.permissions import PermissionService
from app.cache.keys import CacheKeys


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_cache():
    """Mock Redis cache client."""
    cache = AsyncMock()
    cache.get_json = AsyncMock(return_value=None)
    cache.set_json = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    return cache


@pytest.fixture
def permission_service(mock_db, mock_cache):
    """Create permission service instance."""
    return PermissionService(mock_db, mock_cache)


class TestPermissionService:
    """Test suite for PermissionService."""
    
    @pytest.mark.asyncio
    async def test_check_permission_cache_hit(self, permission_service, mock_cache):
        """Test permission check with cache hit."""
        user_id = uuid4()
        
        # Mock cached permissions
        mock_cache.get_json.return_value = {
            "is_admin": False,
            "permissions": [["patient", "read"], ["patient", "create"]]
        }
        
        # Check permission
        result = await permission_service.check_permission(
            user_id,
            "patient",
            "read"
        )
        
        assert result is True
        mock_cache.get_json.assert_called_once_with(
            CacheKeys.user_permissions(user_id)
        )
    
    @pytest.mark.asyncio
    async def test_check_permission_cache_hit_denied(self, permission_service, mock_cache):
        """Test permission check with cache hit but permission denied."""
        user_id = uuid4()
        
        # Mock cached permissions
        mock_cache.get_json.return_value = {
            "is_admin": False,
            "permissions": [["patient", "read"]]
        }
        
        # Check permission that user doesn't have
        result = await permission_service.check_permission(
            user_id,
            "patient",
            "delete"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_permission_admin_cached(self, permission_service, mock_cache):
        """Test admin user has all permissions (cached)."""
        user_id = uuid4()
        
        # Mock cached admin permissions
        mock_cache.get_json.return_value = {
            "is_admin": True,
            "permissions": []
        }
        
        # Check any permission
        result = await permission_service.check_permission(
            user_id,
            "user",
            "delete"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_permission_cache_miss_nurse(self, permission_service, mock_cache, mock_db):
        """Test permission check with cache miss for nurse role."""
        user_id = uuid4()
        
        # Mock cache miss
        mock_cache.get_json.return_value = None
        
        # Mock database query for roles
        mock_result = MagicMock()
        mock_result.all.return_value = [("nurse",)]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Check permission
        result = await permission_service.check_permission(
            user_id,
            "patient",
            "read"
        )
        
        assert result is True
        # Verify cache was updated
        assert mock_cache.set_json.called
    
    @pytest.mark.asyncio
    async def test_check_permission_cache_miss_doctor(self, permission_service, mock_cache, mock_db):
        """Test permission check with cache miss for doctor role."""
        user_id = uuid4()
        
        # Mock cache miss
        mock_cache.get_json.return_value = None
        
        # Mock database query for roles
        mock_result = MagicMock()
        mock_result.all.return_value = [("doctor",)]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Check permission
        result = await permission_service.check_permission(
            user_id,
            "queue",
            "assign"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_permission_cache_miss_admin(self, permission_service, mock_cache, mock_db):
        """Test permission check with cache miss for admin role."""
        user_id = uuid4()
        
        # Mock cache miss
        mock_cache.get_json.return_value = None
        
        # Mock database query for roles
        mock_result = MagicMock()
        mock_result.all.return_value = [("admin",)]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Check any permission
        result = await permission_service.check_permission(
            user_id,
            "audit",
            "read"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_permission_no_roles(self, permission_service, mock_cache, mock_db):
        """Test permission check for user with no roles."""
        user_id = uuid4()
        
        # Mock cache miss
        mock_cache.get_json.return_value = None
        
        # Mock database query for roles (empty)
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Check permission
        result = await permission_service.check_permission(
            user_id,
            "patient",
            "read"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_nurse_cannot_delete_patient(self, permission_service, mock_cache, mock_db):
        """Test nurse cannot delete patients."""
        user_id = uuid4()
        
        # Mock cache miss
        mock_cache.get_json.return_value = None
        
        # Mock database query for roles
        mock_result = MagicMock()
        mock_result.all.return_value = [("nurse",)]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Check permission
        result = await permission_service.check_permission(
            user_id,
            "patient",
            "delete"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_nurse_cannot_assign_queue(self, permission_service, mock_cache, mock_db):
        """Test nurse cannot assign patients to doctors."""
        user_id = uuid4()
        
        # Mock cache miss
        mock_cache.get_json.return_value = None
        
        # Mock database query for roles
        mock_result = MagicMock()
        mock_result.all.return_value = [("nurse",)]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Check permission
        result = await permission_service.check_permission(
            user_id,
            "queue",
            "assign"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_doctor_cannot_manage_users(self, permission_service, mock_cache, mock_db):
        """Test doctor cannot create or modify users."""
        user_id = uuid4()
        
        # Mock cache miss
        mock_cache.get_json.return_value = None
        
        # Mock database query for roles
        mock_result = MagicMock()
        mock_result.all.return_value = [("doctor",)]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Check permission
        result = await permission_service.check_permission(
            user_id,
            "user",
            "create"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_user_roles_cache_hit(self, permission_service, mock_cache):
        """Test get user roles with cache hit."""
        user_id = uuid4()
        
        # Mock cached roles
        mock_cache.get_json.return_value = ["nurse", "doctor"]
        
        # Get roles
        roles = await permission_service.get_user_roles(user_id)
        
        assert roles == ["nurse", "doctor"]
        mock_cache.get_json.assert_called_once_with(
            CacheKeys.user_roles(user_id)
        )
    
    @pytest.mark.asyncio
    async def test_get_user_roles_cache_miss(self, permission_service, mock_cache, mock_db):
        """Test get user roles with cache miss."""
        user_id = uuid4()
        
        # Mock cache miss
        mock_cache.get_json.return_value = None
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.all.return_value = [("nurse",), ("doctor",)]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Get roles
        roles = await permission_service.get_user_roles(user_id)
        
        assert roles == ["nurse", "doctor"]
        # Verify cache was updated
        mock_cache.set_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_role_permissions_nurse(self, permission_service):
        """Test get permissions for nurse role."""
        permissions = await permission_service.get_role_permissions("nurse")
        
        assert ("patient", "create") in permissions
        assert ("patient", "read") in permissions
        assert ("patient", "update") in permissions
        assert ("queue", "create") in permissions
        assert ("queue", "read") in permissions
        assert ("patient", "delete") not in permissions
        assert ("queue", "assign") not in permissions
    
    @pytest.mark.asyncio
    async def test_get_role_permissions_doctor(self, permission_service):
        """Test get permissions for doctor role."""
        permissions = await permission_service.get_role_permissions("doctor")
        
        assert ("patient", "create") in permissions
        assert ("patient", "read") in permissions
        assert ("patient", "update") in permissions
        assert ("queue", "create") in permissions
        assert ("queue", "read") in permissions
        assert ("queue", "update") in permissions
        assert ("queue", "assign") in permissions
        assert ("queue", "delete") in permissions
        assert ("patient", "delete") not in permissions
        assert ("user", "create") not in permissions
    
    @pytest.mark.asyncio
    async def test_get_role_permissions_admin(self, permission_service):
        """Test get permissions for admin role."""
        permissions = await permission_service.get_role_permissions("admin")
        
        assert ("patient", "create") in permissions
        assert ("patient", "read") in permissions
        assert ("patient", "update") in permissions
        assert ("patient", "delete") in permissions
        assert ("queue", "create") in permissions
        assert ("queue", "read") in permissions
        assert ("queue", "update") in permissions
        assert ("queue", "assign") in permissions
        assert ("queue", "delete") in permissions
        assert ("user", "create") in permissions
        assert ("user", "read") in permissions
        assert ("user", "update") in permissions
        assert ("user", "delete") in permissions
        assert ("audit", "read") in permissions
    
    @pytest.mark.asyncio
    async def test_has_role_true(self, permission_service, mock_cache):
        """Test has_role returns True when user has role."""
        user_id = uuid4()
        
        # Mock cached roles
        mock_cache.get_json.return_value = ["nurse", "doctor"]
        
        # Check role
        result = await permission_service.has_role(user_id, "nurse")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_has_role_false(self, permission_service, mock_cache):
        """Test has_role returns False when user doesn't have role."""
        user_id = uuid4()
        
        # Mock cached roles
        mock_cache.get_json.return_value = ["nurse"]
        
        # Check role
        result = await permission_service.has_role(user_id, "admin")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_has_role_case_insensitive(self, permission_service, mock_cache):
        """Test has_role is case insensitive."""
        user_id = uuid4()
        
        # Mock cached roles
        mock_cache.get_json.return_value = ["Nurse"]
        
        # Check role with different case
        result = await permission_service.has_role(user_id, "nurse")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_invalidate_user_permissions(self, permission_service, mock_cache):
        """Test invalidate user permissions."""
        user_id = uuid4()
        
        # Invalidate cache
        result = await permission_service.invalidate_user_permissions(user_id)
        
        assert result is True
        # Verify both cache keys were deleted
        assert mock_cache.delete.call_count == 2
    
    @pytest.mark.asyncio
    async def test_rbac_matrix_nurse_permissions(self, permission_service):
        """Test RBAC matrix for nurse role."""
        matrix = permission_service.RBAC_MATRIX["nurse"]
        
        assert "patient" in matrix
        assert "queue" in matrix
        assert "create" in matrix["patient"]
        assert "read" in matrix["patient"]
        assert "update" in matrix["patient"]
        assert "delete" not in matrix["patient"]
        assert "create" in matrix["queue"]
        assert "read" in matrix["queue"]
        assert "assign" not in matrix["queue"]
    
    @pytest.mark.asyncio
    async def test_rbac_matrix_doctor_permissions(self, permission_service):
        """Test RBAC matrix for doctor role."""
        matrix = permission_service.RBAC_MATRIX["doctor"]
        
        assert "patient" in matrix
        assert "queue" in matrix
        assert "create" in matrix["patient"]
        assert "read" in matrix["patient"]
        assert "update" in matrix["patient"]
        assert "delete" not in matrix["patient"]
        assert "create" in matrix["queue"]
        assert "read" in matrix["queue"]
        assert "update" in matrix["queue"]
        assert "assign" in matrix["queue"]
        assert "delete" in matrix["queue"]
    
    @pytest.mark.asyncio
    async def test_rbac_matrix_admin_permissions(self, permission_service):
        """Test RBAC matrix for admin role."""
        matrix = permission_service.RBAC_MATRIX["admin"]
        
        assert "patient" in matrix
        assert "queue" in matrix
        assert "user" in matrix
        assert "audit" in matrix
        assert "create" in matrix["patient"]
        assert "read" in matrix["patient"]
        assert "update" in matrix["patient"]
        assert "delete" in matrix["patient"]
        assert "create" in matrix["user"]
        assert "read" in matrix["user"]
        assert "update" in matrix["user"]
        assert "delete" in matrix["user"]
        assert "read" in matrix["audit"]
