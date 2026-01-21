"""Negative test cases - invalid inputs and error handling."""

import pytest
import requests


@pytest.mark.regression
def test_get_nonexistent_item(base_url: str, api_client):
    """Test getting an item that doesn't exist."""
    response = api_client.get(f"{base_url}/items/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.regression
def test_update_nonexistent_item(base_url: str, api_client):
    """Test updating an item that doesn't exist."""
    response = api_client.put(
        f"{base_url}/items/99999",
        json={"name": "Ghost Item", "description": "Doesn't exist"}
    )
    assert response.status_code == 404


@pytest.mark.regression
def test_delete_nonexistent_item(base_url: str, api_client):
    """Test deleting an item that doesn't exist."""
    response = api_client.delete(f"{base_url}/items/99999")
    assert response.status_code == 404


@pytest.mark.regression
def test_create_item_missing_name(base_url: str, api_client):
    """Test creating an item without required name field."""
    response = api_client.post(
        f"{base_url}/items",
        json={"description": "No name provided"}
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.regression
def test_create_item_invalid_json(base_url: str, api_client):
    """Test creating an item with invalid JSON."""
    response = api_client.post(
        f"{base_url}/items",
        data="not valid json",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
