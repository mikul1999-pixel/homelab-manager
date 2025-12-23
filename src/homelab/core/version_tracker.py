from datetime import datetime
from typing import List, Dict
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