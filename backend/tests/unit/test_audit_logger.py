"""Unit tests for audit logging module."""

import pytest
from datetime import datetime
from uuid import uuid4

from app.core.audit.logger import (
    AuditEvent,
    AuditLogFormatter,
    PIIMasker,
    SensitiveDataFilter,
)


class TestPIIMasker:
    """Tests for PII masking functionality."""
    
    def test_mask_mrn(self):
        """Test MRN masking shows only first and last parts."""
        mrn = "MRN-20240115-1234"
        masked = PIIMasker.mask_mrn(mrn)
        assert masked == "MRN-****-1234"
        assert "20240115" not in masked
    
    def test_mask_mrn_invalid(self):
        """Test MRN masking handles invalid input."""
        assert PIIMasker.mask_mrn("") == "***"
        assert PIIMasker.mask_mrn("short") == "***"
        assert PIIMasker.mask_mrn("invalid-format") == "***"
    
    def test_mask_email(self):
        """Test email masking shows only first 2 chars and domain."""
        email = "john.doe@example.com"
        masked = PIIMasker.mask_email(email)
        assert masked == "jo***@example.com"
        assert "john.doe" not in masked
        assert "@example.com" in masked
    
    def test_mask_email_short(self):
        """Test email masking handles short local parts."""
        email = "ab@example.com"
        masked = PIIMasker.mask_email(email)
        assert masked == "a***@example.com"
    
    def test_mask_email_invalid(self):
        """Test email masking handles invalid input."""
        assert PIIMasker.mask_email("") == "***"
        assert PIIMasker.mask_email("no-at-sign") == "***"
    
    def test_mask_text_with_mrn(self):
        """Test text masking replaces MRNs."""
        text = "Patient MRN-20240115-1234 was admitted"
        masked = PIIMasker.mask_text(text)
        assert "MRN-****-1234" in masked
        assert "20240115" not in masked
    
    def test_mask_text_with_email(self):
        """Test text masking replaces emails."""
        text = "Contact john.doe@example.com for details"
        masked = PIIMasker.mask_text(text)
        assert "jo***@example.com" in masked
        assert "john.doe" not in masked
    
    def test_mask_text_with_multiple_pii(self):
        """Test text masking handles multiple PII instances."""
        text = "Patient MRN-20240115-1234 (john.doe@example.com) and MRN-20240116-5678"
        masked = PIIMasker.mask_text(text)
        assert "MRN-****-1234" in masked
        assert "MRN-****-5678" in masked
        assert "jo***@example.com" in masked
        assert "20240115" not in masked
        assert "john.doe" not in masked
    
    def test_mask_dict_simple(self):
        """Test dictionary masking for simple values."""
        data = {
            "mrn": "MRN-20240115-1234",
            "email": "john.doe@example.com",
            "name": "John Doe"
        }
        masked = PIIMasker.mask_dict(data)
        assert masked["mrn"] == "MRN-****-1234"
        assert masked["email"] == "jo***@example.com"
        assert masked["name"] == "John Doe"
    
    def test_mask_dict_nested(self):
        """Test dictionary masking for nested structures."""
        data = {
            "patient": {
                "mrn": "MRN-20240115-1234",
                "contact": {
                    "email": "john.doe@example.com"
                }
            }
        }
        masked = PIIMasker.mask_dict(data)
        assert masked["patient"]["mrn"] == "MRN-****-1234"
        assert masked["patient"]["contact"]["email"] == "jo***@example.com"
    
    def test_mask_dict_with_lists(self):
        """Test dictionary masking handles lists."""
        data = {
            "patients": [
                {"mrn": "MRN-20240115-1234"},
                {"mrn": "MRN-20240116-5678"}
            ]
        }
        masked = PIIMasker.mask_dict(data)
        assert masked["patients"][0]["mrn"] == "MRN-****-1234"
        assert masked["patients"][1]["mrn"] == "MRN-****-5678"


