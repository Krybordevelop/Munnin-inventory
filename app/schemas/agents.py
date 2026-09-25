import ipaddress
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.models import AgentStatus

AgentIdentifier = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
]


class OSReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=120)
    kernel: str | None = Field(default=None, max_length=255)


class HardwareReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cpu_cores: int = Field(gt=0, le=65536)
    cpu_model: str | None = Field(default=None, max_length=255)
    ram_bytes: int = Field(ge=0)
    disk_bytes: int = Field(ge=0)


class AgentReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_id: AgentIdentifier
    hostname: str = Field(min_length=1, max_length=255)
    os: OSReport
    hardware: HardwareReport
    ip_addresses: list[str] = Field(default_factory=list, max_length=128)
    inventory: dict[str, Any] = Field(default_factory=dict)

    @field_validator("ip_addresses")
    @classmethod
    def valid_ips(cls, values: list[str]) -> list[str]:
        return [str(ipaddress.ip_address(value)) for value in values]


class ReportResponse(BaseModel):
    agent_id: str
    status: AgentStatus
    registered_at: datetime
    last_seen_at: datetime


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    agent_id: str
    status: AgentStatus
    description: str
    hostname: str
    os_name: str
    os_version: str
    kernel: str | None
    cpu_model: str | None
    cpu_cores: int
    ram_bytes: int
    disk_bytes: int
    ip_addresses: list[str]
    inventory: dict[str, Any]
    registered_at: datetime
    last_seen_at: datetime
    tags: list[TagOut]


class AgentPage(BaseModel):
    items: list[AgentOut]
    total: int
    page: int
    page_size: int


class AgentAdminUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str | None = Field(default=None, max_length=4000)
    tags: list[str] | None = Field(default=None, max_length=50)
