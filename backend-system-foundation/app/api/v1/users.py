"""User management API endpoints (admin only)."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.auth import get_current_user
from app.core.auth.password import hash_password, validate_password_complexity
from app.database.session import get_async_db
from app.models import Role, User, UserRole
from app.schemas.user import (
    RoleAssignment,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
    UserWithRoles,
)
from app.utils.exceptions import PasswordComplexityError


router = APIRouter(prefix="/users", tags=["User Management"])


# Admin permission check dependency
async def check_admin_permission(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """
    Dependency to check if current user has admin role.
    
    Args:
        current_user: Current authenticated user from JWT token
        
    Returns:
        Current user dict if admin
        
    Raises:
        HTTPException: 403 if user is not admin
    """
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required"
        )
    return current_user


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List users",
    description="Get paginated list of all users (admin only)"
)
async def list_users(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    db: Annotated[AsyncSession, Depends(get_async_db)] = None,
    admin: Annotated[dict, Depends(check_admin_permission)] = None,
) -> UserListResponse:
    """
    Get paginated list of all users with their roles.
    
    Args:
        page: Page number (starts at 1)
        page_size: Number of items per page (max 100)
        db: Database session
        admin: Current admin user
        
    Returns:
        UserListResponse with paginated users
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 500 if database error
    """
    try:
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get total count
        count_stmt = select(func.count(User.id))
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar_one()
        
        # Get users with roles
        stmt = (
            select(User)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .offset(offset)
            .limit(page_size)
            .order_by(User.created_at.desc())
        )
        
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        # Build response with roles
        users_with_roles = []
        for user in users:
            roles = [ur.role.name for ur in user.user_roles]
            user_dict = {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "roles": roles
            }
            users_with_roles.append(UserWithRoles(**user_dict))
        
        # Calculate total pages
        total_pages = ceil(total_count / page_size) if total_count > 0 else 1
        
        return UserListResponse(
            users=users_with_roles,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user (admin only)"
)
async def create_user(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    admin: Annotated[dict, Depends(check_admin_permission)],
) -> UserResponse:
    """
    Create a new user.
    
    Args:
        user_data: User creation data
        db: Database session
        admin: Current admin user
        
    Returns:
        Created user information
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 409 if email already exists
        HTTPException: 422 if password doesn't meet complexity requirements
        HTTPException: 500 if database error
    """
    try:
        # Validate password complexity
        is_valid, error_message = validate_password_complexity(user_data.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_message
            )
        
        # Check if email already exists
        stmt = select(User).where(User.email == user_data.email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Hash password
        password_hash = hash_password(user_data.password)
        
        # Create user
        new_user = User(
            email=user_data.email,
            password_hash=password_hash,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            is_active=True
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        return UserResponse.model_validate(new_user)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get(
    "/{user_id}",
    response_model=UserWithRoles,
    status_code=status.HTTP_200_OK,
    summary="Get user details",
    description="Get detailed information about a specific user (admin only)"
)
async def get_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    admin: Annotated[dict, Depends(check_admin_permission)],
) -> UserWithRoles:
    """
    Get detailed information about a specific user.
    
    Args:
        user_id: User ID
        db: Database session
        admin: Current admin user
        
    Returns:
        User information with roles
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if user not found
        HTTPException: 500 if database error
    """
    try:
        # Get user with roles
        stmt = (
            select(User)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .where(User.id == user_id)
        )
        
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Build response with roles
        roles = [ur.role.name for ur in user.user_roles]
        user_dict = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "roles": roles
        }
        
        return UserWithRoles(**user_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user",
    description="Update user information (admin only)"
)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    admin: Annotated[dict, Depends(check_admin_permission)],
) -> UserResponse:
    """
    Update user information.
    
    Args:
        user_id: User ID
        user_data: User update data
        db: Database session
        admin: Current admin user
        
    Returns:
        Updated user information
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if user not found
        HTTPException: 409 if email already exists
        HTTPException: 422 if password doesn't meet complexity requirements
        HTTPException: 500 if database error
    """
    try:
        # Get user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if email is being updated and already exists
        if user_data.email and user_data.email != user.email:
            email_stmt = select(User).where(User.email == user_data.email)
            email_result = await db.execute(email_stmt)
            existing_user = email_result.scalar_one_or_none()
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered"
                )
            
            user.email = user_data.email
        
        # Validate and update password if provided
        if user_data.password:
            is_valid, error_message = validate_password_complexity(user_data.password)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=error_message
                )
            
            user.password_hash = hash_password(user_data.password)
        
        # Update other fields
        if user_data.first_name is not None:
            user.first_name = user_data.first_name
        
        if user_data.last_name is not None:
            user.last_name = user_data.last_name
        
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
        
        await db.commit()
        await db.refresh(user)
        
        return UserResponse.model_validate(user)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate user",
    description="Deactivate user account (soft delete, admin only)"
)
async def deactivate_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    admin: Annotated[dict, Depends(check_admin_permission)],
) -> dict:
    """
    Deactivate user account (soft delete).
    
    Args:
        user_id: User ID
        db: Database session
        admin: Current admin user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if user not found
        HTTPException: 500 if database error
    """
    try:
        # Get user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Soft delete by setting is_active to False
        user.is_active = False
        
        await db.commit()
        
        return {
            "message": "User deactivated successfully",
            "user_id": str(user_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user"
        )


@router.post(
    "/{user_id}/roles",
    status_code=status.HTTP_200_OK,
    summary="Assign role to user",
    description="Assign a role to a user (admin only)"
)
async def assign_role(
    user_id: UUID,
    role_data: RoleAssignment,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    admin: Annotated[dict, Depends(check_admin_permission)],
) -> dict:
    """
    Assign a role to a user.
    
    Args:
        user_id: User ID
        role_data: Role assignment data
        db: Database session
        admin: Current admin user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if user or role not found
        HTTPException: 409 if role already assigned
        HTTPException: 500 if database error
    """
    try:
        # Check if user exists
        user_stmt = select(User).where(User.id == user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get role by name
        role_stmt = select(Role).where(Role.name == role_data.role_name)
        role_result = await db.execute(role_stmt)
        role = role_result.scalar_one_or_none()
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{role_data.role_name}' not found"
            )
        
        # Check if role already assigned
        existing_stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role.id
        )
        existing_result = await db.execute(existing_stmt)
        existing_assignment = existing_result.scalar_one_or_none()
        
        if existing_assignment:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role '{role_data.role_name}' already assigned to user"
            )
        
        # Create user-role association
        user_role = UserRole(
            user_id=user_id,
            role_id=role.id
        )
        
        db.add(user_role)
        await db.commit()
        
        return {
            "message": f"Role '{role_data.role_name}' assigned successfully",
            "user_id": str(user_id),
            "role_id": str(role.id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign role"
        )


@router.delete(
    "/{user_id}/roles/{role_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove role from user",
    description="Remove a role from a user (admin only)"
)
async def remove_role(
    user_id: UUID,
    role_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    admin: Annotated[dict, Depends(check_admin_permission)],
) -> dict:
    """
    Remove a role from a user.
    
    Args:
        user_id: User ID
        role_id: Role ID
        db: Database session
        admin: Current admin user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if user, role, or assignment not found
        HTTPException: 500 if database error
    """
    try:
        # Check if user exists
        user_stmt = select(User).where(User.id == user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if role exists
        role_stmt = select(Role).where(Role.id == role_id)
        role_result = await db.execute(role_stmt)
        role = role_result.scalar_one_or_none()
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Get user-role association
        assignment_stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
        assignment_result = await db.execute(assignment_stmt)
        assignment = assignment_result.scalar_one_or_none()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role assignment not found"
            )
        
        # Delete user-role association
        await db.delete(assignment)
        await db.commit()
        
        return {
            "message": f"Role '{role.name}' removed successfully",
            "user_id": str(user_id),
            "role_id": str(role_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove role"
        )
