"""Tests for application lifecycle, health endpoints, and config safety."""

from fastapi.testclient import TestClient


def test_app_initialization(client: TestClient) -> None:
    """Verify application initializes with correct metadata."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "PaisaFlow" in schema["info"]["title"]
    assert schema["info"]["version"] == "0.1.0"


def test_health_endpoint(client: TestClient) -> None:
    """Verify /health returns consistent schema without leaking credentials."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "meta" in data
    assert "status" in data["data"]
    assert "app_name" in data["data"]
    assert "database" in data["data"]
    assert data["data"]["app_name"] == "PaisaFlow API"

    # Security check: no connection strings or passwords in response
    serialized = response.text.lower()
    assert "password" not in serialized
    assert "postgres:" not in serialized


def test_public_config_endpoint(client: TestClient) -> None:
    """Verify /api/v1/config exposes only safe frontend configuration."""
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    body = response.json()

    assert "data" in body
    config = body["data"]
    assert config["default_currency"] == "INR"
    assert config["default_locale"] == "en-IN"
    assert config["default_timezone"] == "Asia/Kolkata"
    assert config["is_synthetic_only"] is True
    assert "csv" in config["supported_upload_formats"]

    # Strict security assertion: no credentials exposed
    raw_text = response.text.lower()
    assert "gemini_api_key" not in raw_text
    assert "secret" not in raw_text
    assert "database_url" not in raw_text
    assert "key_vault" not in raw_text


def test_unknown_route_returns_404(client: TestClient) -> None:
    """Verify unmapped routes return standard 404 response."""
    response = client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == 404

