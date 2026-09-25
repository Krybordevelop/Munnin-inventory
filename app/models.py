import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class AgentStatus(StrEnum):
    pending = "pending"
    active = "active"
    disabled = "disabled"


agent_tags = Table(
    "agent_tags",
    Base.metadata,
    Column("agent_id", ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    tokens: Mapped[list["ProjectToken"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    agents: Mapped[list["Agent"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    tags: Mapped[list["Tag"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectToken(Base):
    __tablename__ = "project_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    prefix: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    project: Mapped[Project] = relationship(back_populates="tokens")

    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_project_token_name"),)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[str] = mapped_column(String(128))
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, native_enum=False, length=16), default=AgentStatus.pending, index=True
    )
    description: Mapped[str] = mapped_column(Text, default="")
    hostname: Mapped[str] = mapped_column(String(255), index=True)
    os_name: Mapped[str] = mapped_column(String(120), index=True)
    os_version: Mapped[str] = mapped_column(String(120))
    kernel: Mapped[str | None] = mapped_column(String(255))
    cpu_model: Mapped[str | None] = mapped_column(String(255))
    cpu_cores: Mapped[int] = mapped_column(Integer)
    ram_bytes: Mapped[int] = mapped_column(Integer)
    disk_bytes: Mapped[int] = mapped_column(Integer)
    ip_addresses: Mapped[list[str]] = mapped_column(JSON, default=list)
    inventory: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    project: Mapped[Project] = relationship(back_populates="agents")
    tags: Mapped[list["Tag"]] = relationship(secondary=agent_tags, back_populates="agents")

    __table_args__ = (
        UniqueConstraint("project_id", "agent_id", name="uq_agent_project_external_id"),
        CheckConstraint("cpu_cores > 0", name="ck_agent_cpu_cores_positive"),
        CheckConstraint("ram_bytes >= 0", name="ck_agent_ram_nonnegative"),
        CheckConstraint("disk_bytes >= 0", name="ck_agent_disk_nonnegative"),
        Index("ix_agents_project_status_seen", "project_id", "status", "last_seen_at"),
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64))
    project: Mapped[Project] = relationship(back_populates="tags")
    agents: Mapped[list[Agent]] = relationship(secondary=agent_tags, back_populates="tags")

    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_tag_project_name"),)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
