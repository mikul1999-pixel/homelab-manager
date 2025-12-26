import docker
from typing import Dict, List, Optional
from datetime import datetime

class UpdateChecker:
    """Check for updates to container images"""
    
    def __init__(self):
        self.client = docker.from_env()
    
    def check_for_update(self, container_name: str) -> Optional[Dict]:
        """Check if a newer version of the container's image is available"""
        # Get container info
        container = self.client.containers.get(container_name)
        current_image = container.image
        
        current_digest = None
        if current_image.attrs.get('RepoDigests'):
            current_digest = current_image.attrs['RepoDigests'][0]
        
        # Get image name (without tag, :version_tag)
        image_name = current_image.tags[0] if current_image.tags else None
        if not image_name:
            return None
        
        # Pull latest version
        try:
            latest_image = self.client.images.pull(image_name)
        except Exception as e:
            print(f"Error pulling {image_name}: {e}")
            return None
        
        # Get latest digest
        latest_digest = None
        if latest_image.attrs.get('RepoDigests'):
            latest_digest = latest_image.attrs['RepoDigests'][0]
        
        # Compare digests
        if latest_digest and current_digest and latest_digest != current_digest:
            return {
                'container_name': container_name,
                'image_name': image_name,
                'current_digest': current_digest,
                'latest_digest': latest_digest,
                'update_available': True,
                'checked_at': datetime.utcnow()
            }
        
        return None
    
    def check_all_containers(self) -> List[Dict]:
        """Check all running containers for updates"""
        containers = self.client.containers.list()
        updates = []
        
        for container in containers:
            update_info = self.check_for_update(container.name)
            if update_info:
                updates.append(update_info)
        
        return updates