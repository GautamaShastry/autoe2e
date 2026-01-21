"""Health check tests."""

import pytest
import requests


@pytest.mark.smoke
def test_health_endpoint(base_url: str):
    """Test that health endpoint returns 200."""
    response = requests.get(f"{base_url}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.smoke
def test_readiness_endpoint(base_url: str):
    """Test that readiness endpoint shows all services connected."""
    response = requests.get(f"{base_url}/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert data["services"]["db"] == "connected"
    assert data["services"]["redis"] == "connected"
