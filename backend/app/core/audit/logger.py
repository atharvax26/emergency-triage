"""Structured logging module with PII masking and sensitive data exclusion."""

import re
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID


class AuditEvent:
    """
    Data structure for audit events.
    
    Represents a single auditable action in the system with all required metadata.
    
    Attributes:
        event_id: Unique identifier for this event
        timestamp: When the event occurred
        user_id: ID of the user who performed the action (None for system events)
        action: Action performed (e.g., 'auth.login.success', 'patient.create')
        resource_type: Type of resource affected
        resource_id: ID of the affected resource (None if not applicable)
        status: Result status ('success', 'failure', 'error')
        metadata: Additional context and details
        ip_address: IP address of the request origin
        user_agent: User agent string from the request
        request_id: Correlation ID for request tracking
    """
    
    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        action: str,
        resource_type: str,
        status: str,
        ip_address: str,
        user_agent: str,
        request_id: UUID,
        user_id: Optional[UUID] = None,
        resource_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize an audit event."""
        self.event_id = event_id
        self.timestamp = timestamp
        self.user_id = user_id
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.status = status
        self.metadata = metadata or {}
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.request_id = request_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary."""
        return {
            "event_id": str(self.event_id),
            "timestamp": self.timestamp.isoformat(),
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "status": self.status,
            "metadata": self.metadata,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": str(self.request_id),
        }


class PIIMasker:
    """
    Utility class for masking PII in logs.
    
    Implements partial masking for MRN and email addresses to protect patient privacy
    while maintaining some identifiability for audit purposes.
    """
    
    # Patterns for detecting sensitive data
    MRN_PATTERN = re.compile(r'MRN-\d{8}-\d{4}')
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    CREDIT_CARD_PATTERN = re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b')
    
    @staticmethod
    def mask_mrn(mrn: str) -> str:
        """
        Mask MRN to show only first 4 and last 4 characters.
        
        Example: MRN-20240115-1234 -> MRN-****-1234
        
        Args:
            mrn: Medical Record Number in format MRN-YYYYMMDD-XXXX
            
        Returns:
            Masked MRN string
        """
        if not mrn or len(mrn) < 8:
            return "***"
        
        # Format: MRN-YYYYMMDD-XXXX
        # Show: MRN-****-XXXX
        parts = mrn.split('-')
        if len(parts) == 3:
            return f"{parts[0]}-****-{parts[2]}"
        return "***"
    
    @staticmethod
    def mask_email(email: str) -> str:
        """
        Mask email to show only first 2 characters and domain.
        
        Example: john.doe@example.com -> jo***@example.com
        
        Args:
            email: Email address
            
        Returns:
            Masked email string
        """
        if not email or '@' not in email:
            return "***"
        
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            masked_local = local[0] + '***'
        else:
            masked_local = local[:2] + '***'
        
        return f"{masked_local}@{domain}"
    
    @staticmethod
    def mask_text(text: str) -> str:
        """
        Mask all PII in a text string.
        
        Replaces MRNs and emails with masked versions.
        
        Args:
            text: Text that may contain PII
            
        Returns:
            Text with PII masked
        """
        if not text:
            return text
        
        # Mask MRNs
        text = PIIMasker.MRN_PATTERN.sub(
            lambda m: PIIMasker.mask_mrn(m.group(0)),
            text
        )
        
        # Mask emails
        text = PIIMasker.EMAIL_PATTERN.sub(
            lambda m: PIIMasker.mask_email(m.group(0)),
            text
        )
        
        return text
    
    @staticmethod
    def mask_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively mask PII in a dictionary.
        
        Args:
            data: Dictionary that may contain PII
            
        Returns:
            Dictionary with PII masked
        """
        if not isinstance(data, dict):
            return data
        
        masked = {}
        for key, value in data.items():
            if isinstance(value, str):
                masked[key] = PIIMasker.mask_text(value)
            elif isinstance(value, dict):
                masked[key] = PIIMasker.mask_dict(value)
            elif isinstance(value, list):
                masked[key] = [
                    PIIMasker.mask_dict(item) if isinstance(item, dict)
                    else PIIMasker.mask_text(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                masked[key] = value
        
        return masked


class SensitiveDataFilter:
    """
    Utility class for excluding sensitive data from logs.
    
    Removes passwords, SSNs, and credit card numbers completely from log data
    to ensure they are never stored in audit logs.
    """
    
    # Field names that should be excluded
    SENSITIVE_FIELDS = {
        'password',
        'password_hash',
        'old_password',
        'new_password',
        'confirm_password',
        'ssn',
        'social_security_number',
        'credit_card',
        'card_number',
        'cvv',
        'security_code',
    }
    
    @staticmethod
    def contains_ssn(text: str) -> bool:
        """Check if text contains an SSN pattern."""
        return bool(PIIMasker.SSN_PATTERN.search(text))
    
    @staticmethod
    def contains_credit_card(text: str) -> bool:
        """Check if text contains a credit card pattern."""
        return bool(PIIMasker.CREDIT_CARD_PATTERN.search(text))
    
    @staticmethod
    def filter_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively remove sensitive data from a dictionary.
        
        Args:
            data: Dictionary that may contain sensitive data
            
        Returns:
            Dictionary with sensitive data removed
        """
        if not isinstance(data, dict):
            return data
        
        filtered = {}
        for key, value in data.items():
            # Skip sensitive fields entirely
            if key.lower() in SensitiveDataFilter.SENSITIVE_FIELDS:
                filtered[key] = "[REDACTED]"
                continue
            
            # Recursively filter nested dictionaries
            if isinstance(value, dict):
                filtered[key] = SensitiveDataFilter.filter_dict(value)
            elif isinstance(value, list):
                filtered[key] = [
                    SensitiveDataFilter.filter_dict(item) if isinstance(item, dict)
                    else "[REDACTED]" if isinstance(item, str) and (
                        SensitiveDataFilter.contains_ssn(item) or
                        SensitiveDataFilter.contains_credit_card(item)
                    )
                    else item
                    for item in value
                ]
            elif isinstance(value, str):
                # Check for SSN or credit card in string values
                if SensitiveDataFilter.contains_ssn(value) or \
                   SensitiveDataFilter.contains_credit_card(value):
                    filtered[key] = "[REDACTED]"
                else:
                    filtered[key] = value
            else:
                filtered[key] = value
        
        return filtered
    
    @staticmethod
    def filter_text(text: str) -> str:
        """
        Remove sensitive data patterns from text.
        
        Args:
            text: Text that may contain sensitive data
            
        Returns:
            Text with sensitive data removed
        """
        if not text:
            return text
        
        # Replace SSN patterns
        text = PIIMasker.SSN_PATTERN.sub('[REDACTED-SSN]', text)
        
        # Replace credit card patterns
        text = PIIMasker.CREDIT_CARD_PATTERN.sub('[REDACTED-CC]', text)
        
        return text


