from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Agent, AgentStatus, Tag
from app.schemas.agents import AgentAdminUpdate, AgentReport


def report_inventory(db: Session, project_id: UUID, report: AgentReport) -> Agent:
    agent = db.scalar(
        select(Agent).where(
            Agent.project_id == project_id,
            Agent.agent_id == report.agent_id,
        )
    )
    now = datetime.now(UTC)
    if agent is not None:
        _apply_inventory(agent, report, now)
        db.flush()
        return agent
    agent = Agent(
        project_id=project_id,
        agent_id=report.agent_id,
        status=AgentStatus.pending,
        registered_at=now,
        last_seen_at=now,
        hostname=report.hostname,
        os_name=report.os.name,
        os_version=report.os.version,
        kernel=report.os.kernel,
        cpu_model=report.hardware.cpu_model,
        cpu_cores=report.hardware.cpu_cores,
        ram_bytes=report.hardware.ram_bytes,
        disk_bytes=report.hardware.disk_bytes,
        ip_addresses=report.ip_addresses,
        inventory=report.inventory,
    )
    try:
        with db.begin_nested():
            db.add(agent)
            db.flush()
    except IntegrityError:
        agent = db.scalar(
            select(Agent).where(
                Agent.project_id == project_id,
                Agent.agent_id == report.agent_id,
            )
        )
        if agent is None:
            raise
        _apply_inventory(agent, report, now)
        db.flush()
    return agent


def _apply_inventory(agent: Agent, report: AgentReport, now: datetime) -> None:
    agent.hostname = report.hostname
    agent.os_name = report.os.name
    agent.os_version = report.os.version
    agent.kernel = report.os.kernel
    agent.cpu_model = report.hardware.cpu_model
    agent.cpu_cores = report.hardware.cpu_cores
    agent.ram_bytes = report.hardware.ram_bytes
    agent.disk_bytes = report.hardware.disk_bytes
    agent.ip_addresses = report.ip_addresses
    agent.inventory = report.inventory
    agent.last_seen_at = now


def agent_query(
    *,
    project_id: UUID | None = None,
    status: AgentStatus | None = None,
    tag: str | None = None,
    hostname: str | None = None,
    last_seen_after: datetime | None = None,
) -> Select[tuple[Agent]]:
    query = select(Agent).options(selectinload(Agent.tags))
    if project_id:
        query = query.where(Agent.project_id == project_id)
    if status:
        query = query.where(Agent.status == status)
    if tag:
        query = query.join(Agent.tags).where(Tag.name == tag)
    if hostname:
        query = query.where(Agent.hostname.ilike(f"%{hostname}%"))
    if last_seen_after:
        query = query.where(Agent.last_seen_at >= last_seen_after)
    return query


def list_agents(
    db: Session, query: Select[tuple[Agent]], page: int, page_size: int
) -> tuple[list[Agent], int]:
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = db.scalar(count_query) or 0
    items = list(
        db.scalars(
            query.order_by(Agent.last_seen_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).unique()
    )
    return items, total


def update_agent_admin(db: Session, agent: Agent, update: AgentAdminUpdate) -> Agent:
    if update.description is not None:
        agent.description = update.description
    if update.tags is not None:
        names = sorted({name.strip().lower() for name in update.tags if name.strip()})
        tags: list[Tag] = []
        for name in names:
            tag = db.scalar(select(Tag).where(Tag.project_id == agent.project_id, Tag.name == name))
            if tag is None:
                tag = Tag(project_id=agent.project_id, name=name)
                db.add(tag)
            tags.append(tag)
        agent.tags = tags
    db.flush()
    return agent
