import click
from homelab.core.docker_manager import DockerManager

@click.group()
def cli():
    """Homelab Manager - Docker container management tool"""
    pass

@cli.command()
def init():
    """Initialize Homelab Manager and show setup instructions."""
    import pathlib
    import os

    SYSTEMD_UNIT_PATH = "homelab-manager/src/homelab/scheduler/homelab-scheduler.service"

    click.echo("\nWelcome to Homelab Manager!")
    click.echo("\nThis tool helps you:")
    click.echo("  • Automatically update your containers")
    click.echo("  • Snapshot and rollback versions safely")
    click.echo("  • Run scheduled health checks")
    click.echo("  • Expose an API for the TUI and Web UI\n")

    click.echo("=== Setup Instructions === \n")

    # Database Setup
    click.echo("Setup PostgreSQL via Docker:")
    click.echo("  cd homelab-manager")
    click.echo("  docker-compose up -d")

    # Config files
    click.echo("\nCLI and service configs:")
    click.echo("  cp .env.example .env")
    click.echo("  config.py")
    click.echo("  logging_config.py")

    # Init DB
    click.echo("\nInitialize database:")
    click.echo("  homelab init-db\n")

    # --- Instructions ---
    click.echo("To enable automatic updates, install the systemd service:")
    click.echo("  cd homelab-manager")
    click.echo(f"  sudo cp {SYSTEMD_UNIT_PATH} /etc/systemd/system/")
    click.echo("  sudo systemctl daemon-reload")
    click.echo("  sudo systemctl enable --now homelab-scheduler.service\n")

    click.echo("You can verify the service with:")
    click.echo("  sudo systemctl status homelab-scheduler.service\n")

    click.echo("You're all set. Enjoy a safer, smarter homelab!\n")


@cli.command()
def list():
    """List all containers"""
    manager = DockerManager()
    containers = manager.list_containers()
    
    click.echo(f"\n{'NAME':<20} {'IMAGE':<40} {'STATUS':<15}")
    click.echo("-" * 75)
    for c in containers:
        click.echo(f"{c.name:<20} {c.image:<40} {c.status:<15}")

@cli.command()
@click.argument('container_name')
def details(container_name):
    """Show detailed container information"""
    manager = DockerManager()
    details = manager.get_container_details(container_name)
    
    click.echo(f"\nContainer: {details['name']}")
    click.echo(f"Image: {details['image']}")
    click.echo(f"Image digest: {details['image_digest']}")
    click.echo(f"Status: {details['status']}")
    click.echo(f"\nEnvironment Variables:")
    for env in details['env_vars']:
        click.echo(f"  {env}")

@cli.command()
def init_db():
    """Initialize the database schema"""
    from homelab.core.models import init_db as initialize_database
    from homelab.config import DATABASE_URL
    
    click.echo(f"Initializing database...")
    click.echo(f"Database URL: {DATABASE_URL}")
    
    try:
        initialize_database(DATABASE_URL)
        click.echo("Database initialized successfully!")
        click.echo("Tables created: containers, version_history")
    except Exception as e:
        click.echo(f"Error initializing database: {e}", err=True)
        raise

@cli.command()
@click.argument('container_name')
def snapshot(container_name):
    """Create a snapshot of container state"""
    from homelab.core.models import init_db
    from homelab.core.version_tracker import VersionTracker
    from homelab.config import DATABASE_URL
    
    Session = init_db(DATABASE_URL)
    session = Session()
    tracker = VersionTracker(session)
    
    try:
        snap = tracker.create_snapshot(container_name)
        click.echo(f"Snapshot created for {container_name}")
        click.echo(f"  ID: {snap.id}")
        click.echo(f"  Version: {snap.image_version}")
        click.echo(f"  Version_ID: {snap.image_id}")
        click.echo(f"  Timestamp: {snap.timestamp}")
    except Exception as e:
        click.echo(f"Error creating snapshot: {e}", err=True)
        raise

