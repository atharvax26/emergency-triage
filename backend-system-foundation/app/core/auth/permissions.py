"""Permission checking module with RBAC and Redis caching."""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cache.client import RedisClient
from app.cache.keys import CacheKeys
from app.config import settings
from app.models.user import User, Role, Permission, UserRole


class PermissionService:
    """
    Service for checking user permissions with role-based access control.
    
    Implements RBAC matrix enforcement with Redis caching for performance.
    Cache TTL: 10 minutes for permission lookups.
    
    RBAC Matrix:
    - Nurse: Patient (create, read, update), Queue (create, read)
    - Doctor: Patient (create, read, update), Queue (create, read, update, assign, delete)
    - Admin: All permissions on all resources
    """
    
    # RBAC Matrix definition
    RBAC_MATRIX = {
        "nurse": {
            "patient": ["create", "read", "update"],
            "queue": ["create", "read"],
        },
        "doctor": {
            "patient": ["create", "read", "update"],
            "queue": ["create", "read", "update", "assign", "delete"],
        },
        "admin": {
            "patient": ["create", "read", "update", "delete"],
            "queue": ["create", "read", "update", "assign", "delete"],
            "user": ["create", "read", "update", "delete"],
            "audit": ["read"],
        },
    }
    
    def __init__(self, db: AsyncSession, cache: RedisClient):
        """
        Initialize permission service.
        
        Args:
            db: Database session
            cache: Redis cache client
        """
        self.db = db
        self.cache = cache
    
    async def check_permission(
        self,
        user_id: UUID,
        resource: str,
        action: str
    ) -> bool:
        """
        Check if user has permission to perform action on resource.
        
        Implements efficient permission checking with Redis caching:
        1. Check cache for user permissions
        2. If cache miss, query database for user roles
        3. Query permissions for each role
        4. Cache results with 10-minute TTL
        5. Check if any role grants the requested permission
        
        Admin role has all permissions automatically.
        
        Args:
            user_id: User ID to check permissions for
            resource: Resource type (e.g., 'patient', 'queue', 'user')
            action: Action to perform (e.g., 'create', 'read', 'update', 'delete')
            
        Returns:
            True if user has permission, False otherwise
        """
        # Try to get cached permissions
        cache_key = CacheKeys.user_permissions(user_id)
        cached_permissions = await self.cache.get_json(cache_key)
        
        if cached_permissions is not None:
            # Check if permission exists in cache
            return self._check_permission_in_cache(
                cached_permissions,
                resource,
                action
            )
        
        # Cache miss - query database
        user_roles = await self.get_user_roles(user_id)
        
        if not user_roles:
            return False
        
        # Admin has all permissions
        if "admin" in user_roles:
            # Cache admin permissions
            await self._cache_admin_permissions(user_id)
            return True
        
        # Get permissions for all user roles
        all_permissions = []
        for role_name in user_roles:
            role_permissions = await self.get_role_permissions(role_name)
            all_permissions.extend(role_permissions)
        
        # Cache permissions
        await self._cache_permissions(user_id, all_permissions)
        
        # Check if user has the requested permission
        return (resource, action) in all_permissions
    
    async def get_user_roles(self, user_id: UUID) -> List[str]:
        """
        Get list of role names for a user.
        
        Queries database for user roles with caching:
        1. Check cache for user roles
        2. If cache miss, query database
        3. Cache results with 10-minute TTL
        
        Args:
            user_id: User ID to get roles for
            
        Returns:
            List of role names (e.g., ['nurse'], ['doctor', 'admin'])
        """
        # Try to get cached roles
        cache_key = CacheKeys.user_roles(user_id)
        cached_roles = await self.cache.get_json(cache_key)
        
        if cached_roles is not None:
            return cached_roles
        
        # Cache miss - query database
        stmt = (
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        
        result = await self.db.execute(stmt)
        roles = [row[0] for row in result.all()]
        
        # Cache roles
        await self.cache.set_json(
            cache_key,
            roles,
            ttl=settings.CACHE_TTL_PERMISSION
        )
        
        return roles
    
    async def get_role_permissions(self, role_name: str) -> List[Tuple[str, str]]:
        """
        Get list of permissions for a role.
        
        Returns permissions as list of (resource, action) tuples.
        Uses RBAC matrix for permission lookup.
        
        Args:
            role_name: Role name (e.g., 'nurse', 'doctor', 'admin')
            
        Returns:
            List of (resource, action) tuples
        """
        # Get permissions from RBAC matrix
        role_permissions = self.RBAC_MATRIX.get(role_name.lower(), {})
        
        permissions = []
        for resource, actions in role_permissions.items():
            for action in actions:
                permissions.append((resource, action))
        
        return permissions
    
    async def has_role(self, user_id: UUID, role_name: str) -> bool:
        """
        Check if user has a specific role.
        
        Args:
            user_id: User ID to check
            role_name: Role name to check for
            
        Returns:
            True if user has the role, False otherwise
        """
        user_roles = await self.get_user_roles(user_id)
        return role_name.lower() in [r.lower() for r in user_roles]
    
    async def invalidate_user_permissions(self, user_id: UUID) -> bool:
        """
        Invalidate cached permissions for a user.
        
        Should be called when user roles are modified.
        
        Args:
            user_id: User ID to invalidate cache for
            
        Returns:
            True if successful, False otherwise
        """
        cache_key_permissions = CacheKeys.user_permissions(user_id)
        cache_key_roles = CacheKeys.user_roles(user_id)
        
        success_permissions = await self.cache.delete(cache_key_permissions)
        success_roles = await self.cache.delete(cache_key_roles)
        
        return success_permissions and success_roles
    
    def _check_permission_in_cache(
        self,
        cached_permissions: dict,
        resource: str,
        action: str
    ) -> bool:
        """
        Check if permission exists in cached permissions.
        
        Args:
            cached_permissions: Cached permissions dict
            resource: Resource type
            action: Action to perform
            
        Returns:
            True if permission exists, False otherwise
        """
        # Check if it's admin (has all permissions)
        if cached_permissions.get("is_admin", False):
            return True
        
        # Check specific permission
        permissions = cached_permissions.get("permissions", [])
        return [resource, action] in permissions
    
    async def _cache_permissions(
        self,
        user_id: UUID,
        permissions: List[Tuple[str, str]]
    ) -> bool:
        """
        Cache user permissions.
        
        Args:
            user_id: User ID
            permissions: List of (resource, action) tuples
            
        Returns:
            True if successful, False otherwise
        """
        cache_key = CacheKeys.user_permissions(user_id)
        
        # Convert tuples to lists for JSON serialization
        permissions_list = [[resource, action] for resource, action in permissions]
        
        cache_data = {
            "is_admin": False,
            "permissions": permissions_list
        }
        
        return await self.cache.set_json(
            cache_key,
            cache_data,
            ttl=settings.CACHE_TTL_PERMISSION
        )
    
    async def _cache_admin_permissions(self, user_id: UUID) -> bool:
        """
        Cache admin permissions (all permissions).
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        cache_key = CacheKeys.user_permissions(user_id)
        
        cache_data = {
            "is_admin": True,
            "permissions": []
        }
        
        return await self.cache.set_json(
            cache_key,
            cache_data,
            ttl=settings.CACHE_TTL_PERMISSION
        )


async def get_permission_service(
    db: AsyncSession,
    cache: RedisClient
) -> PermissionService:
    """
    Dependency for permission service.
    
    Args:
        db: Database session
        cache: Redis cache client
        
    Returns:
        PermissionService instance
    """
    return PermissionService(db, cache)
