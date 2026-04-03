from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    
    # Связь с хостами (одна группа - много хостов)
    hosts = relationship("Host", back_populates="group")