@cli.command()
@click.argument('container_name')
def version(container_name):
    """Check which image tag is being tracked for a container"""
    from homelab.core.models import init_db
    from homelab.core.version_tracker import VersionTracker
    from homelab.config import DATABASE_URL
    
    Session = init_db(DATABASE_URL)
    session = Session()
    tracker = VersionTracker(session)

    img = tracker.get_version_info(container_name)
    
    if img:
        img_name = tracker.get_version_name(container_name)
        click.echo(f"Image tracking for {container_name}")
        click.echo(f"  ID: {img.id}")
        click.echo(f"  Version: {img_name}")
        click.echo(f"  Pattern: {img.tag_pattern}")
        click.echo(f"  Detect new tags: {img.auto_detect_tags}")

        # Check if compose sync is enabled
        compose_config = tracker.get_compose_config(container_name)
        if compose_config:
            click.echo(f"  Compose sync: enabled")
        else:
            click.echo(f"  Compose sync: disabled")
            
    else:
        click.echo(f"No image being tracked for {container_name}")
        click.echo(f"To begin tracking, snapshot your container:")
        click.echo(f"homelab snapshot {container_name}")

@cli.command()
@click.argument('container_name')
@click.argument('tag')
def change_version(container_name, tag):
    """Change the image tag to track for a container"""
    from homelab.core.models import init_db
    from homelab.core.version_tracker import VersionTracker
    from homelab.config import DATABASE_URL
    
    Session = init_db(DATABASE_URL)
    session = Session()
    tracker = VersionTracker(session)
    
    try:
        # Check if compose sync is enabled
        compose_config = tracker.get_compose_config(container_name)
        if compose_config:
            click.echo(f"  Compose sync:     enabled")
            click.echo(f"  Will update:      {compose_config.manager_env_path}")
        else:
            click.echo(f"  Compose sync:     disabled")

        # Change tag
        tag_info = tracker.add_version_tag(container_name, tag, on_event=click.echo)

        click.echo(f"\nImage tracked for {container_name}")
        click.echo(f"  Old tag: {tag_info['old_tag']}")
        click.echo(f"  New tag: {tag_info['new_tag']}")

        # Compose sync results
        if tag_info['compose_synced']:
            click.echo(f"\nUpdated {tag_info['env_path']}")
            click.echo(f"\nYour .env.manager file has been updated.")
            click.echo(f"   To apply permanently, run:")
            
            if compose_config and compose_config.compose_files:
                compose_cmd = "docker-compose"
                for f in compose_config.compose_files:
                    compose_cmd += f" -f {f}"
                compose_cmd += " up -d"
                click.echo(f"     cd {compose_config.compose_directory}")
                click.echo(f"     {compose_cmd}")
            else:
                click.echo(f"     cd to your compose directory")
                click.echo(f"     docker-compose up -d")
        else:
            click.echo(f"\nNote: This was a direct container rollback.")
            click.echo(f"   Your docker-compose files were not modified.")
            if not compose_config:
                click.echo(f"   To enable compose sync, run: homelab enable-compose {container_name}")

    except Exception as e:
        click.echo(f"Error updating image tags: {e}", err=True)
        raise

@cli.command()
def list_version():
    """List all containers and their version tag"""
    from homelab.core.models import init_db, ImageTag
    from homelab.config import DATABASE_URL
    
    Session = init_db(DATABASE_URL)
    session = Session()
    
    configs = session.query(ImageTag).all()
    
    if not configs:
        click.echo("\nNo containers with image tags stored")
        click.echo("Run 'homelab snapshot <container>' to store")
        return
    
    click.echo(f"\n{'CONTAINER':<20} {'VERSION REPO':<20} {'VERSION TAG':<20} {'TAG PATTERN':<40}")
    click.echo("-" * 80)
    
    for config in configs:
        click.echo(f"{config.container_name:<20} {config.image_repo:<20} {config.tag:<20} {config.tag_pattern:<40}")
    
    click.echo()

@cli.command()
@click.argument('container_name')
def history(container_name):
    """Show version history for a container"""
    from homelab.core.models import init_db
    from homelab.core.version_tracker import VersionTracker
    from homelab.config import DATABASE_URL
    
    Session = init_db(DATABASE_URL)
    session = Session()
    tracker = VersionTracker(session)
    
    history = tracker.get_history(container_name)
    
    if not history:
        click.echo(f"\nNo history found for {container_name}")
        return
    
    click.echo(f"\nVersion History for {container_name}:")
    click.echo(f"{'ID':<5} {'TIMESTAMP':<20} {'VERSION':<30} {'DIGEST':<16} {'ACTION':<10}")
    click.echo("-" * 95)
    
    for h in history:
        # Show short digest for readability
        digest_short = h.image_id[:12] if h.image_id.startswith('sha256:') else h.image_id[:19]
        click.echo(f"{h.id:<5} {str(h.timestamp):<20} {h.image_version:<30} {digest_short:<16} {h.action:<10}")

