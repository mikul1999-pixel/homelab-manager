from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from homelab.api.dependencies import (
    get_docker_manager,
    get_version_tracker,
    verify_container_exists
)
from homelab.api.models import (
    ContainerInfo,
    ContainerDetail,
    VersionHistoryResponse,
    SnapshotRequest,
    SnapshotInfo,
    RollbackRequest,
    RollbackResponse,
    VersionTagRequest
)
from homelab.core.docker_manager import DockerManager
from homelab.core.version_tracker import VersionTracker

router = APIRouter()

@router.get("", response_model=List[ContainerInfo])
def list_containers(
    all: bool = Query(True, description="Include stopped containers"),
    docker: DockerManager = Depends(get_docker_manager)
):
    """List all containers"""
    containers = docker.list_containers(all=all)
    return containers

@router.get("/{container_name}", response_model=ContainerDetail)
def get_container(
    container_name: str = Depends(verify_container_exists),
    docker: DockerManager = Depends(get_docker_manager),
    tracker: VersionTracker = Depends(get_version_tracker)
):
    """Get detailed container information"""
    details = docker.get_container_details(container_name)
    
    # Add current tag from tracking
    tag_info = tracker.get_version_info(container_name)
    details['current_tag'] = tag_info.tag if tag_info else None
    
    return details

@router.get("/{container_name}/history", response_model=VersionHistoryResponse)
def get_history(
    container_name: str,
    limit: int = Query(50, ge=1, le=500, description="Max number of history entries"),
    tracker: VersionTracker = Depends(get_version_tracker)
):
    """Get version history for a container"""
    history = tracker.get_history(container_name)
    
    # Limit results
    history = history[:limit]
    
    return {
        "container": container_name,
        "history": history
    }

@router.post("/{container_name}/snapshot", response_model=SnapshotInfo)
def create_snapshot(
    container_name: str = Depends(verify_container_exists),
    tracker: VersionTracker = Depends(get_version_tracker)
):
    """Create a snapshot of container's current state"""
    try:
        snapshot = tracker.create_snapshot(container_name)
        return snapshot
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create snapshot: {str(e)}")

@router.post("/{container_name}/rollback", response_model=RollbackResponse)
def rollback_container(
    container_name: str,
    request: RollbackRequest,
    tracker: VersionTracker = Depends(get_version_tracker)
):
    """Rollback container to a previous snapshot"""
    try:
        # Get snapshot info
        snapshot = tracker.get_snapshot_by_id(request.snapshot_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail=f"Snapshot {request.snapshot_id} not found")
        
        if snapshot.container_name != container_name:
            raise HTTPException(
                status_code=400,
                detail=f"Snapshot {request.snapshot_id} belongs to {snapshot.container_name}, not {container_name}"
            )
        
        # Perform rollback
        result = tracker.rollback_container(container_name, request.snapshot_id)
        
        return {
            "success": True,
            "container": container_name,
            "snapshot_id": request.snapshot_id,
            "rolled_back_to": snapshot.image_version,
            "compose_synced": result['compose_synced'],
            "message": f"Successfully rolled back to snapshot #{request.snapshot_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")

@router.post("/{container_name}/version-tag")
def change_version_tag(
    container_name: str,
    request: VersionTagRequest,
    tracker: VersionTracker = Depends(get_version_tracker)
):
    """Change the version tag for a container"""
    try:
        result = tracker.add_version_tag(container_name, request.tag)
        
        return {
            "success": True,
            "container": container_name,
            "old_tag": result['old_tag'],
            "new_tag": result['new_tag'],
            "compose_synced": result['compose_synced'],
            "message": f"Version tag changed from {result['old_tag']} to {result['new_tag']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to change version tag: {str(e)}")