import docker

class HealthChecker:
    """Check container health with fallback"""

    def __init__(self):
        self.client = docker.from_env()
    
    def check_container_health(self, container_name: str) -> dict:
        """Check container health using all available methods"""
        results = {
            'container_running': False,
            'docker_health': None,
            'port_check': None,
            'overall_healthy': False
        }
        
        container = self.client.containers.get(container_name)
        
        # Level 1: Is container running?
        results['container_running'] = (container.status == 'running')
        if not results['container_running']:
            return results
        
        # Level 2: Docker health check (if defined)
        health = container.attrs.get('State', {}).get('Health')
        if health:
            results['docker_health'] = health.get('Status')
            if results['docker_health'] == 'healthy':
                results['overall_healthy'] = True
                return results
            elif results['docker_health'] == 'unhealthy':
                results['overall_healthy'] = False
                return results 
            # If 'starting', continue to other checks
        
        # Level 3: Check if any port is accepting connections
        ports = self._get_exposed_ports(container_name)
        if ports:
            for port in ports:
                if self._check_port_open('localhost', port):
                    results['port_check'] = True
                    break
        
        # Determine overall health
        results['overall_healthy'] = self._evaluate_health(results)
        
        return results
    
    def _evaluate_health(self, results: dict) -> bool:
        """Determine if container is healthy based on available checks"""
        # Docker health
        if results['docker_health'] == 'healthy':
            return True
        if results['docker_health'] == 'unhealthy':
            return False
        
        # Port check
        if results['port_check'] is not None:
            return results['port_check']
        
        # Fallback: assume healthy if running
        return results['container_running']
    
    def _get_exposed_ports(self, container_name: str) -> list[int]:
        """Get list of host ports from container attrs"""
        container = self.client.containers.get(container_name)
        ports = container.attrs['NetworkSettings']['Ports']
        
        host_ports = []
        for container_port, bindings in ports.items():
            if bindings:
                host_ports.append(int(bindings[0]['HostPort']))
        
        # Fallback: grab from .env
        if not host_ports:
            return self._get_env_ports(container_name)

        return host_ports
    
    def _get_env_ports(self, container_name: str) -> list[int]:
        """Get list of host ports from container env vars (backup method)"""

        container = self.client.containers.get(container_name)
        env_vars = container.attrs['Config']['Env'] or []

        config_ports = []

        for env in env_vars:
            # Split KEY=VALUE
            if "=" not in env:
                continue
            key, value = env.split("=", 1)

            # search for %PORT and extract 8080:80 --> 8080
            if key == "PORT" or key.endswith("_PORT"):
                host_port = value.split(":", 1)[0]

                if host_port.isdigit():
                    config_ports.append(int(host_port))

        return config_ports

    def _check_port_open(self, host: str, port: int, timeout: int = 3) -> bool:
        """Check if TCP port is accepting connections"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False