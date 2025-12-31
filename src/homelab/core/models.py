from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class ImageTag(Base):
    __tablename__ = 'image_tags'
    
    id = Column(Integer, primary_key=True)
    container_name = Column(String, unique=True, nullable=False)
    image_repo = Column(String, nullable=False)
    tag = Column(String, nullable=False)
    tag_pattern = Column(String)
    auto_detect_tags = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VersionHistory(Base):
    __tablename__ = 'version_history'
    
    id = Column(Integer, primary_key=True)
    container_name = Column(String)
    image_version = Column(String) # from image_tags
    image_digest = Column(String)
    image_id = Column(String)
    config_snapshot = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String)  # 'update', 'rollback', 'snapshot'

class ComposeConfig(Base):
    __tablename__ = 'compose_config'
    
    id = Column(Integer, primary_key=True)
    container_name = Column(String, unique=True, nullable=False)
    compose_directory = Column(String, nullable=False)
    compose_files = Column(JSON)
    service_name = Column(String)
    version_variable = Column(String, nullable=False)
    manager_env_path = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AutoUpdateConfig(Base):
    __tablename__ = 'auto_update_config'
    
    id = Column(Integer, primary_key=True)
    container_name = Column(String, unique=True, nullable=False)
    enabled = Column(Boolean, default=True)
    check_interval_hours = Column(Integer, default=12)
    health_check_duration = Column(Integer, default=600)  # seconds
    auto_rollback = Column(Boolean, default=True)
    last_checked = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_db(db_url: str = None):
    """Initialize database"""
    from homelab.config import DATABASE_URL
    
    url = db_url or DATABASE_URL
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)