@cli.command()
@click.argument('container_name')
@click.argument('snapshot_id', type=int)
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
def rollback(container_name, snapshot_id, force):
    """Rollback container to a previous snapshot"""
    from homelab.core.models import init_db
    from homelab.core.version_tracker import VersionTracker
    from homelab.core.update_checker import UpdateChecker
    from homelab.config import DATABASE_URL
    from pathlib import Path
    
    Session = init_db(DATABASE_URL)
    session = Session()
    tracker = VersionTracker(session)
    checker = UpdateChecker(session)

    # Get snapshot details
    snapshot = tracker.get_snapshot_by_id(snapshot_id)
    if not snapshot:
        click.echo(f"Snapshot {snapshot_id} not found", err=True)
        return 1
    snapshot_reference = snapshot.image_digest or snapshot.image_id
    
    # Get current version
    current_version = checker.get_current_image(container_name)
    current_version_reference = current_version['version_reference']
    
    # Show rollback info
    click.echo(f"\nRollback {container_name} to snapshot #{snapshot_id}:")
    click.echo(f"  Current version:  {current_version_reference or 'unknown'}")
    click.echo(f"  Target digest:    {snapshot_reference}")   
    click.echo(f"  Snapshot date:    {snapshot.timestamp}")
    click.echo(f"  Method:           Direct Docker API")
    
    # Confirm unless --force
    if not force:
        click.echo()
        if not click.confirm('Continue with rollback?'):
            click.echo("Rollback cancelled")
            return 0
    
    # Perform rollback
    try:
        click.echo("\nStopping container...")
        click.echo("Recreating with target version...")
        
        result = tracker.rollback_container(container_name, snapshot_id)
        
        click.echo("Starting container...")
        
        # Digest used for rollback
        if snapshot_reference:
            digest_short = snapshot_reference.split(':')[-1][:16] if ':' in snapshot_reference else snapshot_reference[:16]
            click.echo(f"\nRolled back to {snapshot.image_version}")
            click.echo(f"Using digest: {digest_short}... (exact version)")
        else:
            click.echo(f"\nRolled back to {snapshot.image_version}")
        
        click.echo(f"Rollback recorded (ID: {result['rollback_record'].id})")
        
    except Exception as e:
        click.echo(f"\nRollback failed: {e}", err=True)
        raise


