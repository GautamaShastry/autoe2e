"""Pytest configuration and fixtures."""

import os

import pytest
import requests


@pytest.fixture(scope="session")
def base_url() -> str:
    """Get the base URL for the API."""
    return os.environ.get("API_BASE_URL", "http://localhost:8080")


@pytest.fixture(scope="session")
def api_client(base_url: str):
    """Create a requests session for API calls."""
    session = requests.Session()
    session.base_url = base_url
    return session


@pytest.fixture
def created_item(api_client, base_url: str):
    """Create an item and clean up after test."""
    response = api_client.post(
        f"{base_url}/items",
        json={"name": "Test Item", "description": "For testing"}
    )
    item = response.json()
    yield item
    # Cleanup
    api_client.delete(f"{base_url}/items/{item['id']}")
