from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies import CsrfProtected, CurrentAdmin, DbSession
from app.models import Agent, AgentStatus, Project, ProjectToken
from app.schemas.agents import AgentAdminUpdate, AgentOut, AgentPage
from app.schemas.projects import (
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    TokenCreate,
    TokenCreated,
    TokenOut,
)
from app.services.agents import agent_query, list_agents, update_agent_admin
from app.services.tokens import create_token, revoke_token

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/projects", response_model=list[ProjectOut])
def projects(db: DbSession, _: CurrentAdmin) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.name)))


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate, db: DbSession, _: CurrentAdmin, __: CsrfProtected
) -> Project:
    project = Project(name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    return project


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: UUID, db: DbSession, _: CurrentAdmin) -> Project:
    return _project_or_404(db, project_id)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    db: DbSession,
    _: CurrentAdmin,
    __: CsrfProtected,
) -> Project:
    project = _project_or_404(db, project_id)
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(project, key, value)
    db.commit()
    return project


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: UUID, db: DbSession, _: CurrentAdmin, __: CsrfProtected) -> Response:
    db.delete(_project_or_404(db, project_id))
    db.commit()
    return Response(status_code=204)


@router.get("/projects/{project_id}/tokens", response_model=list[TokenOut])
def tokens(project_id: UUID, db: DbSession, _: CurrentAdmin) -> list[ProjectToken]:
    _project_or_404(db, project_id)
    return list(
        db.scalars(
            select(ProjectToken)
            .where(ProjectToken.project_id == project_id)
            .order_by(ProjectToken.created_at.desc())
        )
    )


@router.post("/projects/{project_id}/tokens", response_model=TokenCreated, status_code=201)
def create_project_token(
    project_id: UUID,
    payload: TokenCreate,
    db: DbSession,
    _: CurrentAdmin,
    __: CsrfProtected,
) -> TokenCreated:
    _project_or_404(db, project_id)
    record, plain = create_token(db, project_id, payload.name)
    db.commit()
    return TokenCreated(
        **TokenOut.model_validate(record, from_attributes=True).model_dump(),
        token=plain,
    )


@router.post("/projects/{project_id}/tokens/{token_id}/revoke", response_model=TokenOut)
def revoke_project_token(
    project_id: UUID,
    token_id: UUID,
    db: DbSession,
    _: CurrentAdmin,
    __: CsrfProtected,
) -> ProjectToken:
    record = revoke_token(db, token_id)
    if record.project_id != project_id:
        raise HTTPException(status_code=404, detail="Token not found")
    db.commit()
    return record


@router.get("/agents", response_model=AgentPage)
def agents(
    db: DbSession,
    _: CurrentAdmin,
    project_id: UUID | None = None,
    agent_status: Annotated[AgentStatus | None, Query(alias="status")] = None,
    tag: str | None = None,
    hostname: str | None = None,
    last_seen_after: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> AgentPage:
    items, total = list_agents(
        db,
        agent_query(
            project_id=project_id,
            status=agent_status,
            tag=tag,
            hostname=hostname,
            last_seen_after=last_seen_after,
        ),
        page,
        page_size,
    )
    return AgentPage(
        items=[AgentOut.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/agents/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: UUID, db: DbSession, _: CurrentAdmin) -> Agent:
    return _agent_or_404(db, agent_id)


@router.patch("/agents/{agent_id}", response_model=AgentOut)
def update_agent(
    agent_id: UUID,
    payload: AgentAdminUpdate,
    db: DbSession,
    _: CurrentAdmin,
    __: CsrfProtected,
) -> Agent:
    agent = update_agent_admin(db, _agent_or_404(db, agent_id), payload)
    db.commit()
    return agent


@router.post("/agents/{agent_id}/approve", response_model=AgentOut)
def approve_agent(agent_id: UUID, db: DbSession, _: CurrentAdmin, __: CsrfProtected) -> Agent:
    return _set_status(db, agent_id, AgentStatus.active)


@router.post("/agents/{agent_id}/disable", response_model=AgentOut)
def disable_agent(agent_id: UUID, db: DbSession, _: CurrentAdmin, __: CsrfProtected) -> Agent:
    return _set_status(db, agent_id, AgentStatus.disabled)


def _set_status(db: DbSession, agent_id: UUID, value: AgentStatus) -> Agent:
    agent = _agent_or_404(db, agent_id)
    agent.status = value
    db.commit()
    return agent


def _project_or_404(db: DbSession, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _agent_or_404(db: DbSession, agent_id: UUID) -> Agent:
    agent = db.scalar(select(Agent).options(selectinload(Agent.tags)).where(Agent.id == agent_id))
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
