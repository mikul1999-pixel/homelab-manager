# Homelab Manager

Docker container version management and monitoring dashboard for home labs.

## Features
- Version tracking and history
- One-click rollbacks
- Health monitoring dashboards
- Config drift detection
- Dependency management

## Requirements
- Python 3.10+
- Docker (with Docker Compose)
- PostgreSQL 14+

## Installation

### Linux
```bash
# Install dependencies
sudo apt update
sudo apt install python3-pip python3-venv docker.io

# Setup project
git clone <your-repo-url>
cd homelab-manager
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev,dashboard]"
```

### macOS
```bash
# Install dependencies
brew install python docker postgresql

# Setup project
git clone <your-repo-url>
cd homelab-manager
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev,dashboard]"
```

### Windows
```bash
# Install dependencies
# - Install Python 3.10+ from python.org
# - Install Docker Desktop

# Setup project
git clone <your-repo-url>
cd homelab-manager
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev,dashboard]"
```

### Database Setup

**PostgreSQL via Docker**
```bash
docker run -d \
  --name homelab-postgres \
  -e POSTGRES_DB=homelab \
  -e POSTGRES_USER=homelab \
  -e POSTGRES_PASSWORD=homelab \
  -p 5432:5432 \
  postgres:16
```

## Config

Copy `.env.example` to `.env` and customize:
```bash
cp .env.example .env
```

Example `.env`:
```bash
DATABASE_URL=postgresql://homelab:homelab@localhost/homelab
DOCKER_HOST=unix:///var/run/docker.sock
DASHBOARD_PORT=8050
```

## Usage

### CLI Commands
```bash
# List all containers
homelab list

# Show container details
homelab details <container_name>

# Create snapshot of container state
homelab snapshot <container_name>

# View version history
homelab history <container_name>

# Rollback to previous version
homelab rollback <container_name> <version>
```

### Dashboard
```bash
# Start the web dashboard
python -m homelab.dashboard.app

# Visit: http://localhost:8050
```