"""CRUD operation tests."""

import pytest
import requests


@pytest.mark.smoke
def test_create_item(base_url: str, api_client):
    """Test creating a new item."""
    response = api_client.post(
        f"{base_url}/items",
        json={"name": "New Item", "description": "A test item"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Item"
    assert data["description"] == "A test item"
    assert "id" in data

    # Cleanup
    api_client.delete(f"{base_url}/items/{data['id']}")


@pytest.mark.regression
def test_list_items(base_url: str, api_client, created_item):
    """Test listing all items."""
    response = api_client.get(f"{base_url}/items")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["id"] == created_item["id"] for item in data)


@pytest.mark.regression
def test_get_item(base_url: str, api_client, created_item):
    """Test getting a single item."""
    response = api_client.get(f"{base_url}/items/{created_item['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_item["id"]
    assert data["name"] == created_item["name"]


@pytest.mark.regression
def test_update_item(base_url: str, api_client, created_item):
    """Test updating an item."""
    response = api_client.put(
        f"{base_url}/items/{created_item['id']}",
        json={"name": "Updated Item", "description": "Updated description"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Item"
    assert data["description"] == "Updated description"


@pytest.mark.regression
def test_delete_item(base_url: str, api_client):
    """Test deleting an item."""
    # Create item first
    create_response = api_client.post(
        f"{base_url}/items",
        json={"name": "To Delete", "description": "Will be deleted"}
    )
    item_id = create_response.json()["id"]

    # Delete it
    response = api_client.delete(f"{base_url}/items/{item_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_response = api_client.get(f"{base_url}/items/{item_id}")
    assert get_response.status_code == 404


@pytest.mark.regression
def test_full_crud_workflow(base_url: str, api_client):
    """Test complete CRUD workflow."""
    # Create
    create_resp = api_client.post(
        f"{base_url}/items",
        json={"name": "Workflow Item", "description": "Testing workflow"}
    )
    assert create_resp.status_code == 201
    item = create_resp.json()
    item_id = item["id"]

    # Read
    read_resp = api_client.get(f"{base_url}/items/{item_id}")
    assert read_resp.status_code == 200
    assert read_resp.json()["name"] == "Workflow Item"

    # Update
    update_resp = api_client.put(
        f"{base_url}/items/{item_id}",
        json={"name": "Updated Workflow", "description": "Modified"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated Workflow"

    # Delete
    delete_resp = api_client.delete(f"{base_url}/items/{item_id}")
    assert delete_resp.status_code == 204

    # Verify deleted
    verify_resp = api_client.get(f"{base_url}/items/{item_id}")
    assert verify_resp.status_code == 404
