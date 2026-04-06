from sqlalchemy import Column, String, Integer, JSON, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Host(Base):
    __tablename__ = "hosts"

    id = Column(String, primary_key=True, index=True)  # UUID от агента
    hostname = Column(String, nullable=False)
    ip_v4 = Column(String)
    ip_v6 = Column(String, nullable=True)
    status = Column(String, default="pending")  # approved, rejected, pending
    
    # Спеки железа (CPU, RAM, Disk) в JSON
    specs = Column(JSON) 
    
    # Связь с группой
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True)
    group = relationship("Group", back_populates="hosts")

    # Таймштампы (теперь на стороне БД)
    # Когда агент впервые постучался
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Когда агент прислал данные в последний раз
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())