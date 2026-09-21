"""End-to-end API integration tests for PhishGuard endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify GET /api/health returns 200 and healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "phishguard-backend"


def test_auth_session():
    """Verify POST /api/auth/session returns user profile."""
    response = client.post("/api/auth/session")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert "user" in data


def test_submit_scan_and_fetch():
    """Verify POST /api/scans initiates scan and GET /api/scans/{id} retrieves result."""
    payload = {
        "source_type": "email",
        "content": (
            "Urgent: Unauthorized login detected from paypa1.com. "
            "Immediate action required within 24 hours to prevent suspension: "
            "http://paypa1.com/verify?next=https://login.xyz"
        ),
    }
    post_resp = client.post("/api/scans", json=payload)
    assert post_resp.status_code == 202
    data = post_resp.json()
    scan_id = data["scan_id"]
    assert scan_id is not None
    assert data["status"] == "processing"

    # Fetch scan details
    get_resp = client.get(f"/api/scans/{scan_id}")
    assert get_resp.status_code == 200
    scan_data = get_resp.json()
    assert scan_data["scan_id"] == scan_id
    assert "severity" in scan_data


def test_list_scans():
    """Verify GET /api/scans returns paginated scan records."""
    response = client.get("/api/scans?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


def test_agent_profiles_crud():
    """Verify GET and POST /api/agent-profiles."""
    # List profiles
    list_resp = client.get("/api/agent-profiles")
    assert list_resp.status_code == 200
    profiles = list_resp.json()
    assert len(profiles) >= 1  # Contains default profile

    # Create new profile
    create_payload = {
        "name": "Strict Banking Security Policy",
        "system_prompt": "Enforce zero-tolerance on unauthorized financial domain alterations.",
        "is_default": False,
    }
    create_resp = client.post("/api/agent-profiles", json=create_payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["name"] == create_payload["name"]


def test_connections_flow():
    """Verify POST /api/connections begins OAuth and GET lists connections."""
    start_resp = client.post("/api/connections", json={"provider": "gmail"})
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert "redirect_url" in start_data
    assert "google.com" in start_data["redirect_url"]

    # List connections
    list_resp = client.get("/api/connections")
    assert list_resp.status_code == 200
    assert isinstance(list_resp.json(), list)


def test_error_envelope_format():
    """Verify non-existent scan returns standard error envelope format."""
    resp = client.get("/api/scans/non-existent-scan-id")
    assert resp.status_code == 404
    err = resp.json()
    assert "error" in err
    assert "code" in err["error"]
    assert "message" in err["error"]