class AuditLogFormatter:
    """
    Formats audit events for logging with PII masking and sensitive data exclusion.
    
    Ensures all logged data is compliant with privacy requirements while maintaining
    audit trail integrity.
    """
    
    @staticmethod
    def format_event(event: AuditEvent) -> Dict[str, Any]:
        """
        Format an audit event for logging.
        
        Applies PII masking and sensitive data filtering to ensure compliance.
        
        Args:
            event: Audit event to format
            
        Returns:
            Formatted event dictionary ready for logging
        """
        # Convert event to dictionary
        event_dict = event.to_dict()
        
        # Filter sensitive data first (complete removal)
        event_dict['metadata'] = SensitiveDataFilter.filter_dict(event_dict['metadata'])
        
        # Then mask PII (partial masking)
        event_dict['metadata'] = PIIMasker.mask_dict(event_dict['metadata'])
        
        # Ensure required metadata fields are present
        if 'request_id' not in event_dict['metadata']:
            event_dict['metadata']['request_id'] = str(event.request_id)
        
        return event_dict
    
    @staticmethod
    def format_for_storage(event: AuditEvent) -> Dict[str, Any]:
        """
        Format an audit event for database storage.
        
        Similar to format_event but optimized for database storage.
        
        Args:
            event: Audit event to format
            
        Returns:
            Formatted event dictionary for database storage
        """
        formatted = AuditLogFormatter.format_event(event)
        
        # Ensure metadata contains required fields
        required_fields = ['request_id', 'endpoint', 'method', 'status_code']
        for field in required_fields:
            if field not in formatted['metadata']:
                # Add placeholder if missing (should be provided by caller)
                formatted['metadata'][field] = None
        
        return formatted
