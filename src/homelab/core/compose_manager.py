import re
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

class ComposeManager:
    """Manages .env.manager files for compose integration"""
    
    def __init__(self):
        pass
    
    def read_env_file(self, env_path: Path) -> Dict[str, str]:
        """Read .env file into dictionary"""
        env_vars = {}
        
        if not env_path.exists():
            return env_vars
        
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        
        return env_vars
    
    def write_env_file(self, env_path: Path, env_vars: Dict[str, str], 
                       header_comment: Optional[str] = None):
        """Write dictionary to .env file"""
        # Ensure directory exists
        env_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(env_path, 'w') as f:
            # Write header
            if header_comment:
                f.write(f"# {header_comment}\n")
            f.write(f"# Managed by homelab-manager\n")
            f.write(f"# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n")
            
            # Write variables
            for key, value in sorted(env_vars.items()):
                f.write(f"{key}={value}\n")
    
    def update_env_variable(self, env_path: Path, var_name: str, var_value: str):
        """Update a single variable in .env file"""
        env_vars = self.read_env_file(env_path)
        env_vars[var_name] = var_value
        self.write_env_file(env_path, env_vars)
    
    def guess_version_variable(self, container_name: str, service_name: Optional[str] = None) -> str:
        """Default environment variable name from container name"""
        name = service_name or container_name
        
        # Remove common suffixes
        suffixes = ["server", "app", "service", "worker"]
        for suffix in suffixes:
            name = name.replace(f"-{suffix}", "").replace(f"_{suffix}", "")

        if "-" in name:
            base_name = name.split("-")[0]
        elif "_" in name:
            base_name = name.split("_")[0]
        else:
            base_name = name

        # Convert to uppercase and add _VERSION
        return f"{base_name.upper()}_VERSION"
    
    def parse_compose_files_from_label(self, label_value: str) -> List[str]:
        """Parse compose files from Docker label"""
        if not label_value:
            return []
        
        files = label_value.split(',')
        # Get just the filenames
        return [Path(f).name for f in files]
    
    def find_compose_directory(self, label_value: str) -> Optional[Path]:
        """Extract compose directory from Docker label"""
        if not label_value:
            return None
        
        first_file = label_value.split(',')[0]
        return Path(first_file).parent