@cli.command()
@click.argument('container_name')
@click.option('--env-path', help='Relative path for .env.manager file (like: immich/.env.manager)')
@click.option('--version-var', help='Environment variable name (like: IMMICH_VERSION)')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompts')
def enable_compose(container_name, env_path, version_var, yes):
    """Enable compose sync for a container"""
    from homelab.core.models import init_db, ComposeConfig
    from homelab.core.version_tracker import VersionTracker
    from homelab.core.compose_manager import ComposeManager
    from homelab.config import DATABASE_URL
    from pathlib import Path
    
    Session = init_db(DATABASE_URL)
    session = Session()
    tracker = VersionTracker(session)
    compose_mgr = ComposeManager()
    
    click.echo(f"\n=== Enable Compose Sync for {container_name} ===\n")
    click.echo("This will create .env.manager files that stay in sync with")
    click.echo("major version changes. No compose commands will be run automatically.\n")
    
    # Check if already enabled
    existing = tracker.get_compose_config(container_name)
    if existing:
        click.echo(f"Compose sync already enabled for {container_name}")
        click.echo(f"   Current path: {existing.manager_env_path}")
        if not yes and not click.confirm('\nReconfigure?'):
            return 0
        # Delete existing config so we can create fresh
        session.delete(existing)
        session.commit()
        click.echo("Removed existing configuration\n")
    
    # Get container details
    try:
        details = tracker.docker_manager.get_container_details(container_name)
    except Exception as e:
        click.echo(f"Error getting container details: {e}", err=True)
        return 1

    # Get current tag info
    tag_info = tracker.get_version_info(container_name)
    current_version = tag_info.tag
    uses_floating_tag = tag_info.tag_pattern == "floating"

    if uses_floating_tag:
        click.echo(f"\nIMPORTANT: This container uses a floating tag (:{current_version})")
        click.echo(f"   └─ The container will be versioned using the exact digest from the snapshot")
        click.echo(f"   └─ However, your .env.manager will still contain: {current_version}")
        click.echo()
        
        if not yes and not click.confirm('Continue with compose sync anyway?'):
            click.echo("\nCompose sync cancelled.")
            click.echo("You can still use rollback without compose sync")
            return 0
        
        click.echo()
    
    # Extract compose info
    compose_files_label = details.get('compose_files')
    compose_service = details.get('compose_service')
    
    if not compose_files_label:
        click.echo(f"Warning: Container not started with docker-compose")
        click.echo(f"   Compose sync may not work correctly")
        if not yes and not click.confirm('\nContinue anyway?'):
            return 0
    
    compose_dir = None
    if compose_files_label:
        compose_dir = compose_mgr.find_compose_directory(compose_files_label)
        compose_files = compose_mgr.parse_compose_files_from_label(compose_files_label)
    else:
        compose_files = []
    
    click.echo("Detected configuration:")
    if compose_dir:
        click.echo(f"  Compose directory: {compose_dir}")
        click.echo(f"  Compose files: {', '.join(compose_files)}")
    if compose_service:
        click.echo(f"  Service name: {compose_service}")
    click.echo(f"  Current image: {details['image']}")
    click.echo()
    
    # Get env path
    if not env_path:
        if compose_service:
            suggested = f"{compose_service.split('-')[0]}/.env.manager"
        else:
            suggested = ".env.manager"
        
        click.echo(f"Where should .env.manager be created?")
        click.echo(f"  1. .env.manager (in compose root)")
        click.echo(f"  2. {suggested} (in service folder)")
        click.echo(f"  3. Custom path")
        
        choice = click.prompt('\nChoice', type=int, default=1)

        if choice == 1:
            env_path = ".env.manager"
        elif choice == 2:
            env_path = suggested
        else:
            env_path = click.prompt('Enter custom path')
    
    if compose_dir:
        full_env_path = compose_dir / env_path
    else:
        compose_dir_input = click.prompt('Enter compose directory', 
                                         default=str(Path.cwd()))
        compose_dir = Path(compose_dir_input)
        full_env_path = compose_dir / env_path
    
    # Get version env variable name
    if not version_var:
        guessed = compose_mgr.guess_version_variable(container_name, compose_service)
        version_var = click.prompt(f'\nVersion variable name', default=guessed)
    
    click.echo()
    
    # Create initial .env.manager
    env_vars = {version_var: current_version}
    
    try:
        compose_mgr.write_env_file(
            full_env_path,
            env_vars,
            header_comment=f"Version management for {container_name}"
        )
        click.echo(f"Created {full_env_path}")
        click.echo(f"Added: {version_var}={current_version}")
    except Exception as e:
        click.echo(f"Error creating .env.manager: {e}", err=True)
        return 1
    
    # Save config to database
    config = ComposeConfig(
        container_name=container_name,
        compose_directory=str(compose_dir),
        compose_files=compose_files,
        service_name=compose_service,
        version_variable=version_var,
        manager_env_path=str(full_env_path),
        enabled=True
    )
    
    session.add(config)
    session.commit()
    
    click.echo(f"Configuration saved\n")
    
    click.echo("━" * 60)
    click.echo("Next Steps:")
    click.echo("━" * 60)
    click.echo()
    
    # Instruct user how to execute compose files
    target_file = "your docker-compose yml"
    
    click.echo(f"1. .env.manager for {target_file} is ready! \n")
    click.echo()
    click.echo(f"2. Test the configuration:\n")
    click.echo(f"   cd {compose_dir}")
    
    if compose_files:
        compose_cmd = f"docker-compose --env-file {env_path}"
        for f in compose_files:
            compose_cmd += f" -f {f}"
        compose_cmd += " config | grep " + version_var
        click.echo(f"   {compose_cmd}")
    else:
        click.echo(f"   docker-compose --env-file {env_path} config | grep {version_var}")
    
    click.echo()
    click.echo(f"3. Verify with:\n")
    click.echo(f"   homelab verify-compose {container_name}")
    click.echo()
    click.echo("━" * 60)
    click.echo()
    click.echo("Compose sync enabled! Future version tag changes will automatically")
    click.echo("update .env.manager. You can run docker-compose whenever")
    click.echo("you want to apply the major change.")
    click.echo()

