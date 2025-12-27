from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from homelab.core.models import VersionHistory, ComposeConfig, ImageTag
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
        
        # Initialize tag tracking if this is first snapshot
        tag_info = self.get_version_info(container_name)
        if not tag_info:
            tag_info = self._init_tag_tracking(container_name, details)

        image_to_use = self.get_version_name(container_name)
        details['image'] = image_to_use
        
        snapshot = VersionHistory(
            container_name=container_name,
            image_version=details.get('image'),
            image_digest=details.get('image_digest'),
            image_id=details.get('image_id'),
            config_snapshot=details,
            action='snapshot'
        )
        
        self.session.add(snapshot)
        self.session.commit()
        return snapshot


    def _init_tag_tracking(self, container_name: str, details: Dict) -> ImageTag:
        """Initialize tag tracking for a container"""
        
        # Get image from Docker container config (original creation image)
        image_full = details.get('image')
        
        # If digest, try to get from config
        if '@sha256:' in image_full:
            config_image = details.get('Config', {}).get('Image', '')
            if ':' in config_image and '@' not in config_image:
                image_full = config_image
            else:
                image_full = image_full.split('@')[0] + ':latest'
        
        # Parse repo and tag
        if ':' in image_full:
            repo, tag = image_full.rsplit(':', 1)
        else:
            repo = image_full
            tag = 'latest'
        
        # Detect tag pattern
        tag_pattern = self._detect_tag_pattern(tag)
        
        tag_info = ImageTag(
            container_name=container_name,
            image_repo=repo,
            tag=tag,
            tag_pattern=tag_pattern,
            auto_detect_tags=False
        )
        
        self.session.add(tag_info)
        self.session.commit()
        
        return tag_info


    def _detect_tag_pattern(self, tag: str) -> str:
        """Detect tag versioning pattern"""
        import re
        
        # Semver: v1.2.3, 1.2.3
        if re.match(r'^v?\d+\.\d+\.\d+', tag):
            return 'semver'
        
        # Major version: v1, v2, 2
        if re.match(r'^v?\d+$', tag):
            return 'major'
        
        # Date-based: 2024.12, 2024.12.1
        if re.match(r'^\d{4}\.\d+', tag):
            return 'date'
        
        # Floating: latest, stable, edge
        if tag.lower() in ['latest', 'stable', 'edge', 'main', 'master']:
            return 'floating'
        
        return 'custom'


    def get_version_info(self, container_name: str) -> Optional[ImageTag]:
        """Get stored image tag info for a container"""
        return self.session.query(ImageTag)\
            .filter_by(container_name=container_name)\
            .first()


    def get_version_name(self, container_name: str) -> Optional[str]:
        """Get the canonical image name (repo:tag) for a container"""
        tag_info = self.get_version_info(container_name)
        if not tag_info:
            return None
        
        return f"{tag_info.image_repo}:{tag_info.tag}"

    def extract_tag_from_version_name(self, image: str) -> str:
        """Extract version tag from (repo:tag) string"""
        if ':' in image:
            return image.split(':')[-1]
        return 'latest'

    def add_version_tag(self, container_name: str, tag: str, on_event=None) -> Optional[Dict]:
        """Change major version tag for a container"""

        def emit(msg):
            if on_event:
                on_event(msg)
                
        # Initialize tag tracking if needed
        details = self.docker_manager.get_container_details(container_name)
        tag_info = self.get_version_info(container_name)

        if not tag_info:
            emit(f"Initializing tag tracking...")
            tag_info = self._init_tag_tracking(container_name, details)
            emit(f"\nVersion info logged for {container_name}")
            emit(f"  repo: {tag_info.repo}")          
            emit(f"  tag: {tag_info.tag}")
            emit(f"  pattern: {tag_info.tag_pattern}")
            emit(f"\n")

        # Change tag
        old_tag = tag_info.tag
        tag_info.tag = tag
        self.session.commit()

        # Check if compose sync is enabled
        compose_config = self.get_compose_config(container_name)
        compose_synced = False
        env_path = None
        
        if compose_config:
            try:
                # Update .env.manager file
                env_path = Path(compose_config.manager_env_path)
                version_value = tag
                
                self.compose_manager.update_env_variable(
                    env_path,
                    compose_config.version_variable,
                    version_value
                )
                
                compose_synced = True
            except Exception as e:
                print(f"Warning: Failed to sync compose: {e}")
        
        return {
            'old_tag': old_tag,
            'new_tag': tag,
            'compose_synced': compose_synced,
            'env_path': str(env_path) if env_path else None,
            'compose_config': compose_config
        }

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
            image_digest=snapshot.image_digest or snapshot.image_id
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
        
        return {
            'rollback_record': rollback_record,
            'snapshot': snapshot
        }