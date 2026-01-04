from fastapi import APIRouter, Depends
from datetime import datetime
from homelab.api.dependencies import (
    get_health_checker,
    verify_container_exists
)
from homelab.api.models import HealthCheckResponse
from homelab.core.health_checker import HealthChecker

router = APIRouter()

@router.get("/health")
def api_health():
    """API health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/containers/{container_name}/health", response_model=HealthCheckResponse)
def check_container_health(
    container_name: str = Depends(verify_container_exists),
    checker: HealthChecker = Depends(get_health_checker)
):
    """Check container health"""
    health = checker.check_container_health(container_name)
    
    return {
        "container": container_name,
        "container_running": health['container_running'],
        "docker_health": health['docker_health'],
        "port_check": health['port_check'],
        "overall_healthy": health['overall_healthy'],
        "timestamp": datetime.utcnow()
    }