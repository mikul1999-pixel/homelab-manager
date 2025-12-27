from typing import Dict, List, Optional
from datetime import datetime
import docker
from homelab.core.models import VersionHistory, ImageTag
from homelab.core.docker_manager import DockerManager
from homelab.core.version_tracker import VersionTracker

class UpdateChecker:
    """Check for updates to container images"""
    
    def __init__(self, session):
        self.client = docker.from_env()
        self.session = session
        self.tracker = VersionTracker(session)

    def get_current_image(self, container_name: str) -> Optional[Dict]:
        """Pull the current image info for a container""" 
        try:
            container = self.client.containers.get(container_name)
        except docker.errors.NotFound:
            print(f"Container {container_name} not found")
            return None

        # Get image name from container config
        image_name = container.attrs['Config']['Image']
        
        if not image_name:
            print(f"Container {container_name} has no image name")
            return None
        
        # Extract image info
        current_image = container.image
        current_image_id = current_image.id
        current_digest = self._get_digest(current_image)

        return {
            'container_name': container_name,
            'image': current_image,
            'image_id': current_image_id,
            'digest': current_digest,
            'version_reference': current_digest or current_image_id
        }
    
    def check_for_update(self, container_name: str, on_event=None) -> Optional[Dict]:
        """Check if a newer version of the container's image is available"""
        def emit(msg):
            if on_event:
                on_event(msg)

        # Get current image info
        current_info = self.get_current_image(container_name)
        current_image = current_info['image']
        current_image_id = current_info['image_id']
        current_digest = current_info['digest']
        
        # Get image tag name to track
        pullable_image_name = self.tracker.get_version_name(container_name)
        
        # Pull latest image info
        print(f"  Pulling {pullable_image_name}...")
        try:
            latest_image = self.client.images.pull(pullable_image_name)
        except docker.errors.APIError as e:
            print(f"  Error pulling {pullable_image_name}: {e}")
            return None
        except Exception as e:
            print(f"  Unexpected error pulling {pullable_image_name}: {e}")
            return None
        
        latest_image_id = latest_image.id
        latest_digest = self._get_digest(latest_image)
        
        # Compare using digest or image ID
        if current_digest and latest_digest:
            update_available = current_digest != latest_digest
        else:
            update_available = current_image_id != latest_image_id
        
        if update_available:
            update_info = {
                'container_name': container_name,
                'image_name': pullable_image_name,
                'current_digest': current_digest or current_image_id,
                'latest_digest': latest_digest or latest_image_id,
                'update_available': True,
                'checked_at': datetime.utcnow()
            }
            current_short = update_info['current_digest'].split(':')[-1][:16] if ':' in update_info['current_digest'] else update_info['current_digest'][:16]
            latest_short = update_info['latest_digest'].split(':')[-1][:16] if ':' in update_info['latest_digest'] else update_info['latest_digest'][:16]
            
            emit(f"\nUpdate available for {container_name}!")
            emit(f"   Current digest: {current_short}...")
            emit(f"   Latest digest:  {latest_short}...")
            return update_info
        
        emit(f"{container_name} is up to date")
        return None
    
    def _get_digest(self, image) -> Optional[str]:
        """Get digest from image"""
        # Try RepoDigests
        if image.attrs.get('RepoDigests'):
            return image.attrs['RepoDigests'][0]
        
        # image ID as fallback
        return image.id