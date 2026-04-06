from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.host import Host
from app.admin.auth import get_current_user
from app.models.user import User
from app.schemas.agent_data import HostUpdate

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/hosts")
async def list_hosts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    hosts = db.query(Host).all()
    result = []
    for h in hosts:
        # Если группы нет, подставляем текст
        group_name = h.group.name if h.group else "БезГруппы"
        result.append({
            "id": h.id,
            "hostname": h.hostname,
            "group": group_name,
            "status": h.status
        })
    return result

@router.patch("/hosts/{host_id}")
async def approve_host(
    host_id: str, 
    data: HostUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Защищаем этот метод тоже
):
    # Проверка на права администратора
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You do not have enough permissions"
        )

    db_host = db.query(Host).filter(Host.id == host_id).first()
    if not db_host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    db_host.status = data.status
    db.commit()
    db.refresh(db_host)
    return {"status": "updated", "new_status": db_host.status, "updated_by": current_user.username}