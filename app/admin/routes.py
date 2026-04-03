from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.host import Host
from app.schemas.agent_data import HostUpdate # Не забудь добавить эту схему в schemas

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/hosts")
async def list_hosts(db: Session = Depends(get_db)):
    return db.query(Host).all()

@router.patch("/hosts/{host_id}")
async def approve_host(host_id: str, data: HostUpdate, db: Session = Depends(get_db)):
    db_host = db.query(Host).filter(Host.id == host_id).first()
    if not db_host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    db_host.status = data.status
    db.commit()
    db.refresh(db_host)
    return {"status": "updated", "new_status": db_host.status}