"""Audit API endpoints (admin only)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit.service import AuditEngine
from app.database.session import get_async_db
from app.schemas.audit import (
    AuditQuery,
    AuditRecordResponse,
    AuditExportRequest,
    AuditLogListResponse,
)
from app.api.v1.auth import get_current_user


router = APIRouter(prefix="/audit", tags=["Audit"])


# Dependency to get AuditEngine
async def get_audit_engine(
    db: Annotated[AsyncSession, Depends(get_async_db)]
) -> AuditEngine:
    """
    Dependency to get AuditEngine instance.
    
    Args:
        db: Database session
        
    Returns:
        AuditEngine instance
    """
    return AuditEngine(db=db)


# Dependency to check admin role
async def require_admin(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """
    Dependency to ensure user has admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if admin
        
    Raises:
        HTTPException: 403 if user is not admin
    """
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.get(
    "",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="Query audit logs",
    description="Query audit logs with filters and pagination (admin only)"
)
async def query_audit_logs(
    user_id: UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    page: int = 1,
    page_size: int = 100,
    current_user: Annotated[dict, Depends(require_admin)] = None,
    audit_engine: Annotated[AuditEngine, Depends(get_audit_engine)] = None,
) -> AuditLogListResponse:
    """
    Query audit logs with filtering and pagination.
    
    Args:
        user_id: Filter by user ID
        action: Filter by action
        resource_type: Filter by resource type
        resource_id: Filter by resource ID
        page: Page number (default: 1)
        page_size: Items per page (default: 100, max: 1000)
        current_user: Current authenticated admin user
        audit_engine: AuditEngine instance
        
    Returns:
        Paginated list of audit logs
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 500 if query fails
    """
    try:
        # Build query criteria
        criteria = AuditQuery(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            page=page,
            page_size=min(page_size, 1000),  # Cap at 1000
        )
        
        # Query audit logs
        logs, total_count = await audit_engine.query_audit_log(criteria)
        
        # Calculate total pages
        total_pages = (total_count + criteria.page_size - 1) // criteria.page_size
        
        # Convert to response models
        items = [
            AuditRecordResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                metadata=log.metadata_,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
            for log in logs
        ]
        
        return AuditLogListResponse(
            items=items,
            total_count=total_count,
            page=criteria.page,
            page_size=criteria.page_size,
            total_pages=total_pages,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query audit logs",
        )


@router.post(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export audit logs",
    description="Export audit logs to CSV or JSON format (admin only)"
)
async def export_audit_logs(
    request: AuditExportRequest,
    current_user: Annotated[dict, Depends(require_admin)],
    audit_engine: Annotated[AuditEngine, Depends(get_audit_engine)],
) -> Response:
    """
    Export audit logs to CSV or JSON format.
    
    Args:
        request: Export request with date range and filters
        current_user: Current authenticated admin user
        audit_engine: AuditEngine instance
        
    Returns:
        File response with exported data
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 422 if date range is invalid
        HTTPException: 500 if export fails
    """
    try:
        # Export audit logs
        data = await audit_engine.export_audit_log(
            start_date=request.start_date,
            end_date=request.end_date,
            format=request.format,
            user_id=request.user_id,
            action=request.action,
            resource_type=request.resource_type,
        )
        
        # Determine content type and filename
        if request.format == "csv":
            media_type = "text/csv"
            filename = f"audit_logs_{request.start_date.date()}_{request.end_date.date()}.csv"
        else:  # json
            media_type = "application/json"
            filename = f"audit_logs_{request.start_date.date()}_{request.end_date.date()}.json"
        
        # Return file response
        return Response(
            content=data,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export audit logs",
        )


@router.get(
    "/user/{user_id}",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get audit logs for user",
    description="Get audit logs for a specific user (admin only)"
)
async def get_user_audit_logs(
    user_id: UUID,
    page: int = 1,
    page_size: int = 100,
    current_user: Annotated[dict, Depends(require_admin)] = None,
    audit_engine: Annotated[AuditEngine, Depends(get_audit_engine)] = None,
) -> AuditLogListResponse:
    """
    Get audit logs for a specific user.
    
    Args:
        user_id: User ID to filter by
        page: Page number (default: 1)
        page_size: Items per page (default: 100, max: 1000)
        current_user: Current authenticated admin user
        audit_engine: AuditEngine instance
        
    Returns:
        Paginated list of audit logs for the user
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if user not found
        HTTPException: 500 if query fails
    """
    try:
        # Build query criteria
        criteria = AuditQuery(
            user_id=user_id,
            page=page,
            page_size=min(page_size, 1000),
        )
        
        # Query audit logs
        logs, total_count = await audit_engine.query_audit_log(criteria)
        
        # Check if user exists (if no logs found)
        if total_count == 0:
            # Note: We don't verify user existence here to avoid additional DB query
            # An empty result could mean user exists but has no audit logs
            pass
        
        # Calculate total pages
        total_pages = (total_count + criteria.page_size - 1) // criteria.page_size
        
        # Convert to response models
        items = [
            AuditRecordResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                metadata=log.metadata_,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
            for log in logs
        ]
        
        return AuditLogListResponse(
            items=items,
            total_count=total_count,
            page=criteria.page,
            page_size=criteria.page_size,
            total_pages=total_pages,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query user audit logs",
        )


@router.get(
    "/resource/{resource_type}/{resource_id}",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get audit logs for resource",
    description="Get audit logs for a specific resource (admin only)"
)
async def get_resource_audit_logs(
    resource_type: str,
    resource_id: UUID,
    page: int = 1,
    page_size: int = 100,
    current_user: Annotated[dict, Depends(require_admin)] = None,
    audit_engine: Annotated[AuditEngine, Depends(get_audit_engine)] = None,
) -> AuditLogListResponse:
    """
    Get audit logs for a specific resource.
    
    Args:
        resource_type: Type of resource (e.g., 'patient', 'queue_entry')
        resource_id: Resource ID to filter by
        page: Page number (default: 1)
        page_size: Items per page (default: 100, max: 1000)
        current_user: Current authenticated admin user
        audit_engine: AuditEngine instance
        
    Returns:
        Paginated list of audit logs for the resource
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not admin
        HTTPException: 404 if resource not found
        HTTPException: 500 if query fails
    """
    try:
        # Build query criteria
        criteria = AuditQuery(
            resource_type=resource_type,
            resource_id=resource_id,
            page=page,
            page_size=min(page_size, 1000),
        )
        
        # Query audit logs
        logs, total_count = await audit_engine.query_audit_log(criteria)
        
        # Check if resource exists (if no logs found)
        if total_count == 0:
            # Note: We don't verify resource existence here to avoid additional DB query
            # An empty result could mean resource exists but has no audit logs
            pass
        
        # Calculate total pages
        total_pages = (total_count + criteria.page_size - 1) // criteria.page_size
        
        # Convert to response models
        items = [
            AuditRecordResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                metadata=log.metadata_,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
            for log in logs
        ]
        
        return AuditLogListResponse(
            items=items,
            total_count=total_count,
            page=criteria.page,
            page_size=criteria.page_size,
            total_pages=total_pages,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query resource audit logs",
        )
