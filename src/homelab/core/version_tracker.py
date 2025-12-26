from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from homelab.core.models import VersionHistory, Container, ComposeConfig
from homelab.core.docker_manager import DockerManager
from homelab.core.compose_manager import ComposeManager

class VersionTracker:
    """Tracks container version history"""
    
    def __init__(self, session):
        self.session = session
        self.docker_manager = DockerManager()
        self.compose_manager = ComposeManager()
    
    def create_snapshot(self, container_name: str) -> VersionHistory:
        """Create a snapshot of current container state"""
        details = self.docker_manager.get_container_details(container_name)
        
        snapshot = VersionHistory(
            container_name=container_name,
            image_version=details['image'],
            image_digest=details.get('image_digest'),
            image_id=details.get('image_id'),
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
    
    def get_compose_config(self, container_name: str) -> Optional[ComposeConfig]:
        """Get compose configuration for a container"""
        return self.session.query(ComposeConfig)\
            .filter_by(container_name=container_name, enabled=True)\
            .first()
    
    def is_floating_tag(self, image_version: str) -> bool:
        """Check if image uses a floating tag like :latest, :stable, :edge"""
        if not image_version:
            return False
        
        # Extract tag from image
        if ':' in image_version:
            tag = image_version.split(':')[-1]
            return tag.lower() in ['latest', 'stable', 'edge', 'master', 'main']
        
        return False
    
    def rollback_container(self, container_name: str, snapshot_id: int) -> Dict:
        """Rollback container to a specific snapshot"""
        # Get the target snapshot
        snapshot = self.get_snapshot_by_id(snapshot_id)
        
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        
        if snapshot.container_name != container_name:
            raise ValueError(
                f"Snapshot {snapshot_id} is for {snapshot.container_name}, "
                f"not {container_name}"
            )
        
        # Rollback via Docker API. Use digest for exact version
        self.docker_manager.recreate_container(
            name=container_name,
            image=snapshot.image_version,
            config=snapshot.config_snapshot,
            image_digest=snapshot.image_digest
        )
        
        # Log the rollback action
        rollback_record = VersionHistory(
            container_name=container_name,
            image_version=snapshot.image_version,
            image_digest=snapshot.image_digest,
            image_id=snapshot.image_id,
            config_snapshot={
                'action': 'rollback',
                'from_snapshot_id': snapshot_id,
                'original_timestamp': str(snapshot.timestamp)
            },
            action='rollback'
        )
        self.session.add(rollback_record)
        self.session.commit()
        
        # Check if compose sync is enabled
        compose_config = self.get_compose_config(container_name)
        compose_synced = False
        env_path = None
        uses_floating_tag = self.is_floating_tag(snapshot.image_version)
        
        if compose_config:
            try:
                # Update .env.manager file
                env_path = Path(compose_config.manager_env_path)
                version_value = self.compose_manager.extract_version_from_image(
                    snapshot.image_version
                )
                
                self.compose_manager.update_env_variable(
                    env_path,
                    compose_config.version_variable,
                    version_value
                )
                
                compose_synced = True
            except Exception as e:
                print(f"Warning: Failed to sync compose: {e}")
        
        return {
            'rollback_record': rollback_record,
            'compose_synced': compose_synced,
            'env_path': str(env_path) if env_path else None,
            'compose_config': compose_config,
            'uses_floating_tag': uses_floating_tag,
            'snapshot': snapshot
        }
    
    def get_current_version(self, container_name: str) -> Optional[str]:
        """Get the currently running version of a container"""
        try:
            details = self.docker_manager.get_container_details(container_name)
            return details['image']
        except Exception:
            return None