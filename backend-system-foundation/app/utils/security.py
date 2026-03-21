"""Security utilities for XSS prevention and input sanitization."""

import html
import re
from typing import Any, Dict, List, Union


class XSSProtection:
    """
    XSS (Cross-Site Scripting) protection utilities.
    
    Provides output encoding and input sanitization to prevent XSS attacks.
    """
    
    # Dangerous HTML tags that should be stripped
    DANGEROUS_TAGS = [
        "script", "iframe", "object", "embed", "applet",
        "meta", "link", "style", "base", "form"
    ]
    
    # Dangerous attributes that can execute JavaScript
    DANGEROUS_ATTRS = [
        "onclick", "onload", "onerror", "onmouseover", "onmouseout",
        "onkeydown", "onkeyup", "onkeypress", "onfocus", "onblur",
        "onchange", "onsubmit", "javascript:"
    ]
    
    @staticmethod
    def encode_html(text: str) -> str:
        """
        Encode HTML special characters to prevent XSS.
        
        Converts: < > & " ' to HTML entities
        
        Args:
            text: Input text to encode
            
        Returns:
            HTML-encoded text safe for output
        """
        if not isinstance(text, str):
            return text
        
        return html.escape(text, quote=True)
    
    @staticmethod
    def encode_html_attribute(text: str) -> str:
        """
        Encode text for safe use in HTML attributes.
        
        Args:
            text: Input text to encode
            
        Returns:
            Encoded text safe for HTML attributes
        """
        if not isinstance(text, str):
            return text
        
        # Encode HTML entities and remove quotes
        encoded = html.escape(text, quote=True)
        # Additional encoding for attribute context
        encoded = encoded.replace("'", "&#x27;")
        encoded = encoded.replace("`", "&#x60;")
        
        return encoded
    
    @staticmethod
    def strip_dangerous_tags(text: str) -> str:
        """
        Remove dangerous HTML tags from text.
        
        Args:
            text: Input text potentially containing HTML
            
        Returns:
            Text with dangerous tags removed
        """
        if not isinstance(text, str):
            return text
        
        # Remove dangerous tags
        for tag in XSSProtection.DANGEROUS_TAGS:
            # Remove opening and closing tags
            pattern = re.compile(f"<{tag}[^>]*>.*?</{tag}>", re.IGNORECASE | re.DOTALL)
            text = pattern.sub("", text)
            # Remove self-closing tags
            pattern = re.compile(f"<{tag}[^>]*/>", re.IGNORECASE)
            text = pattern.sub("", text)
        
        return text
    
    @staticmethod
    def strip_dangerous_attributes(text: str) -> str:
        """
        Remove dangerous HTML attributes from text.
        
        Args:
            text: Input text potentially containing HTML
            
        Returns:
            Text with dangerous attributes removed
        """
        if not isinstance(text, str):
            return text
        
        # Remove dangerous event handlers and javascript: URLs
        for attr in XSSProtection.DANGEROUS_ATTRS:
            pattern = re.compile(f'{attr}\\s*=\\s*["\'][^"\']*["\']', re.IGNORECASE)
            text = pattern.sub("", text)
        
        return text
    
    @staticmethod
    def sanitize_input(text: str, allow_html: bool = False) -> str:
        """
        Sanitize user input to prevent XSS attacks.
        
        Args:
            text: Input text to sanitize
            allow_html: If False, encode all HTML. If True, only remove dangerous content.
            
        Returns:
            Sanitized text safe for storage and output
        """
        if not isinstance(text, str):
            return text
        
        if not allow_html:
            # Encode all HTML
            return XSSProtection.encode_html(text)
        else:
            # Remove dangerous tags and attributes but allow safe HTML
            text = XSSProtection.strip_dangerous_attributes(text)
            text = XSSProtection.strip_dangerous_tags(text)
            return text
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any], allow_html: bool = False) -> Dict[str, Any]:
        """
        Recursively sanitize all string values in a dictionary.
        
        Args:
            data: Dictionary to sanitize
            allow_html: If False, encode all HTML. If True, only remove dangerous content.
            
        Returns:
            Dictionary with sanitized string values
        """
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = XSSProtection.sanitize_input(value, allow_html)
            elif isinstance(value, dict):
                sanitized[key] = XSSProtection.sanitize_dict(value, allow_html)
            elif isinstance(value, list):
                sanitized[key] = XSSProtection.sanitize_list(value, allow_html)
            else:
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def sanitize_list(data: List[Any], allow_html: bool = False) -> List[Any]:
        """
        Recursively sanitize all string values in a list.
        
        Args:
            data: List to sanitize
            allow_html: If False, encode all HTML. If True, only remove dangerous content.
            
        Returns:
            List with sanitized string values
        """
        if not isinstance(data, list):
            return data
        
        sanitized = []
        for item in data:
            if isinstance(item, str):
                sanitized.append(XSSProtection.sanitize_input(item, allow_html))
            elif isinstance(item, dict):
                sanitized.append(XSSProtection.sanitize_dict(item, allow_html))
            elif isinstance(item, list):
                sanitized.append(XSSProtection.sanitize_list(item, allow_html))
            else:
                sanitized.append(item)
        
        return sanitized


