import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Config vars
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://homelab:homelab@localhost:5432/homelab')
DOCKER_HOST = os.getenv('DOCKER_HOST', 'unix:///var/run/docker.sock')
DASHBOARD_HOST = os.getenv('DASHBOARD_HOST', '0.0.0.0')
DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', '8050'))