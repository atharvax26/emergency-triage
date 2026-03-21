"""Tests for security hardening implementation."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.utils.security import XSSProtection, SQLInjectionProtection, SecretsProtection
from app.utils.sql_verification import verify_sql_injection_prevention


class TestSecurityHeaders:
    """Test security headers middleware."""
    
    def test_security_headers_present(self):
        """Test that all required security headers are present."""
        client = TestClient(app)
        response = client.get("/api/v1/health")
        
        # Check Content-Security-Policy
        assert "Content-Security-Policy" in response.headers
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]
        
        # Check X-Frame-Options
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        
        # Check X-Content-Type-Options
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        # Check Referrer-Policy
        assert "Referrer-Policy" in response.headers
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        
        # Check X-XSS-Protection
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        
        # Check Permissions-Policy
        assert "Permissions-Policy" in response.headers
    
    def test_server_header_removed(self):
        """Test that Server header is removed to avoid information disclosure."""
        client = TestClient(app)
        response = client.get("/api/v1/health")
        
        # Server header should be removed
        assert "Server" not in response.headers


class TestXSSProtection:
    """Test XSS protection utilities."""
    
    def test_encode_html(self):
        """Test HTML encoding."""
        dangerous = "<script>alert('XSS')</script>"
        safe = XSSProtection.encode_html(dangerous)
        
        assert "<script>" not in safe
        assert "&lt;script&gt;" in safe
    
    def test_strip_dangerous_tags(self):
        """Test dangerous tag removal."""
        dangerous = "<div>Safe</div><script>alert('XSS')</script><p>Also safe</p>"
        safe = XSSProtection.strip_dangerous_tags(dangerous)
        
        assert "<script>" not in safe
        assert "<div>Safe</div>" in safe
        assert "<p>Also safe</p>" in safe
    
    def test_strip_dangerous_attributes(self):
        """Test dangerous attribute removal."""
        dangerous = '<img src="image.jpg" onerror="alert(\'XSS\')">'
        safe = XSSProtection.strip_dangerous_attributes(dangerous)
        
        assert "onerror" not in safe
        assert "src=" in safe
    
    def test_sanitize_input_no_html(self):
        """Test input sanitization without HTML."""
        dangerous = "<script>alert('XSS')</script>"
        safe = XSSProtection.sanitize_input(dangerous, allow_html=False)
        
        assert "<script>" not in safe
        assert "&lt;script&gt;" in safe
    
    def test_sanitize_input_with_html(self):
        """Test input sanitization with safe HTML allowed."""
        dangerous = "<p>Safe</p><script>alert('XSS')</script>"
        safe = XSSProtection.sanitize_input(dangerous, allow_html=True)
        
        assert "<script>" not in safe
        assert "<p>Safe</p>" in safe
    
    def test_sanitize_dict(self):
        """Test dictionary sanitization."""
        data = {
            "name": "<script>alert('XSS')</script>",
            "description": "Normal text",
            "nested": {
                "field": "<img onerror='alert(1)' src=x>"
            }
        }
        
        safe = XSSProtection.sanitize_dict(data)
        
        assert "<script>" not in safe["name"]
        assert safe["description"] == "Normal text"
        # When allow_html=False (default), everything is encoded
        assert "&lt;img" in safe["nested"]["field"]
        assert "onerror" in safe["nested"]["field"]  # Encoded but present
    
    def test_sanitize_list(self):
        """Test list sanitization."""
        data = [
            "<script>alert('XSS')</script>",
            "Normal text",
            {"field": "<img onerror='alert(1)' src=x>"}
        ]
        
        safe = XSSProtection.sanitize_list(data)
        
        assert "<script>" not in safe[0]
        assert safe[1] == "Normal text"
        # When allow_html=False (default), everything is encoded
        assert "&lt;img" in safe[2]["field"]
        assert "onerror" in safe[2]["field"]  # Encoded but present


class TestSQLInjectionProtection:
    """Test SQL injection protection utilities."""
    
    def test_detect_sql_injection_or_statement(self):
        """Test detection of OR-based SQL injection."""
        malicious = "admin' OR '1'='1"
        assert SQLInjectionProtection.detect_sql_injection(malicious) is True
    
    def test_detect_sql_injection_union(self):
        """Test detection of UNION-based SQL injection."""
        malicious = "1 UNION SELECT * FROM users"
        assert SQLInjectionProtection.detect_sql_injection(malicious) is True
    
    def test_detect_sql_injection_comment(self):
        """Test detection of comment-based SQL injection."""
        malicious = "admin'--"
        assert SQLInjectionProtection.detect_sql_injection(malicious) is True
    
    def test_detect_sql_injection_drop_table(self):
        """Test detection of DROP TABLE injection."""
        malicious = "'; DROP TABLE users; --"
        assert SQLInjectionProtection.detect_sql_injection(malicious) is True
    
    def test_safe_input_not_detected(self):
        """Test that safe input is not flagged."""
        safe = "john.doe@example.com"
        assert SQLInjectionProtection.detect_sql_injection(safe) is False
    
    def test_validate_identifier_safe(self):
        """Test validation of safe SQL identifiers."""
        assert SQLInjectionProtection.validate_identifier("users") is True
        assert SQLInjectionProtection.validate_identifier("user_table") is True
        assert SQLInjectionProtection.validate_identifier("table123") is True
    
    def test_validate_identifier_unsafe(self):
        """Test validation of unsafe SQL identifiers."""
        assert SQLInjectionProtection.validate_identifier("users; DROP TABLE") is False
        assert SQLInjectionProtection.validate_identifier("123table") is False
        assert SQLInjectionProtection.validate_identifier("user-table") is False


class TestSecretsProtection:
    """Test secrets protection utilities."""
    
    def test_mask_password(self):
        """Test password masking."""
        text = "password=mysecretpassword123"
        masked = SecretsProtection.mask_secrets(text)
        
        assert "mysecretpassword123" not in masked
        assert "***REDACTED***" in masked
    
    def test_mask_api_key(self):
        """Test API key masking."""
        text = "api_key=sk-1234567890abcdef"
        masked = SecretsProtection.mask_secrets(text)
        
        assert "sk-1234567890abcdef" not in masked
        assert "***REDACTED***" in masked
    
    def test_mask_jwt_token(self):
        """Test JWT token masking."""
        text = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        masked = SecretsProtection.mask_secrets(text)
        
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in masked
        assert "***REDACTED***" in masked
    
    def test_mask_credit_card(self):
        """Test credit card masking."""
        text = "Credit card: 4532-1234-5678-9010"
        masked = SecretsProtection.mask_secrets(text)
        
        assert "4532-1234-5678-9010" not in masked
        assert "***REDACTED***" in masked
    
    def test_mask_ssn(self):
        """Test SSN masking."""
        text = "SSN: 123-45-6789"
        masked = SecretsProtection.mask_secrets(text)
        
        assert "123-45-6789" not in masked
        assert "***REDACTED***" in masked
    
    def test_detect_hardcoded_secrets(self):
        """Test detection of hardcoded secrets."""
        code = """
        password = "mysecretpassword"
        api_key = "sk-1234567890"
        """
        
        detected = SecretsProtection.detect_hardcoded_secrets(code)
        
        assert "password" in detected
        assert "api_key" in detected


class TestSQLInjectionVerification:
    """Test SQL injection verification tool."""
    
    def test_verify_application(self):
        """Test that application code passes SQL injection verification."""
        results = verify_sql_injection_prevention("app")
        
        assert results["success"] is True
        assert results["files_with_issues"] == 0
        assert results["message"] == "All files passed SQL injection verification"


class TestSecureConfiguration:
    """Test secure configuration."""
    
    def test_tls_configuration(self):
        """Test TLS configuration."""
        from app.config import settings
        
        # TLS 1.3 should be configured
        assert settings.TLS_MIN_VERSION == "TLSv1.3"
    
    def test_security_features_enabled(self):
        """Test that security features are enabled."""
        from app.config import settings
        
        assert settings.ENABLE_SECURITY_HEADERS is True
        assert settings.ENABLE_XSS_PROTECTION is True
        assert settings.ENABLE_SQL_INJECTION_DETECTION is True
    
    def test_bcrypt_cost_factor(self):
        """Test that bcrypt cost factor is secure."""
        from app.config import settings
        
        # Cost factor should be at least 12
        assert settings.BCRYPT_COST_FACTOR >= 12
    
    def test_password_requirements(self):
        """Test password requirements."""
        from app.config import settings
        
        # Minimum password length should be at least 12
        assert settings.PASSWORD_MIN_LENGTH >= 12


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
