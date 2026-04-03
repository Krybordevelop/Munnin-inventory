from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.schemas.agent_data import AgentRegistration
from app.core.database import get_db
from app.models.group import Group
from app.models.host import Host

router = APIRouter(prefix="/api/v1", tags=["agents"])

@router.post("/register", status_code=201)
async def register_agent(data: AgentRegistration, request: Request, db: Session = Depends(get_db)):
    # 1. Ищем группу по токену
    group = db.query(Group).filter(Group.token == data.token).first()
    if not group:
        raise HTTPException(status_code=403, detail="Invalid group token")

    # 2. Ищем, есть ли уже такой агент в базе
    db_host = db.query(Host).filter(Host.id == data.agent_id).first()

    # Собираем данные из присланного JSON
    specs_json = {
        "os": data.os_info.model_dump(),
        "hardware": data.hardware.model_dump()
    }

    if db_host:
        # Если агент уже есть — обновляем данные
        db_host.hostname = data.hostname
        db_host.ip_v4 = request.client.host
        db_host.specs = specs_json
    else:
        # ЕСЛИ АГЕНТА НЕТ — СОЗДАЕМ (вот тут рождается db_host)
        db_host = Host(
            id=data.agent_id,
            hostname=data.hostname,
            ip_v4=request.client.host,
            specs=specs_json,
            group_id=group.id
        )
        db.add(db_host)

    # 3. Сохраняем изменения в БД
    db.commit()
    db.refresh(db_host)

    # 4. Теперь db_host точно существует и мы можем его вернуть
    return {
        "id": db_host.id,
        "status": db_host.status,
        "message": f"Agent {data.hostname} registered. Awaiting admin approval."
    }