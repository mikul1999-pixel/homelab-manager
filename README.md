# Homelab Manager

Docker container version management and monitoring tool for home labs. It provides a CLI, API, and background job for tracking image versions, detecting updates, performing rollbacks, and optionally syncing with docker‑compose files.

**++ check out the TUI [here](https://github.com/mikul1999-pixel/homelab-tui)**   
 <br>

## Features

- Version tracking with history
- Update detection
- Container health checks
- One‑click rollbacks
- Dependency management **(on the roadmap)**

### Optional Features

- Automated updates with health monitoring and rollbacks
- docker‑compose file syncing
- Config drift detection **(on the roadmap)**


## Requirements
- Python 3.10+
- Docker (with Docker Compose)
- PostgreSQL 14+
- uv (instead of pip)


## Installation

```bash
# Install dependencies
sudo apt update
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup project
git clone https://github.com/mikul1999-pixel/homelab-manager.git
cd homelab-manager
uv sync
source .venv/bin/activate

# Instructions
homelab init
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

## Background Jobs
There are a couple daemons that you can run in the background, either through a CLI command or as a systemd service

#### A. CLI commands
```homelab scheduler``` runs automated image version checks. + optional: update, health check, rollback

```homelab-api``` starts the api on a local port. used for integration with other apps


#### B. Systemd Service
Instead of running background jobs within the terminal, you can set up systemd services.
<br>

Included example files: <br>
```homelab-scheduler.service```, 
```homelab-api.service```

install systemd services:
```bash
cd homelab-manager
sudo cp <path/*.service> /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now <filename.service>
```

## CLI Commands

#### Container Management
```bash
# List all containers
homelab list

# Show detailed container information
homelab details <container_name>

# Get usage stats
homelab stats <container_name>
homelab stats  # All containers

# Standard container control
homelab start <container_name>
homelab stop <container_name>
homelab restart <container_name>

# Get container logs
homelab logs <container_name> --tail --follow --since
```

#### Version Control
```bash
# Create snapshot of current state
homelab snapshot <container_name>

# View version history
homelab history <container_name>

# Rollback to specific snapshot
homelab rollback <container_name> <snapshot_id>
homelab rollback <container_name> <snapshot_id> --force

# Check if an image update is needed
homelab check-update <container_name>

# Update to newest image version
homelab update <container_name>
homelab update <container_name> --force

# Check the health of a container
homelab health <container_name>

# View major version tag being tracked
homelab version <container_name>

# Change major version tag
homelab change-version <container_name> <tag>

# List all containers and their version tag
homelab list-version
```

#### Automated Checks (Optional)
```bash
# Enable auto-update (+ health checks) for containers
homelab auto-update enable <container_name> --interval --health-duration --no-rollback --check-only

# Disable auto-update. Run 'auto-update enable' again to reset
homelab auto-update disable <container_name>

# Check status
homelab auto-update status

# Test update job (dry-run)
homelab auto-update test <container_name>
homelab auto-update test <container_name> --force

# Start scheduler (runs in background). Can also use systemd
homelab scheduler

# Check logs
homelab logs
homelab logs -f
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

## API Endpoints

#### Example: Local routes, port 3000 
```bash
# Start api (runs in background). Can also use systemd
homelab-api
```

```/api/containers```
```bash
# List containers
curl http://localhost:3000/api/containers

# Get container details
curl http://localhost:3000/api/containers/<container>

# Get usage stats
curl http://localhost:3000/api/containers/<container>/stats
curl http://localhost:3000/api/containers/stats/all

# Start/stop/restart container
curl -X POST http://localhost:3000/api/containers/<container>/start
curl -X POST http://localhost:3000/api/containers/<container>/stop
curl -X POST http://localhost:3000/api/containers/<container>/restart

# Get container logs
curl http://localhost:3000/api/containers/<container>/logs?tail=50

# Create snapshot
curl -X POST http://localhost:3000/api/containers/<container>/snapshot

# Get history
curl http://localhost:3000/api/containers/<container>/history

# Rollback
curl -X POST http://localhost:3000/api/containers/<container>/rollback \
  -H "Content-Type: application/json" \
  -d '{"snapshot_id": 5}'

# Change major version tag
curl -X POST http://localhost:3000/api/containers/<container>/version-tag \
  -H "Content-Type: application/json" \
  -d '{"tag": "v2"}'

# Check health
curl http://localhost:3000/api/containers/<container>/health
```

```/api/updates```
```bash
# Check for update
curl http://localhost:3000/api/updates/<container>/check

# Perform an update
curl -X POST http://localhost:3000/api/updates/<container>/update

# Get auto-update config
curl http://localhost:3000/api/updates/<container>/auto-update

# Configure auto-update
curl -X POST http://localhost:3000/api/updates/<container>/auto-update
```

```/api/snapshots```
```bash
# List snapshots
curl http://localhost:3000/api/snapshots

# Get a snapshot
curl http://localhost:3000/api/snapshots/<snapshot_id>

# Delete a snapshot
curl -X DELETE http://localhost:3000/api/snapshots/<snapshot_id>
```

## Appendix
**Note:** This is a personal project. Features and functionality may change.

<br>

### > Automated Version Control vs Planned Changes
**Version Control** - Snapshot, update, and rollback the container state:
- Alters the underlying image digest (hash of v2.117.0)
- Stays on the same major version (v2 → v2 new digest)
- Does NOT update compose files

**Planned Changes** - Intentional upgrade/downgrade to a different major version:
- Major change (v2 → v3)
- Updates `.env.manager` (if compose sync enabled)
- Requires running `homelab change-version` to apply
- Alters version control to track (v3 → v3 new digest)


### > Docker Compose Integration

Homelab Manager can optionally keep your docker-compose `.env` files in sync with major changes.

#### Setup Process

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
    image: ghcr.io/immich-app/immich-server:${IMMICH_VERSION}
```
You can either combine `.env.manager` and `.env` with a `.sh` script or execute docker compose with `--env-file .env.manager`
```bash
docker compose --env-file .env --env-file .env.manager up -d
```

**3. Verify setup:**
```bash
homelab verify-compose immich-server
```

#### How Compose Sync Works

**Without compose sync:**
- Major changes impact the running container only
- Your compose files are unchanged
- Running `docker-compose up` later will revert to the compose file version

**With compose sync:**
- Major changes update both the container AND `.env.manager`
- Your compose files stay in sync with the running state
- You can run `docker-compose up` without major version conflicts


### > PostgreSQL Management

In addition to commands like `history` or `verify-compose`, you can optionally manually interact with the database
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

SELECT container_name, image_repo, tag, tag_pattern
FROM image_tags 
ORDER BY container_name;
```

<br>

---

