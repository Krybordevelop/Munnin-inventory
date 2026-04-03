def test_agent_registration_success(client, test_group):
    """Тест: агент успешно регистрируется с валидным токеном группы"""
    payload = {
        "agent_id": "real-agent-uuid",
        "token": test_group.token,  # Берем токен из созданной фикстурой группы
        "hostname": "workstation-01",
        "os_info": {
            "name": "Fedora",
            "version": "41",
            "kernel": "6.11"
        },
        "hardware": {
            "cpu_total": 4,
            "ram_total_gb": 8.0,
            "disk_total_gb": 256.0
        }
    }
    
    response = client.post("/api/v1/register", json=payload)
    
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert response.json()["id"] == "real-agent-uuid"

def test_agent_registration_wrong_token(client):
    """Тест: агент получает 403 при неверном токене"""
    payload = {
        "agent_id": "hacker-pc",
        "token": "wrong-token",
        "hostname": "hacker",
        "os_info": {"name": "Kali", "version": "1", "kernel": "1"},
        "hardware": {"cpu_total": 1, "ram_total_gb": 1, "disk_total_gb": 1}
    }
    response = client.post("/api/v1/register", json=payload)
    assert response.status_code == 403