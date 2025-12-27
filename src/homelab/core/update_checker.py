from typing import Dict, List, Optional
from datetime import datetime
import docker

class UpdateChecker:
    """Check for updates to container images"""
    
    def __init__(self):
        self.client = docker.from_env()
    
    def check_for_update(self, container_name: str) -> Optional[Dict]:
        """Check if a newer version of the container's image is available"""
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
        
        # Get current image ID
        current_image = container.image
        current_image_id = current_image.id
        
        # Extract the pullable image name (remove digest)
        pullable_image_name = self._get_pullable_image_name(image_name)
        
        # Pull latest version
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
        
        # Get digests
        current_digest = self._get_digest(current_image)
        latest_digest = self._get_digest(latest_image)
        
        # Compare using digest or image ID
        if current_digest and latest_digest:
            update_available = current_digest != latest_digest
        else:
            update_available = current_image_id != latest_image_id
        
        if update_available:
            return {
                'container_name': container_name,
                'image_name': pullable_image_name,
                'current_digest': current_digest or current_image_id,
                'latest_digest': latest_digest or latest_image_id,
                'update_available': True,
                'checked_at': datetime.utcnow()
            }
        
        return None
    
    def _get_pullable_image_name(self, image_name: str) -> str:
        """Extract pullable image name from config"""
        # If image was created with digest, remove digest @sha... and add :latest
        if '@sha256:' in image_name:
            # Extract the repo part before @
            repo_part = image_name.split('@')[0]
            # Add :latest if no tag
            if ':' not in repo_part:
                return f"{repo_part}:latest"
            return repo_part
        
        # If no tag specified, add :latest
        if ':' not in image_name and '@' not in image_name:
            return f"{image_name}:latest"
        
        return image_name
    
    def _get_digest(self, image) -> Optional[str]:
        """Get digest from image"""
        # Try RepoDigests
        if image.attrs.get('RepoDigests'):
            return image.attrs['RepoDigests'][0]
        
        # image ID as fallback
        return image.id