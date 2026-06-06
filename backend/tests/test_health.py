"""Health endpoint smoke tests — no database or Redis required.

These tests call the endpoint handler functions directly, bypassing the ASGI
lifecycle so they run in CI without live service connections.
"""
import pytest

pytestmark = pytest.mark.unit


async def test_health_check_returns_healthy():
    """Basic /health endpoint returns 'healthy' without auth."""
    from app.api.health import health_check

    result = await health_check()

    assert result["status"] == "healthy"
    assert "message" in result


async def test_liveness_check_returns_alive():
    """/health/live endpoint returns 'alive' (process-only probe)."""
    from app.api.health import liveness_check

    result = await liveness_check()

    assert result["status"] == "alive"
    assert "message" in result
