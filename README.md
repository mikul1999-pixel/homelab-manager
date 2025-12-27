# Homelab Manager

Docker container version management and monitoring dashboard for home labs. Track image versions, rollback updates, and optionally sync with docker-compose files.


## Features
- Version tracking and history
- One-click rollbacks
- Docker compose syncs (optional)
- Health monitoring dashboards
- Config drift detection
- Dependency management

## Requirements
- Python 3.10+
- Docker (with Docker Compose)
- PostgreSQL 14+

## Installation


```bash
# Install dependencies
sudo apt update
sudo apt install python3-pip python3-venv docker.io

# Setup project
git clone https://github.com/mikul1999-pixel/homelab-manager.git
cd homelab-manager
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev,dashboard]"
```


### Database Setup

**PostgreSQL via Docker**
```bash
cd homelab-manager
docker-compose up -d
```

This starts PostgreSQL using the included `docker-compose.yml`. <br>
You can also use your own PostgreSQL, just update `.env`

## Config

Copy `.env.example` to `.env` and customize:
```bash
cp .env.example .env
```

Initialize database:

```bash
homelab init-db
```

## Usage

### CLI Commands

#### Container Management
```bash
# List all containers
homelab list

# Show detailed container information
homelab details <container_name>
```

#### Version Control
```bash
# Create snapshot of current state
homelab snapshot <container_name>

# View version history
homelab history <container_name>

# Rollback to specific snapshot
homelab rollback <container_name> <snapshot_id>

# Rollback without confirmation
homelab rollback <container_name> <snapshot_id> --force
```

#### Compose Integration (Optional)
```bash
# Enable compose sync (one-time setup)
homelab enable-compose <container_name>

# Verify compose setup
homelab verify-compose <container_name>

# Disable compose sync
homelab disable-compose <container_name>

# List all containers with compose sync enabled
homelab list-compose
```

### Dashboard
```bash
# Start the web dashboard
python -m homelab.dashboard.app

# Visit http://localhost:8050
```

## Appendix: Docker Compose Integration

Homelab Manager can optionally keep your docker-compose `.env` files in sync with rollbacks.

### Setup Process

**1. Enable compose sync:**
```bash
homelab enable-compose immich-server
```

Follow the interactive prompts. This creates an `.env.manager` file with version variables.

**2. Update your compose file:**

Add the `.env.manager` variable to your service:

```yaml
# immich.yml
services:
  immich-server:
    image: ghcr.io/immich-app/immich-server:${IMMICH_VERSION:-v1.117.0}
```
You can either combine `.env.manager` and `.env` with a `.sh` script or execute docker compose with `.env.manager`
```bash
docker compose --env-file .env --env-file .env.manager up -d
```




**3. Verify setup:**
```bash
homelab verify-compose immich-server
```

### How Compose Sync Works

**Without compose sync:**
- Rollback changes the running container only
- Your compose files are unchanged
- Running `docker-compose up` later will revert to the compose file version

**With compose sync:**
- Rollback updates both the container AND `.env.manager`
- Your compose files stay in sync with the running state
- You can run `docker-compose up` anytime without conflicts


## Appendix: PostgreSQL Interactions

If you don't want to use commands like `history` or `verify-compose`, you can optionally manually interact with the database
```bash
cd homelab-manager
docker exec -it homelab_postgres psql -U homelab -d homelab
```

Here are some sample queries
```bash
# Tables are defined in core/models.py
SELECT container_name, image_version, image_digest, image_id, ID, timestamp, action 
FROM version_history 
WHERE container_name='immich-server' 
ORDER BY ID DESC;

SELECT container_name, ID, timestamp
FROM version_history 
WHERE action='snapshot'
ORDER BY container_name, ID DESC;

SELECT container_name, compose_directory, manager_env_path, enabled
FROM compose_config 
ORDER BY container_name;
```

<br>

---

**Note:** This is a personal project. Features and functionality may change.
