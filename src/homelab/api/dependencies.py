from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from homelab.core.models import init_db
from homelab.core.docker_manager import DockerManager
from homelab.core.version_tracker import VersionTracker
from homelab.core.update_checker import UpdateChecker
from homelab.core.update_manager import UpdateManager
from homelab.core.health_checker import HealthChecker
from homelab.config import DATABASE_URL

# Database session
SessionLocal = init_db(DATABASE_URL)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_docker_manager():
    """Get DockerManager instance"""
    return DockerManager()

def get_version_tracker(db: Session = Depends(get_db)):
    """Get VersionTracker instance"""
    return VersionTracker(db)

def get_update_checker(db: Session = Depends(get_db)):
    """Get UpdateChecker instance"""
    return UpdateChecker(db)

def get_update_manager(db: Session = Depends(get_db)):
    """Get UpdateManager instance"""
    return UpdateManager(db)

def get_health_checker():
    """Get HealthChecker instance"""
    return HealthChecker()

def verify_container_exists(container_name: str, docker: DockerManager = Depends(get_docker_manager)):
    """Verify container exists, raise 404 if not"""
    try:
        docker.client.containers.get(container_name)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Container '{container_name}' not found")
    return container_name