@cli.command()
@click.argument('container_name')
@click.option('--keep-file', is_flag=True, help='Keep .env.manager file (default: delete)')
def disable_compose(container_name, keep_file):
    """Disable compose sync for a container"""
    from homelab.core.models import init_db
    from homelab.core.version_tracker import VersionTracker
    from homelab.config import DATABASE_URL
    from pathlib import Path
    
    Session = init_db(DATABASE_URL)
    session = Session()
    tracker = VersionTracker(session)
    
    config = tracker.get_compose_config(container_name)
    
    if not config:
        click.echo(f"Compose sync not enabled for {container_name}")
        return 0
    
    env_path = Path(config.manager_env_path)
    
    # Delete the database record
    session.delete(config)
    session.commit()
    
    click.echo(f"Compose sync disabled for {container_name}")
    
    # Optionally delete .env.manager file
    if not keep_file and env_path.exists():
        try:
            env_path.unlink()
            click.echo(f"Deleted {env_path}")
        except Exception as e:
            click.echo(f"Could not delete {env_path}: {e}")
    else:
        if env_path.exists():
            click.echo(f"  .env.manager file kept at {env_path}")
        else:
            click.echo(f"  .env.manager file not found at {env_path}")

@cli.command()
@click.argument('container_name')
def verify_compose(container_name):
    """Verify compose sync setup for a container"""
    from homelab.core.models import init_db
    from homelab.core.version_tracker import VersionTracker
    from homelab.core.compose_manager import ComposeManager
    from homelab.config import DATABASE_URL
    from pathlib import Path
    
    Session = init_db(DATABASE_URL)
    session = Session()
    tracker = VersionTracker(session)
    compose_mgr = ComposeManager()
    
    click.echo(f"\nVerifying compose setup for {container_name}...\n")
    
    # Check if enabled
    config = tracker.get_compose_config(container_name)
    if not config:
        click.echo(f"Compose sync not enabled")
        click.echo(f"  Run: homelab enable-compose {container_name}")
        return 1
    
    click.echo(f"Compose sync enabled")
    
    # Check .env.manager exists
    env_path = Path(config.manager_env_path)
    if not env_path.exists():
        click.echo(f".env.manager not found: {env_path}")
        return 1
    
    click.echo(f".env.manager exists: {env_path}")
    
    # Check variable in .env.manager
    env_vars = compose_mgr.read_env_file(env_path)
    if config.version_variable not in env_vars:
        click.echo(f"Variable {config.version_variable} not in .env.manager")
        return 1
    
    click.echo(f"Variable {config.version_variable} present in .env.manager")
    
    # Get current container version
    tag_info = tracker.get_version_info(container_name)
    current_version = tag_info.tag

    if current_version:
        container_ver = current_version
        env_ver = env_vars[config.version_variable]
        
        if container_ver == env_ver:
            click.echo(f"Version in sync: {container_ver}")
        else:
            click.echo(f"Version mismatch:")
            click.echo(f"  Container: {container_ver}")
            click.echo(f"  .env.manager: {env_ver}")
    
    click.echo(f"\nEverything looks good!")
    return 0

@cli.command()
def list_compose():
    """List all containers with compose sync enabled"""
    from homelab.core.models import init_db, ComposeConfig
    from homelab.config import DATABASE_URL
    
    Session = init_db(DATABASE_URL)
    session = Session()
    
    configs = session.query(ComposeConfig).filter_by(enabled=True).all()
    
    if not configs:
        click.echo("\nNo containers with compose sync enabled")
        click.echo("Run 'homelab enable-compose <container>' to enable")
        return
    
    click.echo(f"\n{'CONTAINER':<20} {'VERSION VAR':<20} {'ENV PATH':<40}")
    click.echo("-" * 80)
    
    for config in configs:
        click.echo(f"{config.container_name:<20} {config.version_variable:<20} {config.manager_env_path:<40}")
    
    click.echo()

