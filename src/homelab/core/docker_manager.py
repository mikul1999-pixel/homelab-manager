import docker
from typing import List, Dict, Optional
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
        
        # Get version tag from image_tags
        image_version = container.attrs['Config']['Image']

        # Get current image info
        image = container.image
        
        # Get the digest for unique ID
        image_digest = None
        if image.attrs.get('RepoDigests'):
            image_digest = image.attrs['RepoDigests'][0]
        
        # Get image ID
        image_id = image.id
        
        # Extract compose info from labels
        labels = container.labels
        compose_project = labels.get('com.docker.compose.project', None)
        compose_files = labels.get('com.docker.compose.project.config_files', None)
        compose_service = labels.get('com.docker.compose.service', None)
        
        return {
            'id': container.id[:12],
            'name': container.name,
            'image': image_version,
            'image_digest': image_digest,
            'image_id': image_id,
            'status': container.status,
            'env_vars': container.attrs['Config']['Env'],
            'volumes': container.attrs['Mounts'],
            'ports': container.attrs['NetworkSettings']['Ports'],
            'network_mode': container.attrs['HostConfig']['NetworkMode'],
            'networks': list(container.attrs['NetworkSettings']['Networks'].keys()),
            'restart_policy': container.attrs['HostConfig']['RestartPolicy'],
            'labels': labels,
            'compose_project': compose_project,
            'compose_files': compose_files,
            'compose_service': compose_service,
        }

    def start_container(self, name: str) -> None:
        """Start a stopped container"""
        container = self.client.containers.get(name)
        container.start()
    
    def stop_container(self, name: str, timeout: int = 10) -> None:
        """Stop a running container"""
        container = self.client.containers.get(name)
        container.stop(timeout=timeout)
    
    def restart_container(self, name: str, timeout: int = 10) -> None:
        """Restart a container"""
        container = self.client.containers.get(name)
        container.restart(timeout=timeout)
    
    def get_container_logs(
        self, 
        name: str, 
        tail: int = 100, 
        since: Optional[str] = None,
        timestamps: bool = True
    ) -> str:
        """Get logs from a container"""
        container = self.client.containers.get(name)
        
        kwargs = {
            'tail': tail,
            'timestamps': timestamps
        }
        
        if since:
            kwargs['since'] = since
        
        logs = container.logs(**kwargs)
        
        # Decode bytes to string
        if isinstance(logs, bytes):
            return logs.decode('utf-8')
        
        return logs
    
    def recreate_container(self, name: str, image: str, config: Dict, image_digest: Optional[str] = None) -> None:
        """Recreate a container with specific image and config (core rollback mechanism)"""

        try:
            # Get current container
            container = self.client.containers.get(name)
            
            # Stop and remove
            container.stop(timeout=10)
            container.remove()
        except docker.errors.NotFound:
            pass
        
        # Parse info from config
        image_to_use = image_digest if image_digest else image
        volumes = self._parse_volumes(config.get('volumes', []))
        ports = self._parse_ports(config.get('ports', {}))
        environment = config.get('env_vars', [])
        network_mode = config.get('network_mode', 'bridge')
        restart_policy = config.get('restart_policy', {'Name': 'unless-stopped'})
        labels = config.get('labels', {})
        
        # Create new container
        new_container = self.client.containers.run(
            image_to_use,
            name=name,
            detach=True,
            environment=environment,
            volumes=volumes,
            ports=ports,
            network_mode=network_mode,
            restart_policy=restart_policy,
            labels=labels,
        )
        
        return new_container
    
    def _parse_volumes(self, mounts: List[Dict]) -> Dict[str, Dict]:
        """Parse Docker volume mounts into format for containers.run()"""
        volumes = {}
        for mount in mounts:
            if mount['Type'] == 'bind':
                volumes[mount['Source']] = {
                    'bind': mount['Destination'],
                    'mode': mount.get('Mode', 'rw')
                }
            elif mount['Type'] == 'volume':
                volumes[mount['Name']] = {
                    'bind': mount['Destination'],
                    'mode': mount.get('Mode', 'rw')
                }
        return volumes
    
    def _parse_ports(self, ports: Dict) -> Dict:
        """Parse Docker port mappings into format for containers.run()"""
        parsed_ports = {}
        for container_port, host_bindings in ports.items():
            if host_bindings:
                # Take the first binding
                host_port = host_bindings[0]['HostPort']
                parsed_ports[container_port] = int(host_port)
            else:
                # Port exposed but not bound
                parsed_ports[container_port] = None
        return parsed_ports