from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Request models
class SnapshotRequest(BaseModel):
    pass

class RollbackRequest(BaseModel):
    snapshot_id: int = Field(..., description="Snapshot ID to rollback to")
    force: bool = Field(False, description="Skip confirmation")

class UpdateRequest(BaseModel):
    force: bool = Field(False, description="Skip health checks")

class VersionTagRequest(BaseModel):
    tag: str = Field(..., description="New version tag (e.g., v3)")

class AutoUpdateConfigRequest(BaseModel):
    enabled: bool = Field(True, description="Enable auto-updates")
    check_interval_hours: int = Field(12, ge=1, le=168, description="Check interval in hours")
    health_check_duration: int = Field(600, ge=60, le=3600, description="Health check duration in seconds")
    auto_rollback: bool = Field(True, description="Auto-rollback on failure")
    check_only: bool = Field(True, description="Only run the update check and don't execute")

# Response models
class ContainerInfo(BaseModel):
    name: str
    image: str
    status: str
    created: str
    
    class Config:
        from_attributes = True

class ContainerDetail(BaseModel):
    name: str
    image: str
    image_digest: Optional[str]
    image_id: Optional[str]
    status: str
    env_vars: List[str]
    ports: Dict[str, Any]
    networks: List[str]
    restart_policy: Dict[str, Any]
    compose_project: Optional[str]
    current_tag: Optional[str]

class SnapshotInfo(BaseModel):
    id: int
    container_name: str
    image_version: str
    image_digest: Optional[str]
    timestamp: datetime
    action: str
    
    class Config:
        from_attributes = True

class VersionHistoryResponse(BaseModel):
    container: str
    history: List[SnapshotInfo]

class RollbackResponse(BaseModel):
    success: bool
    container: str
    snapshot_id: int
    rolled_back_to: str
    compose_synced: bool
    message: str

class UpdateResponse(BaseModel):
    success: bool
    container: str
    pre_update_snapshot_id: int
    post_update_snapshot_id: int
    updated_from: str
    updated_to: str
    message: str

class UpdateCheckResponse(BaseModel):
    container: str
    current_digest: str
    latest_digest: str
    update_available: bool
    checked_at: datetime

class HealthCheckResponse(BaseModel):
    container: str
    container_running: bool
    docker_health: Optional[str]
    port_check: Optional[bool]
    overall_healthy: bool
    timestamp: datetime

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None