@cli.command()
@click.argument('container_name')
def check_update(container_name):
    """Check if a newer version of the container image is available"""
    from homelab.core.update_checker import UpdateChecker
    from homelab.core.update_manager import UpdateManager
    from homelab.core.models import init_db
    from homelab.config import DATABASE_URL
    
    Session = init_db(DATABASE_URL)
    session = Session()
    checker = UpdateChecker(session)
    updater = UpdateManager(session)
    
    click.echo(f"Checking for updates to {container_name}...")
    
    update_info = checker.check_for_update(container_name, on_event=click.echo,)
    
    if not update_info:
        return 0
    
    # Show available update
    click.echo(f"\nTo update:")
    click.echo(f"  homelab update {container_name}")
    
    return 0

@cli.command()
@click.argument('container_name')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
def update(container_name, force):
    """Update container to latest image version"""
    from homelab.core.update_checker import UpdateChecker
    from homelab.core.update_manager import UpdateManager
    from homelab.core.models import init_db, VersionHistory
    from homelab.core.version_tracker import VersionTracker
    from homelab.config import DATABASE_URL
    from pathlib import Path
    
    Session = init_db(DATABASE_URL)
    session = Session()
    tracker = VersionTracker(session)
    checker = UpdateChecker(session)
    updater = UpdateManager(session)
    
    update_info = checker.check_for_update(container_name, on_event=click.echo,)
    if not update_info:
        return 0

    # Confirm unless --force
    if not force:
        click.echo()
        if not click.confirm("Continue with update?"):
            click.echo("Update cancelled")
            return 0

    # Perform update
    result = updater.update_container(container_name, on_event=click.echo,)

    if not result.get("updated"):
        click.echo(f"\nUpdate failed: {result.get('reason')}")
        if "error" in result:
            click.echo(f"Error: {result['error']}")
        return 1

    # Success summary
    click.echo(f"\nSuccessfully updated {container_name}")
    click.echo(f"\nSnapshots created:")
    click.echo(f"  • Before update: ID {result['before_snapshot']}")
    click.echo(f"  • After update:  ID {result['after_snapshot']}")

    click.echo(f"\nIf issues occur, rollback with:")
    click.echo(f"  homelab rollback {container_name} {result['before_snapshot']}")

    return 0

@cli.command()
@click.argument('container_name')
def health(container_name):
    """Check the health of a container"""
    from homelab.core.health_checker import HealthChecker
    
    health = HealthChecker()

    try:
        health_result = health.check_container_health(container_name)
        click.echo(f"Health for {container_name}")
        click.echo(f"  Running: {health_result['container_running']}")
        click.echo(f"  Docker Check: {health_result['docker_health']}")
        click.echo(f"  Port Check: {health_result['port_check']}")
        click.echo(f"  Overall Healthy: {health_result['overall_healthy']}")
    except Exception as e:
        click.echo(f"Error checking health: {e}", err=True)
        raise




@cli.group()
def auto_update():
    """Manage automatic updates"""
    pass

@auto_update.command()
@click.argument('container_name')
@click.option('--interval', default=12, help='Check interval in hours')
@click.option('--health-duration', default=600, help='Health monitoring duration in seconds')
@click.option('--no-rollback', is_flag=True, help='Disable automatic rollback on failure')
def enable(container_name, interval, health_duration, no_rollback):
    """Enable automatic updates for a container"""
    from homelab.core.models import init_db, AutoUpdateConfig
    from homelab.config import DATABASE_URL
    
    Session = init_db(DATABASE_URL)
    session = Session()
    
    # Check if already exists
    config = session.query(AutoUpdateConfig)\
        .filter_by(container_name=container_name)\
        .first()
    
    if config:
        config.enabled = True
        config.check_interval_hours = interval
        config.health_check_duration = health_duration
        config.auto_rollback = not no_rollback
        click.echo(f"Updated auto-update config for {container_name}")
    else:
        config = AutoUpdateConfig(
            container_name=container_name,
            enabled=True,
            check_interval_hours=interval,
            health_check_duration=health_duration,
            auto_rollback=not no_rollback
        )
        session.add(config)
        click.echo(f"Enabled auto-update for {container_name}")
    
    session.commit()
    
    click.echo(f"\nConfiguration:")
    click.echo(f"  Check interval: every {interval} hours")
    click.echo(f"  Health monitoring: {health_duration} seconds")
    click.echo(f"  Auto-rollback: {'enabled' if not no_rollback else 'disabled'}")
    click.echo(f"\nThe scheduler will check for updates automatically.")

