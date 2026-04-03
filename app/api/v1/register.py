from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.agent_data import AgentRegistration
from app.core.database import get_db
# Сюда потом импортируем модели БД

router = APIRouter(prefix="/api/v1", tags=["agents"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_agent(data: AgentRegistration, db: Session = Depends(get_db)):
    # 1. Тут будет проверка токена группы в БД
    # 2. Тут будет логика: если агент новый -> статус pending
    # 3. Если агент старый -> обновляем данные (hostname/IP)
    
    return {
        "status": "pending", 
        "message": f"Agent {data.hostname} registered. Awaiting admin approval."
    }