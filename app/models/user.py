from sqlalchemy import Column, String, Integer, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

# Таблица связи "Многие-ко-многим" для доступа Юзеров к Группам
user_group_association = Table(
    "user_group",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("group_id", ForeignKey("groups.id"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")  # admin / user
    
    # Группы, к которым у пользователя есть доступ (для роли user)
    allowed_groups = relationship("Group", secondary=user_group_association)