"""Unit tests for AuditEngine service."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.core.audit.service import AuditEngine
from app.schemas.audit import AuditQuery


@pytest.mark.asyncio
class TestAuditEngine:
    """Tests for AuditEngine service."""
    
    async def test_log_action_creates_audit_log(self, db_session):
        """Test log_action creates an audit log entry."""
        engine = AuditEngine(db_session)
        user_id = uuid4()
        request_id = uuid4()
        
        audit_log = await engine.log_action(
            user_id=user_id,
            action="patient.create",
            resource_type="patient",
            status="success",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            request_id=request_id,
            metadata={
                "endpoint": "/api/v1/patients",
                "method": "POST",
                "status_code": 201
            }
        )
        
        assert audit_log.id is not None
        assert audit_log.user_id == user_id
        assert audit_log.action == "patient.create"
        assert audit_log.resource_type == "patient"
        assert audit_log.status == "success"
        assert audit_log.ip_address == "192.168.1.1"
        assert "endpoint" in audit_log.metadata_
    
    async def test_log_action_masks_pii(self, db_session):
        """Test log_action masks PII in metadata."""
        engine = AuditEngine(db_session)
        
        audit_log = await engine.log_action(
            user_id=uuid4(),
            action="patient.create",
            resource_type="patient",
            status="success",
            ip_address="192.168.1.1",
            user_agent="Test",
            request_id=uuid4(),
            metadata={
                "mrn": "MRN-20240115-1234",
                "email": "john.doe@example.com"
            }
        )
        
        # PII should be masked
        assert audit_log.metadata_["mrn"] == "MRN-****-1234"
        assert audit_log.metadata_["email"] == "jo***@example.com"
    
    async def test_log_action_filters_sensitive_data(self, db_session):
        """Test log_action filters sensitive data."""
        engine = AuditEngine(db_session)
        
        audit_log = await engine.log_action(
            user_id=uuid4(),
            action="user.update",
            resource_type="user",
            status="success",
            ip_address="192.168.1.1",
            user_agent="Test",
            request_id=uuid4(),
            metadata={
                "username": "john",
                "password": "secret123",
                "ssn": "123-45-6789"
            }
        )
        
        # Sensitive data should be redacted
        assert audit_log.metadata_["password"] == "[REDACTED]"
        assert audit_log.metadata_["ssn"] == "[REDACTED]"
        assert audit_log.metadata_["username"] == "john"
    
    async def test_log_auth_event_success(self, db_session):
        """Test log_auth_event for successful authentication."""
        engine = AuditEngine(db_session)
        user_id = uuid4()
        
        audit_log = await engine.log_auth_event(
            user_id=user_id,
            action="auth.login.success",
            result=True,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            request_id=uuid4(),
            metadata={"email": "user@example.com"}
        )
        
        assert audit_log.action == "auth.login.success"
        assert audit_log.resource_type == "session"
        assert audit_log.status == "success"
    
    async def test_log_auth_event_failure(self, db_session):
        """Test log_auth_event for failed authentication."""
        engine = AuditEngine(db_session)
        
        audit_log = await engine.log_auth_event(
            user_id=None,  # No user ID for failed login
            action="auth.login.failure",
            result=False,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            request_id=uuid4(),
            metadata={"email": "user@example.com", "reason": "invalid_password"}
        )
        
        assert audit_log.action == "auth.login.failure"
        assert audit_log.status == "failure"
        assert audit_log.user_id is None
    
    async def test_log_data_access(self, db_session):
        """Test log_data_access for data access events."""
        engine = AuditEngine(db_session)
        user_id = uuid4()
        resource_id = uuid4()
        
        audit_log = await engine.log_data_access(
            user_id=user_id,
            resource="patient",
            action="read",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            request_id=uuid4(),
            resource_id=resource_id,
            metadata={"fields": ["name", "mrn", "dob"]}
        )
        
        assert audit_log.action == "patient.read"
        assert audit_log.resource_type == "patient"
        assert audit_log.resource_id == resource_id
        assert audit_log.status == "success"
    
    async def test_query_audit_log_no_filters(self, db_session):
        """Test querying audit logs without filters."""
        engine = AuditEngine(db_session)
        
        # Create some audit logs
        for i in range(5):
            await engine.log_action(
                user_id=uuid4(),
                action=f"test.action{i}",
                resource_type="test",
                status="success",
                ip_address="192.168.1.1",
                user_agent="Test",
                request_id=uuid4(),
            )
        
        # Query all logs
        criteria = AuditQuery(page=1, page_size=10)
        logs, total = await engine.query_audit_log(criteria)
        
        assert len(logs) >= 5
        assert total >= 5
    
    async def test_query_audit_log_by_user(self, db_session):
        """Test querying audit logs by user ID."""
        engine = AuditEngine(db_session)
        user_id = uuid4()
        
        # Create logs for specific user
        for i in range(3):
            await engine.log_action(
                user_id=user_id,
                action=f"test.action{i}",
                resource_type="test",
                status="success",
                ip_address="192.168.1.1",
                user_agent="Test",
                request_id=uuid4(),
            )
        
        # Create logs for other users
        for i in range(2):
            await engine.log_action(
                user_id=uuid4(),
                action=f"test.other{i}",
                resource_type="test",
                status="success",
                ip_address="192.168.1.1",
                user_agent="Test",
                request_id=uuid4(),
            )
        
        # Query logs for specific user
        criteria = AuditQuery(user_id=user_id, page=1, page_size=10)
        logs, total = await engine.query_audit_log(criteria)
        
        assert len(logs) == 3
        assert all(log.user_id == user_id for log in logs)
    
    async def test_query_audit_log_by_action(self, db_session):
        """Test querying audit logs by action."""
        engine = AuditEngine(db_session)
        
        # Create logs with different actions
        await engine.log_action(
            user_id=uuid4(),
            action="patient.create",
            resource_type="patient",
            status="success",
            ip_address="192.168.1.1",
            user_agent="Test",
            request_id=uuid4(),
        )
        
        await engine.log_action(
            user_id=uuid4(),
            action="patient.update",
            resource_type="patient",
            status="success",
            ip_address="192.168.1.1",
            user_agent="Test",
            request_id=uuid4(),
        )
        
        # Query logs for specific action
        criteria = AuditQuery(action="patient.create", page=1, page_size=10)
        logs, total = await engine.query_audit_log(criteria)
        
        assert all(log.action == "patient.create" for log in logs)
    
    async def test_query_audit_log_by_date_range(self, db_session):
        """Test querying audit logs by date range."""
        engine = AuditEngine(db_session)
        
        # Create a log
        await engine.log_action(
            user_id=uuid4(),
            action="test.action",
            resource_type="test",
            status="success",
            ip_address="192.168.1.1",
            user_agent="Test",
            request_id=uuid4(),
        )
        
        # Query with date range
        now = datetime.utcnow()
        criteria = AuditQuery(
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
            page=1,
            page_size=10
        )
        logs, total = await engine.query_audit_log(criteria)
        
        assert len(logs) >= 1
    
    async def test_query_audit_log_pagination(self, db_session):
        """Test audit log pagination."""
        engine = AuditEngine(db_session)
        
        # Create multiple logs
        for i in range(15):
            await engine.log_action(
                user_id=uuid4(),
                action=f"test.action{i}",
                resource_type="test",
                status="success",
                ip_address="192.168.1.1",
                user_agent="Test",
                request_id=uuid4(),
            )
        
        # Query first page
        criteria = AuditQuery(page=1, page_size=10)
        logs_page1, total = await engine.query_audit_log(criteria)
        
        assert len(logs_page1) == 10
        assert total >= 15
        
        # Query second page
        criteria = AuditQuery(page=2, page_size=10)
        logs_page2, total = await engine.query_audit_log(criteria)
        
        assert len(logs_page2) >= 5
    
    async def test_export_audit_log_json(self, db_session):
        """Test exporting audit logs to JSON."""
        engine = AuditEngine(db_session)
        
        # Create some logs
        for i in range(3):
            await engine.log_action(
                user_id=uuid4(),
                action=f"test.action{i}",
                resource_type="test",
                status="success",
                ip_address="192.168.1.1",
                user_agent="Test",
                request_id=uuid4(),
            )
        
        # Export to JSON
        now = datetime.utcnow()
        data = await engine.export_audit_log(
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
            format='json'
        )
        
        assert isinstance(data, bytes)
        assert len(data) > 0
        
        # Verify it's valid JSON
        import json
        parsed = json.loads(data.decode('utf-8'))
        assert isinstance(parsed, list)
        assert len(parsed) >= 3
    
    async def test_export_audit_log_csv(self, db_session):
        """Test exporting audit logs to CSV."""
        engine = AuditEngine(db_session)
        
        # Create some logs
        for i in range(3):
            await engine.log_action(
                user_id=uuid4(),
                action=f"test.action{i}",
                resource_type="test",
                status="success",
                ip_address="192.168.1.1",
                user_agent="Test",
                request_id=uuid4(),
            )
        
        # Export to CSV
        now = datetime.utcnow()
        data = await engine.export_audit_log(
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
            format='csv'
        )
        
        assert isinstance(data, bytes)
        assert len(data) > 0
        
        # Verify it's valid CSV
        csv_text = data.decode('utf-8')
        lines = csv_text.strip().split('\n')
        assert len(lines) >= 4  # Header + 3 data rows
        assert 'id,user_id,action' in lines[0]
    
    async def test_export_audit_log_with_filters(self, db_session):
        """Test exporting audit logs with filters."""
        engine = AuditEngine(db_session)
        user_id = uuid4()
        
        # Create logs for specific user
        for i in range(2):
            await engine.log_action(
                user_id=user_id,
                action="patient.create",
                resource_type="patient",
                status="success",
                ip_address="192.168.1.1",
                user_agent="Test",
                request_id=uuid4(),
            )
        
        # Create logs for other users
        await engine.log_action(
            user_id=uuid4(),
            action="queue.update",
            resource_type="queue",
            status="success",
            ip_address="192.168.1.1",
            user_agent="Test",
            request_id=uuid4(),
        )
        
        # Export with filters
        now = datetime.utcnow()
        data = await engine.export_audit_log(
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
            format='json',
            user_id=user_id,
            action="patient.create"
        )
        
        import json
        parsed = json.loads(data.decode('utf-8'))
        assert len(parsed) == 2
        assert all(log['action'] == 'patient.create' for log in parsed)
