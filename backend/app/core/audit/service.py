"""AuditEngine service for comprehensive audit logging."""

import csv
import io
import json
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit.logger import AuditEvent, AuditLogFormatter
from app.models.audit import AuditLog
from app.schemas.audit import AuditQuery, AuditRecordResponse


class AuditEngine:
    """
    Comprehensive audit logging service.
    
    Provides methods for logging all system actions, querying audit logs,
    and exporting audit data for compliance and security analysis.
    
    Key Features:
    - Immutable audit logs (no updates or deletes)
    - PII masking for privacy compliance
    - Sensitive data exclusion (passwords, SSN, credit cards)
    - Correlation ID support for request tracking
    - Flexible querying with filtering and pagination
    - Export to CSV and JSON formats
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the audit engine.
        
        Args:
            db: Database session for audit log storage
        """
        self.db = db
    
    async def log_action(
        self,
        user_id: Optional[UUID],
        action: str,
        resource_type: str,
        status: str,
        ip_address: str,
        user_agent: str,
        request_id: UUID,
        resource_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """
        Log a general system action.
        
        Creates an immutable audit log entry for any system action.
        Applies PII masking and sensitive data filtering automatically.
        
        Args:
            user_id: ID of user performing the action (None for system events)
            action: Action being performed (e.g., 'patient.create', 'queue.update')
            resource_type: Type of resource affected
            status: Result status ('success', 'failure', 'error')
            ip_address: IP address of request origin
            user_agent: User agent string from request
            request_id: Correlation ID for request tracking
            resource_id: ID of affected resource (optional)
            metadata: Additional context (endpoint, method, status_code, etc.)
            
        Returns:
            Created AuditLog record
            
        Example:
            await audit_engine.log_action(
                user_id=user.id,
                action='patient.create',
                resource_type='patient',
                status='success',
                ip_address='192.168.1.1',
                user_agent='Mozilla/5.0...',
                request_id=uuid4(),
                resource_id=patient.id,
                metadata={
                    'endpoint': '/api/v1/patients',
                    'method': 'POST',
                    'status_code': 201
                }
            )
        """
        # Create audit event
        event = AuditEvent(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        
        # Format event with PII masking and sensitive data filtering
        formatted = AuditLogFormatter.format_for_storage(event)
        
        # Create audit log record
        audit_log = AuditLog(
            id=event.event_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_=formatted['metadata'],
            ip_address=ip_address,
        )
        
        # Store in database
        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)
        
        return audit_log
    
    async def log_auth_event(
        self,
        user_id: Optional[UUID],
        action: str,
        result: bool,
        ip_address: str,
        user_agent: str,
        request_id: UUID,
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """
        Log an authentication event.
        
        Specialized method for logging authentication-related actions like
        login, logout, token refresh, etc.
        
        Args:
            user_id: ID of user (None for failed login attempts)
            action: Auth action (e.g., 'auth.login.success', 'auth.logout')
            result: Whether the action succeeded
            ip_address: IP address of request origin
            user_agent: User agent string from request
            request_id: Correlation ID for request tracking
            metadata: Additional context (email, reason for failure, etc.)
            
        Returns:
            Created AuditLog record
            
        Example:
            await audit_engine.log_auth_event(
                user_id=user.id,
                action='auth.login.success',
                result=True,
                ip_address='192.168.1.1',
                user_agent='Mozilla/5.0...',
                request_id=uuid4(),
                metadata={'email': 'user@example.com'}
            )
        """
        status = 'success' if result else 'failure'
        
        return await self.log_action(
            user_id=user_id,
            action=action,
            resource_type='session',
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            metadata=metadata,
        )
    
    async def log_data_access(
        self,
        user_id: UUID,
        resource: str,
        action: str,
        ip_address: str,
        user_agent: str,
        request_id: UUID,
        resource_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """
        Log a data access event.
        
        Specialized method for logging data access actions for HIPAA compliance.
        Tracks all patient data access for audit trails.
        
        Args:
            user_id: ID of user accessing the data
            resource: Resource type being accessed (e.g., 'patient', 'queue_entry')
            action: Action being performed (e.g., 'read', 'update', 'search')
            ip_address: IP address of request origin
            user_agent: User agent string from request
            request_id: Correlation ID for request tracking
            resource_id: ID of specific resource accessed (optional)
            metadata: Additional context (search criteria, fields accessed, etc.)
            
        Returns:
            Created AuditLog record
            
        Example:
            await audit_engine.log_data_access(
                user_id=user.id,
                resource='patient',
                action='read',
                ip_address='192.168.1.1',
                user_agent='Mozilla/5.0...',
                request_id=uuid4(),
                resource_id=patient.id,
                metadata={'fields': ['name', 'mrn', 'dob']}
            )
        """
        full_action = f"{resource}.{action}"
        
        return await self.log_action(
            user_id=user_id,
            action=full_action,
            resource_type=resource,
            status='success',
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            resource_id=resource_id,
            metadata=metadata,
        )
    
    async def query_audit_log(
        self,
        criteria: AuditQuery,
    ) -> tuple[List[AuditLog], int]:
        """
        Query audit logs with filtering and pagination.
        
        Supports filtering by user, action, resource type, date range, etc.
        Returns paginated results with total count.
        
        Args:
            criteria: Query criteria including filters and pagination
            
        Returns:
            Tuple of (list of audit logs, total count)
            
        Example:
            logs, total = await audit_engine.query_audit_log(
                AuditQuery(
                    user_id=user.id,
                    action='patient.create',
                    start_date=datetime(2024, 1, 1),
                    end_date=datetime(2024, 1, 31),
                    page=1,
                    page_size=100
                )
            )
        """
        # Build query with filters
        query = select(AuditLog)
        conditions = []
        
        if criteria.user_id:
            conditions.append(AuditLog.user_id == criteria.user_id)
        
        if criteria.action:
            conditions.append(AuditLog.action == criteria.action)
        
        if criteria.resource_type:
            conditions.append(AuditLog.resource_type == criteria.resource_type)
        
        if criteria.resource_id:
            conditions.append(AuditLog.resource_id == criteria.resource_id)
        
        if criteria.start_date:
            conditions.append(AuditLog.created_at >= criteria.start_date)
        
        if criteria.end_date:
            conditions.append(AuditLog.created_at <= criteria.end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count()).select_from(AuditLog)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        result = await self.db.execute(count_query)
        total_count = result.scalar() or 0
        
        # Apply pagination and ordering
        query = query.order_by(AuditLog.created_at.desc())
        query = query.offset((criteria.page - 1) * criteria.page_size)
        query = query.limit(criteria.page_size)
        
        # Execute query
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        return list(logs), total_count
    
    async def export_audit_log(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = 'json',
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> bytes:
        """
        Export audit logs to CSV or JSON format.
        
        Exports all audit logs within the specified date range with optional filters.
        Includes all fields and metadata for comprehensive audit trails.
        
        Args:
            start_date: Start date for export
            end_date: End date for export
            format: Export format ('json' or 'csv')
            user_id: Optional filter by user ID
            action: Optional filter by action
            resource_type: Optional filter by resource type
            
        Returns:
            Exported data as bytes (UTF-8 encoded)
            
        Example:
            data = await audit_engine.export_audit_log(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                format='csv'
            )
        """
        # Build query
        query = select(AuditLog)
        conditions = [
            AuditLog.created_at >= start_date,
            AuditLog.created_at <= end_date,
        ]
        
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        
        if action:
            conditions.append(AuditLog.action == action)
        
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        
        query = query.where(and_(*conditions))
        query = query.order_by(AuditLog.created_at.asc())
        
        # Execute query
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        # Export based on format
        if format == 'csv':
            return self._export_to_csv(logs)
        else:  # json
            return self._export_to_json(logs)
    
    def _export_to_csv(self, logs: List[AuditLog]) -> bytes:
        """
        Export audit logs to CSV format.
        
        Args:
            logs: List of audit log records
            
        Returns:
            CSV data as bytes
        """
        output = io.StringIO()
        
        if not logs:
            return b''
        
        # Define CSV columns
        fieldnames = [
            'id',
            'user_id',
            'action',
            'resource_type',
            'resource_id',
            'ip_address',
            'created_at',
            'metadata',
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for log in logs:
            writer.writerow({
                'id': str(log.id),
                'user_id': str(log.user_id) if log.user_id else '',
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': str(log.resource_id) if log.resource_id else '',
                'ip_address': log.ip_address,
                'created_at': log.created_at.isoformat(),
                'metadata': json.dumps(log.metadata_),
            })
        
        return output.getvalue().encode('utf-8')
    
    def _export_to_json(self, logs: List[AuditLog]) -> bytes:
        """
        Export audit logs to JSON format.
        
        Args:
            logs: List of audit log records
            
        Returns:
            JSON data as bytes
        """
        data = []
        
        for log in logs:
            data.append({
                'id': str(log.id),
                'user_id': str(log.user_id) if log.user_id else None,
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': str(log.resource_id) if log.resource_id else None,
                'metadata': log.metadata_,
                'ip_address': log.ip_address,
                'created_at': log.created_at.isoformat(),
            })
        
        return json.dumps(data, indent=2).encode('utf-8')
