"""Integration tests for authentication API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.fixtures.sample_data import sample_user_data


@pytest.mark.integration
@pytest.mark.asyncio
class TestAuthenticationEndpoints:
    """Test authentication API endpoints."""
    
    async def test_login_success(
        self,
        client: AsyncClient,
        nurse_user: User
    ):
        """Test successful login returns tokens."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": nurse_user.email,
                "password": "SecurePass123!@#"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials returns 401."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401
    
    async def test_login_inactive_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        nurse_user: User
    ):
        """Test login with inactive user returns 401."""
        # Deactivate user
        nurse_user.is_active = False
        await db_session.flush()
        
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": nurse_user.email,
                "password": "SecurePass123!@#"
            }
        )
        
        assert response.status_code == 401
    
    async def test_get_current_user(
        self,
        client: AsyncClient,
        nurse_user: User,
        nurse_auth_headers: dict
    ):
        """Test getting current user info."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == nurse_user.email
        assert data["first_name"] == nurse_user.first_name
        assert "nurse" in [role["name"] for role in data["roles"]]
    
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting current user without token returns 401."""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    async def test_logout(
        self,
        client: AsyncClient,
        nurse_auth_headers: dict
    ):
        """Test logout revokes token."""
        response = await client.post(
            "/api/v1/auth/logout",
            headers=nurse_auth_headers
        )
        
        assert response.status_code == 200
