import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_endpoint():
    """Проверка, что сервер вообще дышит"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "Muninn Core is running"}

def test_agent_registration_mock():
    """Проверка эндпоинта регистрации агента (пока без БД)"""
    payload = {
        "agent_id": "test-uuid-999",
        "token": "secret-group-token",
        "hostname": "borya-fedora",
        "os_info": {
            "name": "Fedora",
            "version": "41",
            "kernel": "6.11.0"
        },
        "hardware": {
            "cpu_total": 8,
            "ram_total_gb": 16.0,
            "disk_total_gb": 512.0
        }
    }
    response = client.post("/api/v1/register", json=payload)
    
    assert response.status_code == 201
    assert response.json()["status"] == "pending"