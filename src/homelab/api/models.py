from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

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

class VersionTagResponse(BaseModel):
    success: bool
    container: str
    old_tag: str
    old_tag: str
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

class MemoryStats(BaseModel):
    usage: int
    limit: int
    percent: float
    usage_mb: float
    limit_mb: float


class NetworkStats(BaseModel):
    rx_bytes: int
    tx_bytes: int
    rx_mb: float
    tx_mb: float


class BlockIOStats(BaseModel):
    read_bytes: int
    write_bytes: int
    read_mb: float
    write_mb: float


class StatsResponse(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() + 'Z' if v else None
        }
    )
    
    container: str
    cpu_percent: float
    memory: MemoryStats
    network: NetworkStats
    block_io: BlockIOStats
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None