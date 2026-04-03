from sqlalchemy import Column, String, Integer, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Host(Base):
    __tablename__ = "hosts"

    id = Column(String, primary_key=True, index=True)  # UUID от агента
    hostname = Column(String, nullable=False)
    ip_v4 = Column(String)
    ip_v6 = Column(String, nullable=True)
    status = Column(String, default="pending")  # approved, rejected
    
    # Железо и ОС храним в JSON
    specs = Column(JSON) 
    
    # Внешний ключ на группу
    group_id = Column(Integer, ForeignKey("groups.id"))
    
    # Обратная связь
    group = relationship("Group", back_populates="hosts")
    
    # Таймштампы
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)