# app/admin/routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.host import Host

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/hosts")
async def list_hosts(db: Session = Depends(get_db)):
    hosts = db.query(Host).all()
    return hosts