from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Container(Base):
    __tablename__ = 'containers'
    
    id = Column(Integer, primary_key=True)
    docker_id = Column(String, unique=True)
    name = Column(String, unique=True)
    current_image = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VersionHistory(Base):
    __tablename__ = 'version_history'
    
    id = Column(Integer, primary_key=True)
    container_name = Column(String)
    image_version = Column(String)
    config_snapshot = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String)  # 'update', 'rollback', 'snapshot'

def init_db(db_url: str = None):
    """Initialize database"""
    from homelab.config import DATABASE_URL
    
    url = db_url or DATABASE_URL
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)