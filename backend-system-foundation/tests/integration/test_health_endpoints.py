"""Integration tests for health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test health check endpoints."""
    
    async def test_health_endpoint_no_auth_required(self, client: AsyncClient):
        """Test health endpoint doesn't require authentication."""
        response = await client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "ok"]
    
    async def test_health_ready_endpoint(self, client: AsyncClient):
        """Test readiness probe endpoint."""
        response = await client.get("/api/v1/health/ready")
        
        # Should return 200 if services are ready, 503 if not
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "database" in data
            assert "redis" in data
    
    async def test_health_live_endpoint(self, client: AsyncClient):
        """Test liveness probe endpoint."""
        response = await client.get("/api/v1/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
