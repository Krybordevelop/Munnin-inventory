from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.models.group import Group
from app.models.host import Host
from app.admin.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/admin/groups", tags=["admin_groups"])

class GroupSchema(BaseModel):
    name: str
    token: Optional[str] = "default-token"

@router.get("/", response_model=List[GroupSchema])
async def list_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Group).all()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_group(data: GroupSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    
    new_group = Group(name=data.name, token=data.token)
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return new_group

@router.patch("/{group_id}")
async def update_group(group_id: int, data: GroupSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    group.name = data.name
    group.token = data.token
    db.commit()
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(group_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    db.delete(group)
    db.commit()
    return None