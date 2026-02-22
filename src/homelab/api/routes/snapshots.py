from fastapi import APIRouter, Depends, HTTPException, Query
from homelab.api.dependencies import get_version_tracker
from homelab.api.models import SnapshotInfo
from homelab.core.version_tracker import VersionTracker

router = APIRouter()

@router.get("", response_model=list[SnapshotInfo])
def list_snapshots(
    limit: int = Query(100, ge=1, le=1000, description="Max snapshots to return"),
    tracker: VersionTracker = Depends(get_version_tracker)
):
    """List all snapshots across all containers"""
    from homelab.core.models import VersionHistory
    
    snapshots = tracker.session.query(VersionHistory)\
        .order_by(VersionHistory.timestamp.desc())\
        .limit(limit)\
        .all()
    
    return snapshots

@router.get("/{snapshot_id}", response_model=SnapshotInfo)
def get_snapshot(
    snapshot_id: int,
    tracker: VersionTracker = Depends(get_version_tracker)
):
    """Get details of a specific snapshot"""
    snapshot = tracker.get_snapshot_by_id(snapshot_id)
    
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
    
    return snapshot

@router.delete("/{snapshot_id}")
def delete_snapshot(
    snapshot_id: int,
    tracker: VersionTracker = Depends(get_version_tracker)
):
    """Delete a snapshot"""
    snapshot = tracker.get_snapshot_by_id(snapshot_id)
    
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
    
    try:
        tracker.session.delete(snapshot)
        tracker.session.commit()
        
        return {
            "success": True,
            "snapshot_id": snapshot_id,
            "message": f"Snapshot {snapshot_id} deleted"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete snapshot: {str(e)}")