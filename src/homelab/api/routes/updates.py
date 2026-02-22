from fastapi import APIRouter, Depends, HTTPException
from homelab.api.dependencies import (
    get_db,
    verify_container_exists
)
from homelab.api.models import (
    UpdateCheckResponse,
    UpdateRequest,
    UpdateResponse,
    AutoUpdateConfigRequest
)
from homelab.core.update_manager import UpdateManager
from homelab.core.update_checker import UpdateChecker
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/{container_name}/check", response_model=UpdateCheckResponse)
def check_for_update(
    container_name: str = Depends(verify_container_exists),
    db: Session = Depends(get_db)
):
    """Check if a newer version is available"""
    checker = UpdateChecker(db)
    update_info = checker.check_for_update(container_name)
    
    if not update_info:
        raise HTTPException(status_code=400, detail="Unable to check for updates")
    
    return {
        "container": update_info['container_name'],
        "current_digest": update_info['current_digest'],
        "latest_digest": update_info['latest_digest'],
        "update_available": update_info['update_available'],
        "checked_at": update_info['checked_at']
    }

@router.post("/{container_name}/update", response_model=UpdateResponse)
def update_container(
    container_name: str = Depends(verify_container_exists),
    request: UpdateRequest = UpdateRequest(),
    db: Session = Depends(get_db)
):
    """Update container to latest version"""
    # Check if update available
    checker = UpdateChecker(db)
    update_info = checker.check_for_update(container_name)
    
    if not update_info or not update_info['update_available']:
        raise HTTPException(status_code=400, detail="No update available")
    
    # Perform update
    manager = UpdateManager(db)
    
    try:
        result = manager.update_container(container_name)
        
        if not result['updated']:
            # Update failed
            raise HTTPException(
                status_code=500,
                detail=f"Update failed: {result.get('reason')} - {result.get('error')}"
            )
        
        # Success
        return {
            "success": True,
            "container": container_name,
            "pre_update_snapshot_id": result['before_snapshot'],
            "post_update_snapshot_id": result['after_snapshot'],
            "updated_from": update_info['current_digest'][:20] + "...",
            "updated_to": result['latest_digest'][:20] + "...",
            "message": f"Successfully updated {container_name}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

@router.get("/{container_name}/auto-update")
def get_auto_update_config(
    container_name: str,
    db: Session = Depends(get_db)
):
    """Get auto-update configuration for a container"""
    from homelab.core.models import AutoUpdateConfig
    
    config = db.query(AutoUpdateConfig)\
        .filter_by(container_name=container_name)\
        .first()
    
    if not config:
        return {
            "container": container_name,
            "enabled": False,
            "message": "Auto-update not configured"
        }
    
    return {
        "container": container_name,
        "enabled": config.enabled,
        "check_interval_hours": config.check_interval_hours,
        "health_check_duration": config.health_check_duration,
        "auto_rollback": config.auto_rollback,
        "check_only": config.check_only,
        "last_checked": config.last_checked,
        "last_updated": config.last_updated
    }

@router.post("/{container_name}/auto-update")
def configure_auto_update(
    container_name: str = Depends(verify_container_exists),
    request: AutoUpdateConfigRequest = AutoUpdateConfigRequest(),
    db: Session = Depends(get_db)
):
    """Configure auto-update for a container"""
    from homelab.core.models import AutoUpdateConfig
    
    config = db.query(AutoUpdateConfig)\
        .filter_by(container_name=container_name)\
        .first()
    
    if config:
        # Update existing
        config.enabled = request.enabled
        config.check_interval_hours = request.check_interval_hours
        config.health_check_duration = request.health_check_duration
        config.auto_rollback = request.auto_rollback
        config.check_only = request.check_only
        message = f"Updated auto-update config for {container_name}"
    else:
        # Create new
        config = AutoUpdateConfig(
            container_name=container_name,
            enabled=request.enabled,
            check_interval_hours=request.check_interval_hours,
            health_check_duration=request.health_check_duration,
            auto_rollback=request.auto_rollback,
            check_only=request.check_only
        )
        db.add(config)
        message = f"Enabled auto-update for {container_name}"
    
    db.commit()
    
    return {
        "success": True,
        "container": container_name,
        "config": {
            "enabled": config.enabled,
            "check_interval_hours": config.check_interval_hours,
            "health_check_duration": config.health_check_duration,
            "auto_rollback": config.auto_rollback,
            "check_only": config.check_only
        },
        "message": message
    }