class TestSensitiveDataFilter:
    """Tests for sensitive data filtering."""
    
    def test_filter_password_field(self):
        """Test password fields are redacted."""
        data = {
            "username": "john",
            "password": "secret123",
            "email": "john@example.com"
        }
        filtered = SensitiveDataFilter.filter_dict(data)
        assert filtered["password"] == "[REDACTED]"
        assert filtered["username"] == "john"
        assert filtered["email"] == "john@example.com"
    
    def test_filter_multiple_sensitive_fields(self):
        """Test multiple sensitive fields are redacted."""
        data = {
            "password": "secret123",
            "old_password": "old_secret",
            "new_password": "new_secret",
            "ssn": "123-45-6789",
            "credit_card": "4111-1111-1111-1111"
        }
        filtered = SensitiveDataFilter.filter_dict(data)
        assert filtered["password"] == "[REDACTED]"
        assert filtered["old_password"] == "[REDACTED]"
        assert filtered["new_password"] == "[REDACTED]"
        assert filtered["ssn"] == "[REDACTED]"
        assert filtered["credit_card"] == "[REDACTED]"
    
    def test_filter_nested_sensitive_data(self):
        """Test nested sensitive data is filtered."""
        data = {
            "user": {
                "name": "John",
                "password": "secret123"
            }
        }
        filtered = SensitiveDataFilter.filter_dict(data)
        assert filtered["user"]["password"] == "[REDACTED]"
        assert filtered["user"]["name"] == "John"
    
    def test_contains_ssn(self):
        """Test SSN pattern detection."""
        assert SensitiveDataFilter.contains_ssn("123-45-6789")
        assert not SensitiveDataFilter.contains_ssn("123-456-789")
        assert not SensitiveDataFilter.contains_ssn("no ssn here")
    
    def test_contains_credit_card(self):
        """Test credit card pattern detection."""
        assert SensitiveDataFilter.contains_credit_card("4111-1111-1111-1111")
        assert SensitiveDataFilter.contains_credit_card("4111111111111111")
        assert not SensitiveDataFilter.contains_credit_card("1234")
    
    def test_filter_ssn_in_text(self):
        """Test SSN in text values is redacted."""
        data = {
            "notes": "Patient SSN is 123-45-6789"
        }
        filtered = SensitiveDataFilter.filter_dict(data)
        assert filtered["notes"] == "[REDACTED]"
    
    def test_filter_credit_card_in_text(self):
        """Test credit card in text values is redacted."""
        data = {
            "payment": "Card number: 4111-1111-1111-1111"
        }
        filtered = SensitiveDataFilter.filter_dict(data)
        assert filtered["payment"] == "[REDACTED]"
    
    def test_filter_text_ssn(self):
        """Test SSN removal from text."""
        text = "Patient SSN: 123-45-6789"
        filtered = SensitiveDataFilter.filter_text(text)
        assert "123-45-6789" not in filtered
        assert "[REDACTED-SSN]" in filtered
    
    def test_filter_text_credit_card(self):
        """Test credit card removal from text."""
        text = "Card: 4111-1111-1111-1111"
        filtered = SensitiveDataFilter.filter_text(text)
        assert "4111-1111-1111-1111" not in filtered
        assert "[REDACTED-CC]" in filtered


class TestAuditEvent:
    """Tests for AuditEvent data structure."""
    
    def test_audit_event_creation(self):
        """Test creating an audit event."""
        event_id = uuid4()
        user_id = uuid4()
        request_id = uuid4()
        timestamp = datetime.utcnow()
        
        event = AuditEvent(
            event_id=event_id,
            timestamp=timestamp,
            user_id=user_id,
            action="patient.create",
            resource_type="patient",
            resource_id=uuid4(),
            status="success",
            metadata={"key": "value"},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            request_id=request_id,
        )
        
        assert event.event_id == event_id
        assert event.user_id == user_id
        assert event.action == "patient.create"
        assert event.status == "success"
    
    def test_audit_event_to_dict(self):
        """Test converting audit event to dictionary."""
        event = AuditEvent(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            action="test.action",
            resource_type="test",
            status="success",
            ip_address="192.168.1.1",
            user_agent="Test",
            request_id=uuid4(),
        )
        
        event_dict = event.to_dict()
        assert "event_id" in event_dict
        assert "action" in event_dict
        assert "status" in event_dict
        assert event_dict["action"] == "test.action"


class TestAuditLogFormatter:
    """Tests for audit log formatting."""
    
    def test_format_event_basic(self):
        """Test basic event formatting."""
        event = AuditEvent(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            action="test.action",
            resource_type="test",
            status="success",
            ip_address="192.168.1.1",
            user_agent="Test",
            request_id=uuid4(),
            metadata={"key": "value"},
        )
        
        formatted = AuditLogFormatter.format_event(event)
        assert "action" in formatted
        assert "metadata" in formatted
        assert formatted["action"] == "test.action"
    
    def test_format_event_with_pii(self):
        """Test event formatting masks PII."""
        event = AuditEvent(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            action="patient.create",
            resource_type="patient",
            status="success",
            ip_address="192.168.1.1",
            user_agent="Test",
            request_id=uuid4(),
            metadata={
                "mrn": "MRN-20240115-1234",
                "email": "john.doe@example.com"
            },
        )
        
        formatted = AuditLogFormatter.format_event(event)
        assert formatted["metadata"]["mrn"] == "MRN-****-1234"
        assert formatted["metadata"]["email"] == "jo***@example.com"
    
    def test_format_event_with_sensitive_data(self):
        """Test event formatting removes sensitive data."""
        event = AuditEvent(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
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
            },
        )
        
        formatted = AuditLogFormatter.format_event(event)
        assert formatted["metadata"]["password"] == "[REDACTED]"
        assert formatted["metadata"]["ssn"] == "[REDACTED]"
        assert formatted["metadata"]["username"] == "john"
    
    def test_format_for_storage_adds_required_fields(self):
        """Test format_for_storage ensures required metadata fields."""
        event = AuditEvent(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            action="test.action",
            resource_type="test",
            status="success",
            ip_address="192.168.1.1",
            user_agent="Test",
            request_id=uuid4(),
            metadata={},
        )
        
        formatted = AuditLogFormatter.format_for_storage(event)
        assert "request_id" in formatted["metadata"]
        assert "endpoint" in formatted["metadata"]
        assert "method" in formatted["metadata"]
        assert "status_code" in formatted["metadata"]