@auto_update.command()
@click.argument('container_name')
def disable(container_name):
    """Disable automatic updates for a container"""
    from homelab.core.models import init_db, AutoUpdateConfig
    from homelab.config import DATABASE_URL
    
    Session = init_db(DATABASE_URL)
    session = Session()
    
    config = session.query(AutoUpdateConfig)\
        .filter_by(container_name=container_name)\
        .first()
    
    if not config:
        click.echo(f"Auto-update not enabled for {container_name}")
        return
    
    config.enabled = False
    session.commit()
    
    click.echo(f"Disabled auto-update for {container_name}")

@auto_update.command(name='status')
def status_cmd():
    """Show auto-update status for all containers"""
    from homelab.core.models import init_db, AutoUpdateConfig
    from homelab.config import DATABASE_URL
    
    Session = init_db(DATABASE_URL)
    session = Session()
    
    configs = session.query(AutoUpdateConfig).all()
    
    if not configs:
        click.echo("No containers configured for auto-update")
        return
    
    click.echo("\nAuto-Update Status:\n")
    click.echo(f"{'CONTAINER':<20} {'STATUS':<10} {'INTERVAL':<12} {'LAST CHECKED':<20} {'LAST UPDATED':<20}")
    click.echo("-" * 90)
    
    for config in configs:
        status = "enabled" if config.enabled else "disabled"
        interval = f"{config.check_interval_hours}h"
        last_checked = config.last_checked.strftime('%Y-%m-%d %H:%M') if config.last_checked else 'never'
        last_updated = config.last_updated.strftime('%Y-%m-%d %H:%M') if config.last_updated else 'never'
        
        click.echo(f"{config.container_name:<20} {status:<10} {interval:<12} {last_checked:<20} {last_updated:<20}")

@auto_update.command()
@click.argument('container_name')
def test(container_name):
    """Test update process (dry-run with health check)"""
    from homelab.core.models import init_db
    from homelab.core.update_checker import UpdateChecker
    from homelab.core.version_tracker import VersionTracker
    from homelab.config import DATABASE_URL
    from homelab.scheduler.jobs import apply_update_with_monitoring
    
    Session = init_db(DATABASE_URL)
    session = Session()
    
    tracker = VersionTracker(session)
    checker = UpdateChecker()
    
    click.echo(f"Testing auto-update for {container_name}...\n")
    
    # Check for update
    click.echo("Checking for updates...")
    update_info = checker.check_for_update(container_name)
    
    if not update_info:
        click.echo("No update available")
        return
    
    click.echo(f"Update available")
    click.echo(f"  Current: {update_info['current_digest'][:40]}...")
    click.echo(f"  Latest:  {update_info['latest_digest'][:40]}...")
    
    click.echo(f"\nThis is a test - would normally:")
    click.echo(f"  1. Create snapshot")
    click.echo(f"  2. Update container")
    click.echo(f"  3. Monitor health for 10 minutes")
    click.echo(f"  4. Rollback if unhealthy")
    
    if not click.confirm('\nActually perform update?'):
        click.echo("Test cancelled")
        return
    
    # Perform update
    success = apply_update_with_monitoring(
        container_name=container_name,
        tracker=tracker,
        health_check_duration=600,
        auto_rollback=True
    )
    
    if success:
        click.echo("\nUpdate successful!")
    else:
        click.echo("\nUpdate failed (rolled back)")

@cli.command()
def scheduler():
    """Start the background scheduler daemon"""
    import signal
    import sys
    from homelab.scheduler.scheduler import start_scheduler
    from homelab.config import DATABASE_URL
    from logging_config import configure_logging
    
    # Setup logging
    configure_logging()
    logger = logging.getLogger(__name__)

    
    click.echo("Starting Homelab Manager scheduler...")
    
    scheduler = start_scheduler(DATABASE_URL)
    
    click.echo("Scheduler started")
    click.echo("  Checking for updates every 12 hours")
    click.echo("  Press Ctrl+C to stop")
    
    # Handle shutdown
    def signal_handler(sig, frame):
        click.echo("\nShutting down scheduler...")
        scheduler.shutdown()
        click.echo("Scheduler stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass





if __name__ == '__main__':
    cli()