import hmac
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies import DbSession, login_limiter
from app.core.security import new_csrf_token, verify_password
from app.models import AdminUser, Agent, AgentStatus, Project
from app.schemas.agents import AgentAdminUpdate
from app.services.agents import agent_query, list_agents, update_agent_admin
from app.services.tokens import create_token, revoke_token

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _admin(request: Request, db: DbSession) -> AdminUser:
    value = request.session.get("admin_id")
    admin = db.get(AdminUser, UUID(value)) if value else None
    if admin is None or not admin.is_active:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return admin


def _csrf(request: Request, supplied: str) -> None:
    expected = request.session.get("csrf")
    if not expected or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


def _context(request: Request, **values: object) -> dict[str, object]:
    return {"request": request, "csrf": request.session.get("csrf"), **values}


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    request.session.setdefault("csrf", new_csrf_token())
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": None, "csrf": request.session["csrf"]},
    )


@router.post("/login")
def login(
    request: Request,
    db: DbSession,
    username: str = Form(),
    password: str = Form(),
    csrf_token: str = Form(default=""),
) -> Response:
    _csrf(request, csrf_token)
    key = request.client.host if request.client else "unknown"
    if not login_limiter.allowed(key):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Too many attempts. Try again later.", "csrf": csrf_token},
            status_code=429,
        )
    admin = db.scalar(select(AdminUser).where(AdminUser.username == username))
    if admin is None or not admin.is_active or not verify_password(password, admin.password_hash):
        login_limiter.failed(key)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid credentials", "csrf": csrf_token},
            status_code=401,
        )
    admin.last_login_at = datetime.now(UTC)
    db.commit()
    login_limiter.succeeded(key)
    request.session.clear()
    request.session["admin_id"] = str(admin.id)
    request.session["csrf"] = new_csrf_token()
    return RedirectResponse("/admin/agents", status_code=303)


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form(default="")) -> RedirectResponse:
    _csrf(request, csrf_token)
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/admin", include_in_schema=False)
def admin_root() -> RedirectResponse:
    return RedirectResponse("/admin/agents", status_code=302)


@router.get("/admin/projects", response_class=HTMLResponse)
def project_list(request: Request, db: DbSession) -> HTMLResponse:
    _admin(request, db)
    projects = list(
        db.scalars(select(Project).options(selectinload(Project.tokens)).order_by(Project.name))
    )
    return templates.TemplateResponse(
        request, "projects.html", _context(request, projects=projects)
    )


@router.post("/admin/projects")
def project_create(
    request: Request,
    db: DbSession,
    name: str = Form(),
    description: str = Form(default=""),
    csrf_token: str = Form(default=""),
) -> RedirectResponse:
    _admin(request, db)
    _csrf(request, csrf_token)
    db.add(Project(name=name.strip(), description=description.strip()))
    db.commit()
    return RedirectResponse("/admin/projects", status_code=303)


@router.post("/admin/projects/{project_id}/tokens")
def token_create(
    project_id: UUID,
    request: Request,
    db: DbSession,
    name: str = Form(),
    csrf_token: str = Form(default=""),
) -> HTMLResponse:
    _admin(request, db)
    _csrf(request, csrf_token)
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404)
    record, secret = create_token(db, project_id, name.strip())
    db.commit()
    return templates.TemplateResponse(
        request,
        "_token_secret.html",
        _context(request, token=record, secret=secret, project_id=project_id),
    )


@router.post("/admin/projects/{project_id}/tokens/{token_id}/revoke")
def token_revoke(
    project_id: UUID,
    token_id: UUID,
    request: Request,
    db: DbSession,
    csrf_token: str = Form(default=""),
) -> HTMLResponse:
    _admin(request, db)
    _csrf(request, csrf_token)
    token = revoke_token(db, token_id)
    if token.project_id != project_id:
        raise HTTPException(status_code=404)
    db.commit()
    return templates.TemplateResponse(
        request,
        "_token.html",
        _context(request, token=token, project_id=project_id),
    )


@router.get("/admin/agents", response_class=HTMLResponse)
def agent_list(
    request: Request,
    db: DbSession,
    project_id: UUID | None = None,
    status: AgentStatus | None = None,
    tag: str | None = None,
    hostname: str | None = None,
    last_seen_after: datetime | None = None,
    page: int = 1,
) -> HTMLResponse:
    _admin(request, db)
    agents, total = list_agents(
        db,
        agent_query(
            project_id=project_id,
            status=status,
            tag=tag,
            hostname=hostname,
            last_seen_after=last_seen_after,
        ),
        max(page, 1),
        50,
    )
    context = _context(
        request,
        agents=agents,
        total=total,
        page=max(page, 1),
        projects=list(db.scalars(select(Project).order_by(Project.name))),
        filters={
            "project_id": project_id,
            "status": status,
            "tag": tag or "",
            "hostname": hostname or "",
            "last_seen_after": last_seen_after.isoformat() if last_seen_after else "",
        },
    )
    template = "_agent_table.html" if request.headers.get("hx-request") else "agents.html"
    return templates.TemplateResponse(request, template, context)


@router.get("/admin/pending")
def pending() -> RedirectResponse:
    return RedirectResponse("/admin/agents?" + urlencode({"status": "pending"}), status_code=302)


@router.get("/admin/agents/{agent_id}", response_class=HTMLResponse)
def agent_detail(agent_id: UUID, request: Request, db: DbSession) -> HTMLResponse:
    _admin(request, db)
    agent = db.scalar(
        select(Agent)
        .options(selectinload(Agent.tags), selectinload(Agent.project))
        .where(Agent.id == agent_id)
    )
    if agent is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "agent.html", _context(request, agent=agent))


@router.post("/admin/agents/{agent_id}/status")
def agent_status(
    agent_id: UUID,
    request: Request,
    db: DbSession,
    status: Annotated[AgentStatus, Form()],
    csrf_token: Annotated[str, Form()] = "",
) -> RedirectResponse:
    _admin(request, db)
    _csrf(request, csrf_token)
    if status not in {AgentStatus.active, AgentStatus.disabled}:
        raise HTTPException(status_code=422)
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404)
    agent.status = status
    db.commit()
    return RedirectResponse(f"/admin/agents/{agent_id}", status_code=303)


@router.post("/admin/agents/{agent_id}")
def agent_edit(
    agent_id: UUID,
    request: Request,
    db: DbSession,
    description: str = Form(default=""),
    tags: str = Form(default=""),
    csrf_token: str = Form(default=""),
) -> RedirectResponse:
    _admin(request, db)
    _csrf(request, csrf_token)
    agent = db.scalar(select(Agent).options(selectinload(Agent.tags)).where(Agent.id == agent_id))
    if agent is None:
        raise HTTPException(status_code=404)
    update_agent_admin(
        db,
        agent,
        AgentAdminUpdate(
            description=description.strip(),
            tags=[tag for tag in tags.split(",")],
        ),
    )
    db.commit()
    return RedirectResponse(f"/admin/agents/{agent_id}", status_code=303)
