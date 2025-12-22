import docker
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class ContainerInfo:
    """Information about a running container"""
    id: str
    name: str
    image: str
    status: str
    created: str

class DockerManager:
    """Manages Docker container operations"""
    
    def __init__(self):
        self.client = docker.from_env()
    
    def list_containers(self, all: bool = True) -> List[ContainerInfo]:
        """List all containers"""
        containers = self.client.containers.list(all=all)
        return [
            ContainerInfo(
                id=c.id[:12],
                name=c.name,
                image=c.image.tags[0] if c.image.tags else c.image.id[:12],
                status=c.status,
                created=c.attrs['Created']
            )
            for c in containers
        ]
    
    def get_container_details(self, name: str) -> Dict:
        """Get detailed container information"""
        container = self.client.containers.get(name)
        return {
            'id': container.id[:12],
            'name': container.name,
            'image': container.image.tags[0] if container.image.tags else 'unknown',
            'status': container.status,
            'env_vars': container.attrs['Config']['Env'],
            'volumes': container.attrs['Mounts'],
            'ports': container.attrs['NetworkSettings']['Ports'],
        }