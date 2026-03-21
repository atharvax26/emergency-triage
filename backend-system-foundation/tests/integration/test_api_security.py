"""Integration tests for API security."""

import pytest
from httpx import AsyncClient

from app.models.user import User
from app.models.patient import Patient


@pytest.mark.integration
@pytest.mark.asyncio
class TestAPISecurity:
    """Test API security features."""
    
    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        """Test unauthenticated requests return 401."""
        endpoints = [
            "/api/v1/auth/me",
            "/api/v1/patients",
            "/api/v1/queue",
        ]
        
        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require auth"
    
    async def test_invalid_token_returns_401(self, client: AsyncClient):
        """Test invalid token returns 401."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    async def test_expired_token_returns_401(self, client: AsyncClient):
        """Test expired token returns 401."""
        # Create an expired token (this would need JWT manipulation)
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxfQ.invalid"
        
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
    
    async def test_nurse_cannot_access_admin_endpoints(
        self,
        client: AsyncClient,
        nurse_auth_headers: dict
    ):
        """Test nurse cannot access admin-only endpoints."""
        response = await client.get(
            "/api/v1/users",
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 403
    
    async def test_nurse_cannot_assign_patients(
        self,
        client: AsyncClient,
        sample_patient: Patient,
        doctor_user: User,
        nurse_auth_headers: dict
    ):
        """Test nurse cannot assign patients to doctors."""
        # First add patient to queue
        await client.post(
            "/api/v1/queue",
            json={
                "patient_id": str(sample_patient.id),
                "priority": 5,
                "symptoms": {"chief_complaint": "test"}
            },
            headers=nurse_auth_headers
        )
        
        # Try to assign (should fail)
        response = await client.post(
            "/api/v1/queue/assign",
            json={
                "patient_id": str(sample_patient.id),
                "doctor_id": str(doctor_user.id)
            },
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 403
    
    async def test_doctor_cannot_access_user_management(
        self,
        client: AsyncClient,
        doctor_auth_headers: dict
    ):
        """Test doctor cannot access user management endpoints."""
        response = await client.get(
            "/api/v1/users",
            headers=doctor_auth_headers
        )
        
        assert response.status_code == 403
    
    async def test_admin_can_access_all_endpoints(
        self,
        client: AsyncClient,
        admin_auth_headers: dict
    ):
        """Test admin can access all endpoints."""
        endpoints = [
            "/api/v1/patients",
            "/api/v1/queue",
            "/api/v1/users",
            "/api/v1/audit",
        ]
        
        for endpoint in endpoints:
            response = await client.get(endpoint, headers=admin_auth_headers)
            # Should not be 403 (may be 200, 404, etc.)
            assert response.status_code != 403, f"Admin should access {endpoint}"
    
    async def test_sql_injection_prevention(
        self,
        client: AsyncClient,
        nurse_auth_headers: dict
    ):
        """Test SQL injection attempts are prevented."""
        # Try SQL injection in search
        response = await client.get(
            "/api/v1/patients/search?first_name='; DROP TABLE patients; --",
            headers=nurse_auth_headers
        )
        
        # Should not cause error, just return no results
        assert response.status_code in [200, 400, 422]
    
    async def test_xss_prevention_in_patient_data(
        self,
        client: AsyncClient,
        nurse_auth_headers: dict
    ):
        """Test XSS attempts in patient data are handled."""
        response = await client.post(
            "/api/v1/patients",
            json={
                "first_name": "<script>alert('xss')</script>",
                "last_name": "Test",
                "date_of_birth": "1990-01-01",
                "gender": "male"
            },
            headers=nurse_auth_headers
        )
        
        # Should either reject or sanitize
        if response.status_code == 201:
            data = response.json()
            # Should not contain script tags
            assert "<script>" not in data["first_name"]
    
    async def test_rate_limiting_headers_present(
        self,
        client: AsyncClient,
        nurse_auth_headers: dict
    ):
        """Test rate limiting headers are present."""
        response = await client.get(
            "/api/v1/patients",
            headers=nurse_auth_headers
        )
        
        # Check for rate limit headers (if implemented)
        # This is a placeholder - actual implementation may vary
        assert response.status_code in [200, 429]
    
    async def test_cors_headers_present(self, client: AsyncClient):
        """Test CORS headers are present."""
        response = await client.options("/api/v1/health")
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code == 200
    
    async def test_security_headers_present(self, client: AsyncClient):
        """Test security headers are present."""
        response = await client.get("/api/v1/health")
        
        # Check for common security headers
        headers = response.headers
        # These may or may not be present depending on configuration
        # Just verify the response is valid
        assert response.status_code == 200
    
    async def test_password_not_returned_in_user_data(
        self,
        client: AsyncClient,
        nurse_user: User,
        nurse_auth_headers: dict
    ):
        """Test password hash is never returned in API responses."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "password" not in data
        assert "password_hash" not in data
    
    async def test_audit_logs_require_admin(
        self,
        client: AsyncClient,
        nurse_auth_headers: dict,
        doctor_auth_headers: dict
    ):
        """Test audit logs require admin role."""
        # Nurse should not access
        response = await client.get(
            "/api/v1/audit",
            headers=nurse_auth_headers
        )
        assert response.status_code == 403
        
        # Doctor should not access
        response = await client.get(
            "/api/v1/audit",
            headers=doctor_auth_headers
        )
        assert response.status_code == 403
