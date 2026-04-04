from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class AgentHardware(BaseModel):
    cpu_total: int = Field(..., description="Общее количество ядер CPU")
    ram_total_gb: float = Field(..., description="Общий объем RAM в ГБ")
    disk_total_gb: float = Field(..., description="Общий объем диска в ГБ")

class AgentOS(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Fedora Linux"})
    version: str = Field(..., json_schema_extra={"example": "41"})
    kernel: str = Field(..., json_schema_extra={"example": "6.11.x"})

class AgentRegistration(BaseModel):
    agent_id: str = Field(..., description="Уникальный UUID агента")
    token: str = Field(..., description="Токен группы для авторизации")
    hostname: str
    os_info: AgentOS
    hardware: AgentHardware
    ipv6: Optional[str] = None

class HostUpdate(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected|pending)$")