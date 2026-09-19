from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, AgentStatus, Project
from app.services.tokens import create_token, revoke_token


def payload(agent_id: str = "agent-001", hostname: str = "host-a") -> dict[str, object]:
    return {
        "agent_id": agent_id,
        "hostname": hostname,
        "os": {"name": "Fedora", "version": "41", "kernel": "6.11"},
        "hardware": {
            "cpu_cores": 8,
            "cpu_model": "Example CPU",
            "ram_bytes": 17_179_869_184,
            "disk_bytes": 549_755_813_888,
        },
        "ip_addresses": ["192.0.2.10", "2001:db8::1"],
        "inventory": {"packages": 2123, "role": "builder"},
    }


def project_token(db: Session, name: str = "project") -> tuple[Project, str]:
    project = Project(name=name)
    db.add(project)
    db.flush()
    _, plain = create_token(db, project.id, "primary")
    db.commit()
    return project, plain


def test_root_endpoint(client: TestClient) -> None:
    assert client.get("/").json() == {"status": "Muninn Core is running"}
    assert client.get("/health/live").status_code == 200


def test_first_and_repeat_report_only_updates_inventory(client: TestClient, db: Session) -> None:
    project, token = project_token(db)
    headers = {"Authorization": f"Bearer {token}"}
    first = client.post("/api/v1/agents/report", json=payload(), headers=headers)
    assert first.status_code == 200
    assert first.json()["status"] == "pending"
    agent = db.scalar(select(Agent))
    assert agent is not None
    registered_at = agent.registered_at
    agent.status = AgentStatus.active
    agent.description = "owned by admin"
    db.commit()

    second = client.post(
        "/api/v1/agents/report", json=payload(hostname="host-renamed"), headers=headers
    )
    db.refresh(agent)
    assert second.status_code == 200
    assert agent.hostname == "host-renamed"
    assert agent.registered_at == registered_at
    assert agent.status == AgentStatus.active
    assert agent.description == "owned by admin"
    assert agent.project_id == project.id


def test_invalid_revoked_and_body_token_rejected(client: TestClient, db: Session) -> None:
    project, token = project_token(db)
    assert client.post("/api/v1/agents/report", json=payload()).status_code == 401
    assert (
        client.post(
            "/api/v1/agents/report",
            json={**payload(), "token": token},
            headers={"Authorization": f"Bearer {token}"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/agents/report",
            json=payload(),
            headers={"Authorization": "Bearer bad"},
        ).status_code
        == 401
    )
    record = project.tokens[0]
    revoke_token(db, record.id)
    db.commit()
    response = client.post(
        "/api/v1/agents/report",
        json=payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


def test_same_agent_id_is_isolated_by_project(client: TestClient, db: Session) -> None:
    _, one = project_token(db, "one")
    _, two = project_token(db, "two")
    for token in (one, two):
        response = client.post(
            "/api/v1/agents/report",
            json=payload(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
    assert len(list(db.scalars(select(Agent)))) == 2


def test_strict_validation_and_body_limit(client: TestClient, db: Session) -> None:
    _, token = project_token(db)
    bad = {**payload(), "unexpected": True}
    assert (
        client.post(
            "/api/v1/agents/report",
            json=bad,
            headers={"Authorization": f"Bearer {token}"},
        ).status_code
        == 422
    )
    response = client.post(
        "/api/v1/agents/report",
        content=b"x" * 1_048_577,
        headers={"Authorization": f"Bearer {token}", "content-type": "application/json"},
    )
    assert response.status_code == 413


def test_timestamps_are_returned(client: TestClient, db: Session) -> None:
    _, token = project_token(db)
    result = client.post(
        "/api/v1/agents/report",
        json=payload(),
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert datetime.fromisoformat(result["registered_at"])
    assert datetime.fromisoformat(result["last_seen_at"])
