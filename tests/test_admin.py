from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, ProjectToken
from tests.test_agent_api import payload


def test_admin_requires_session_and_csrf(client: TestClient, admin: object) -> None:
    assert client.get("/api/v1/admin/projects").status_code == 401
    login = client.get("/login")
    marker = 'name="csrf_token" value="'
    csrf = login.text.split(marker, 1)[1].split('"', 1)[0]
    assert (
        client.post(
            "/login",
            data={"username": "admin", "password": "wrong", "csrf_token": csrf},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/login",
            data={
                "username": "admin",
                "password": "correct-horse-battery",
                "csrf_token": csrf,
            },
            follow_redirects=False,
        ).status_code
        == 303
    )
    assert client.post("/api/v1/admin/projects", json={"name": "blocked"}).status_code == 403


def test_project_token_rotation_and_revoke(
    logged_in_client: TestClient, csrf: str, db: Session
) -> None:
    headers = {"X-CSRF-Token": csrf}
    project = logged_in_client.post(
        "/api/v1/admin/projects", json={"name": "Production"}, headers=headers
    )
    assert project.status_code == 201
    project_id = project.json()["id"]
    first = logged_in_client.post(
        f"/api/v1/admin/projects/{project_id}/tokens",
        json={"name": "primary"},
        headers=headers,
    )
    second = logged_in_client.post(
        f"/api/v1/admin/projects/{project_id}/tokens",
        json={"name": "rotation"},
        headers=headers,
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["token"].startswith(first.json()["prefix"])
    listed = logged_in_client.get(f"/api/v1/admin/projects/{project_id}/tokens").json()
    assert "token" not in listed[0] and "token_hash" not in listed[0]
    revoke = logged_in_client.post(
        f"/api/v1/admin/projects/{project_id}/tokens/{first.json()['id']}/revoke",
        headers=headers,
    )
    assert revoke.status_code == 200
    assert revoke.json()["revoked_at"]
    assert db.scalar(select(ProjectToken).where(ProjectToken.id == UUID(first.json()["id"])))


def test_agent_admin_rest_and_html_flows(
    logged_in_client: TestClient, csrf: str, db: Session
) -> None:
    headers = {"X-CSRF-Token": csrf}
    project = logged_in_client.post(
        "/api/v1/admin/projects", json={"name": "Fleet"}, headers=headers
    ).json()
    token = logged_in_client.post(
        f"/api/v1/admin/projects/{project['id']}/tokens",
        json={"name": "primary"},
        headers=headers,
    ).json()["token"]
    report_headers = {"Authorization": "Bearer " + token}
    logged_in_client.post("/api/v1/agents/report", json=payload(), headers=report_headers)
    agent = db.scalar(select(Agent))
    assert agent is not None

    page = logged_in_client.get("/api/v1/admin/agents?status=pending")
    assert page.status_code == 200 and page.json()["total"] == 1
    updated = logged_in_client.patch(
        f"/api/v1/admin/agents/{agent.id}",
        json={"description": "CI host", "tags": ["linux", "ci"]},
        headers=headers,
    )
    assert updated.status_code == 200
    assert {tag["name"] for tag in updated.json()["tags"]} == {"linux", "ci"}
    approved = logged_in_client.post(f"/api/v1/admin/agents/{agent.id}/approve", headers=headers)
    assert approved.json()["status"] == "active"
    disabled = logged_in_client.post(f"/api/v1/admin/agents/{agent.id}/disable", headers=headers)
    assert disabled.json()["status"] == "disabled"

    assert logged_in_client.get("/admin/agents").status_code == 200
    assert logged_in_client.get("/admin/pending", follow_redirects=False).status_code == 302
    detail = logged_in_client.get(f"/admin/agents/{agent.id}")
    assert detail.status_code == 200
    assert "CI host" in detail.text and "Last seen" in detail.text
    form = logged_in_client.post(
        f"/admin/agents/{agent.id}",
        data={"description": "edited in UI", "tags": "edge, linux", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert form.status_code == 303
    db.refresh(agent)
    assert agent.description == "edited in UI"


def test_web_csrf_and_logout(logged_in_client: TestClient, csrf: str) -> None:
    assert logged_in_client.post("/admin/projects", data={"name": "bad"}).status_code == 403
    logout = logged_in_client.post("/logout", data={"csrf_token": csrf}, follow_redirects=False)
    assert logout.status_code == 303
    assert logged_in_client.get("/api/v1/admin/projects").status_code == 401
