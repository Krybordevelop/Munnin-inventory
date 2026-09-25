from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=4000)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class TokenCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)


class TokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class TokenCreated(TokenOut):
    token: str
