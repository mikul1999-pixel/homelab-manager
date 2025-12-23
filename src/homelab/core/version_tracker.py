from datetime import datetime
from typing import List, Dict, Optional
from homelab.core.models import VersionHistory, Container
from homelab.core.docker_manager import DockerManager

class VersionTracker:
    """Tracks container version history"""
    
    def __init__(self, session):
        self.session = session
        self.docker_manager = DockerManager()
    
    def create_snapshot(self, container_name: str) -> VersionHistory:
        """Create a snapshot of current container state"""
        details = self.docker_manager.get_container_details(container_name)
        
        snapshot = VersionHistory(
            container_name=container_name,
            image_version=details['image'],
            config_snapshot=details,
            action='snapshot'
        )
        
        self.session.add(snapshot)
        self.session.commit()
        return snapshot
    
    def get_history(self, container_name: str) -> List[VersionHistory]:
        """Get version history for a container"""
        return self.session.query(VersionHistory)\
            .filter_by(container_name=container_name)\
            .order_by(VersionHistory.timestamp.desc())\
            .all()
    
    def get_snapshot_by_id(self, snapshot_id: int) -> Optional[VersionHistory]:
        """Get a specific snapshot by ID"""
        return self.session.query(VersionHistory)\
            .filter_by(id=snapshot_id)\
            .first()
    
    def rollback_container(self, container_name: str, snapshot_id: int) -> VersionHistory:
        """
        Rollback container to a specific snapshot
        """
        # Get the target snapshot
        snapshot = self.get_snapshot_by_id(snapshot_id)
        
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        
        if snapshot.container_name != container_name:
            raise ValueError(
                f"Snapshot {snapshot_id} is for {snapshot.container_name}, "
                f"not {container_name}"
            )
        
        # Rollback via Docker API
        self.docker_manager.recreate_container(
            name=container_name,
            image=snapshot.image_version,
            config=snapshot.config_snapshot
        )
        
        # Log the rollback action
        rollback_record = VersionHistory(
            container_name=container_name,
            image_version=snapshot.image_version,
            config_snapshot={
                'action': 'rollback',
                'from_snapshot_id': snapshot_id,
                'original_timestamp': str(snapshot.timestamp)
            },
            action='rollback'
        )
        self.session.add(rollback_record)
        self.session.commit()
        
        return rollback_record
    
    def get_current_version(self, container_name: str) -> Optional[str]:
        """Get the currently running version of a container"""
        try:
            details = self.docker_manager.get_container_details(container_name)
            return details['image']
        except Exception:
            return None