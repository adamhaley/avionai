"""
API endpoint tests
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "templates_available" in data


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert "endpoints" in data


def test_templates_endpoint():
    """Test templates listing endpoint"""
    response = client.get("/templates")
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    assert "count" in data
    assert isinstance(data["templates"], list)


def test_generate_xlsx_missing_template():
    """Test XLSX generation with missing template"""
    response = client.post(
        "/generate-xlsx",
        json={
            "template_name": "nonexistent.xlsx",
            "data": {"B3": "test"},
            "return_format": "base64"
        }
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_generate_xlsx_empty_data():
    """Test XLSX generation with empty data"""
    response = client.post(
        "/generate-xlsx",
        json={
            "template_name": "Template.xlsx",
            "data": {},
            "return_format": "base64"
        }
    )
    # Should fail with 400 or 404 depending on whether template exists
    assert response.status_code in [400, 404]


def test_generate_xlsx_invalid_return_format():
    """Test that invalid return_format is handled"""
    response = client.post(
        "/generate-xlsx",
        json={
            "template_name": "Template.xlsx",
            "data": {"B3": "test"},
            "return_format": "invalid_format"
        }
    )
    # Should still work, but return base64 by default
    # Or fail with validation error
    assert response.status_code in [200, 400, 404, 422]
