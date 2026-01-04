from typing import Dict, List, Optional
import docker
from datetime import datetime

class StatsManager:
    """Manage Docker container statistics"""
    
    def __init__(self):
        self.client = docker.from_env()
    
    def get_container_stats(self, container_name: str) -> Dict:
        """Get resource usage stats for a single container"""
        container = self.client.containers.get(container_name)
        raw_stats = container.stats(stream=False)
        
        return self._parse_stats(container.name, raw_stats)
    
    def get_all_container_stats(self) -> List[Dict]:
        """Get stats for all running containers"""
        containers = self.client.containers.list()
        stats_list = []
        
        for container in containers:
            try:
                raw_stats = container.stats(stream=False)
                parsed = self._parse_stats(container.name, raw_stats)
                stats_list.append(parsed)
            except Exception as e:
                # Skip containers that error
                stats_list.append({
                    "container": container.name,
                    "status": container.status,
                    "error": str(e)
                })
        
        return stats_list
    
    def _parse_stats(self, container_name: str, stats: Dict) -> Dict:
        """Parse Docker stats into clean format"""
        # CPU Usage
        cpu_percent = self._calculate_cpu_percent(stats)
        
        # Memory Usage
        mem_usage = stats['memory_stats'].get('usage', 0)
        mem_limit = stats['memory_stats'].get('limit', 0)
        mem_percent = (mem_usage / mem_limit * 100.0) if mem_limit > 0 else 0.0
        
        # Network I/O
        rx_bytes, tx_bytes = self._calculate_network_io(stats)
        
        # Disk I/O
        read_bytes, write_bytes = self._calculate_block_io(stats)
        
        return {
            "container": container_name,
            "cpu_percent": round(cpu_percent, 2),
            "memory": {
                "usage": mem_usage,
                "limit": mem_limit,
                "percent": round(mem_percent, 2),
                "usage_mb": round(mem_usage / (1024 * 1024), 2),
                "limit_mb": round(mem_limit / (1024 * 1024), 2)
            },
            "network": {
                "rx_bytes": rx_bytes,
                "tx_bytes": tx_bytes,
                "rx_mb": round(rx_bytes / (1024 * 1024), 2),
                "tx_mb": round(tx_bytes / (1024 * 1024), 2)
            },
            "block_io": {
                "read_bytes": read_bytes,
                "write_bytes": write_bytes,
                "read_mb": round(read_bytes / (1024 * 1024), 2),
                "write_mb": round(write_bytes / (1024 * 1024), 2)
            },
            "timestamp": datetime.utcnow()
        }
    
    def _calculate_cpu_percent(self, stats: Dict) -> float:
        """Calculate CPU usage percentage"""
        cpu_stats = stats.get('cpu_stats', {})
        precpu_stats = stats.get('precpu_stats', {})
        
        # Get CPU usage deltas
        cpu_usage = cpu_stats.get('cpu_usage', {})
        precpu_usage = precpu_stats.get('cpu_usage', {})
        
        cpu_delta = cpu_usage.get('total_usage', 0) - precpu_usage.get('total_usage', 0)
        system_delta = cpu_stats.get('system_cpu_usage', 0) - precpu_stats.get('system_cpu_usage', 0)
        
        # Calculate percentage
        if system_delta > 0 and cpu_delta > 0:
            cpu_count = cpu_stats.get('online_cpus', len(cpu_usage.get('percpu_usage', [1])))
            return (cpu_delta / system_delta) * cpu_count * 100.0
        
        return 0.0
    
    def _calculate_network_io(self, stats: Dict) -> tuple:
        """Calculate network RX/TX bytes"""
        networks = stats.get('networks', {})
        
        rx_bytes = sum(net.get('rx_bytes', 0) for net in networks.values())
        tx_bytes = sum(net.get('tx_bytes', 0) for net in networks.values())
        
        return rx_bytes, tx_bytes
    
    def _calculate_block_io(self, stats: Dict) -> tuple:
        """Calculate disk read/write bytes"""
        blkio_stats = stats.get('blkio_stats', {})
        io_service_bytes = blkio_stats.get('io_service_bytes_recursive', [])
        
        read_bytes = 0
        write_bytes = 0
        
        for entry in io_service_bytes:
            if entry.get('op') == 'Read':
                read_bytes += entry.get('value', 0)
            elif entry.get('op') == 'Write':
                write_bytes += entry.get('value', 0)
        
        return read_bytes, write_bytes