class SQLInjectionProtection:
    """
    SQL injection protection utilities.
    
    Provides validation and verification for SQL injection prevention.
    Note: Primary protection is through SQLAlchemy ORM and parameterized queries.
    """
    
    # SQL keywords that might indicate injection attempts
    SQL_KEYWORDS = [
        "SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "CREATE",
        "ALTER", "EXEC", "EXECUTE", "UNION", "DECLARE", "CAST",
        "CONVERT", "SCRIPT", "JAVASCRIPT", "VBSCRIPT"
    ]
    
    # SQL comment patterns
    SQL_COMMENT_PATTERNS = [
        "--", "/*", "*/", "#", "xp_", "sp_"
    ]
    
    @staticmethod
    def detect_sql_injection(text: str) -> bool:
        """
        Detect potential SQL injection attempts in input.
        
        This is a defense-in-depth measure. Primary protection is through
        parameterized queries in SQLAlchemy.
        
        Args:
            text: Input text to check
            
        Returns:
            True if potential SQL injection detected, False otherwise
        """
        if not isinstance(text, str):
            return False
        
        text_upper = text.upper()
        
        # Check for SQL keywords
        for keyword in SQLInjectionProtection.SQL_KEYWORDS:
            if keyword in text_upper:
                # Check if it's part of a SQL statement (has spaces or special chars around it)
                pattern = re.compile(f"\\b{keyword}\\b", re.IGNORECASE)
                if pattern.search(text):
                    return True
        
        # Check for SQL comment patterns
        for pattern in SQLInjectionProtection.SQL_COMMENT_PATTERNS:
            if pattern in text:
                return True
        
        # Check for common SQL injection patterns
        injection_patterns = [
            r"'\s*OR\s*'",  # ' OR '
            r"'\s*OR\s*1\s*=\s*1",  # ' OR 1=1
            r";\s*DROP\s+TABLE",  # ; DROP TABLE
            r";\s*DELETE\s+FROM",  # ; DELETE FROM
            r"UNION\s+SELECT",  # UNION SELECT
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def validate_identifier(identifier: str) -> bool:
        """
        Validate that a string is a safe SQL identifier (table/column name).
        
        Args:
            identifier: Identifier to validate
            
        Returns:
            True if safe, False otherwise
        """
        if not isinstance(identifier, str):
            return False
        
        # Only allow alphanumeric characters and underscores
        # Must start with a letter
        pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
        return bool(pattern.match(identifier))


class SecretsProtection:
    """
    Secrets protection utilities.
    
    Provides detection and masking of sensitive data in logs and outputs.
    """
    
    # Patterns for sensitive data
    PATTERNS = {
        "password": re.compile(r"password[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.IGNORECASE),
        "api_key": re.compile(r"api[_-]?key[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.IGNORECASE),
        "secret": re.compile(r"secret[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.IGNORECASE),
        "token": re.compile(r"token[\"']?\s*[:=]\s*[\"']?([^\"'\s,}]+)", re.IGNORECASE),
        "jwt": re.compile(r"Bearer\s+([A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*)", re.IGNORECASE),
        "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    }
    
    @staticmethod
    def mask_secrets(text: str) -> str:
        """
        Mask sensitive data in text for safe logging.
        
        Args:
            text: Text potentially containing secrets
            
        Returns:
            Text with secrets masked
        """
        if not isinstance(text, str):
            return text
        
        masked = text
        
        # Mask each pattern
        for secret_type, pattern in SecretsProtection.PATTERNS.items():
            masked = pattern.sub(f"{secret_type}=***REDACTED***", masked)
        
        return masked
    
    @staticmethod
    def detect_hardcoded_secrets(text: str) -> List[str]:
        """
        Detect potential hardcoded secrets in code.
        
        Args:
            text: Code or configuration text to check
            
        Returns:
            List of detected secret types
        """
        if not isinstance(text, str):
            return []
        
        detected = []
        
        for secret_type, pattern in SecretsProtection.PATTERNS.items():
            if pattern.search(text):
                detected.append(secret_type)
        
        return detected
