import click
from homelab.core.docker_manager import DockerManager

@click.group()
def cli():
    """Homelab Manager - Docker container management tool"""
    pass

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
    from homelab.core.compose_manager import ComposeManager
    from homelab.config import DATABASE_URL
    from pathlib import Path
    
    Session = init_db(DATABASE_URL)
    session = Session()
    tracker = VersionTracker(session)
    compose_mgr = ComposeManager()
    
    # Get snapshot details
    snapshot = tracker.get_snapshot_by_id(snapshot_id)
    if not snapshot:
        click.echo(f"Snapshot {snapshot_id} not found", err=True)
        return 1
    
    # Get current version
    current_version = tracker.get_current_version(container_name)
    
    # Check if compose sync is enabled
    compose_config = tracker.get_compose_config(container_name)
    
    # Check if using floating tag
    uses_floating_tag = tracker.is_floating_tag(snapshot.image_version)
    
    # Show rollback info
    click.echo(f"\nRollback {container_name} to snapshot #{snapshot_id}:")
    click.echo(f"  Current version:  {current_version or 'unknown'}")
    click.echo(f"  Target version:   {snapshot.image_version}")
    
    if snapshot.image_digest:
        digest_short = snapshot.image_digest.split(':')[-1][:16] if ':' in snapshot.image_digest else snapshot.image_digest[:16]
        click.echo(f"  Target digest:    {digest_short}...")
    
    click.echo(f"  Snapshot date:    {snapshot.timestamp}")
    click.echo(f"  Method:           Direct Docker API")
    
    if compose_config:
        click.echo(f"  Compose sync:     enabled")
        if uses_floating_tag:
            click.echo(f"Floating tag:   {compose_mgr.extract_version_from_image(snapshot.image_version)}")
    else:
        click.echo(f"  Compose sync:     disabled")
    
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
        if snapshot.image_digest:
            digest_short = snapshot.image_digest.split(':')[-1][:16] if ':' in snapshot.image_digest else snapshot.image_digest[:16]
            click.echo(f"\nRolled back to {snapshot.image_version}")
            click.echo(f"Using digest: {digest_short}... (exact version)")
        else:
            click.echo(f"\nRolled back to {snapshot.image_version}")
        
        click.echo(f"Rollback recorded (ID: {result['rollback_record'].id})")
        
        # Handle compose sync output
        if result['compose_synced']:
            compose_config = result['compose_config']
            env_path = Path(result['env_path'])
            
            # Get relative path from compose directory
            try:
                relative_env_path = env_path.relative_to(compose_config.compose_directory)
            except ValueError:
                relative_env_path = env_path
            
            click.echo(f"\nUpdated {env_path}")
            
            # Special warning for floating tags. TODO: docker compose using digest?
            if result['uses_floating_tag']:
                tag = compose_mgr.extract_version_from_image(snapshot.image_version)
                click.echo(f"\nIMPORTANT: This container uses a floating tag (:{tag})")
                click.echo(f"   └─ The container was rolled back using the exact digest from the snapshot")
                click.echo(f"   └─ However, your .env.manager still contains: {tag}")
            else:
                # Normal versioned tag
                click.echo(f"\nTo apply the rollback permanently:\n")
                click.echo(f"   cd {compose_config.compose_directory}")
                
                if compose_config.compose_files:
                    compose_cmd = f"docker-compose --env-file {relative_env_path}"
                    for f in compose_config.compose_files:
                        compose_cmd += f" -f {f}"
                    compose_cmd += " up -d"
                    click.echo(f"   {compose_cmd}")
                else:
                    click.echo(f"   docker-compose --env-file {relative_env_path} up -d")
            
        else:
            click.echo(f"\nNote: This was a direct container rollback.")
            click.echo(f"   Your docker-compose files were not modified.")
            if not compose_config:
                click.echo(f"   To enable compose sync, run: homelab enable-compose {container_name}")
        
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
    click.echo("container rollbacks. No compose commands will be run automatically.\n")
    
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

    # Check if using floating tag
    current_version = compose_mgr.extract_version_from_image(details['image'])
    uses_floating_tag = tracker.is_floating_tag(details['image'])

    if uses_floating_tag:
        click.echo(f"\nIMPORTANT: This container uses a floating tag (:{current_version})")
        click.echo(f"   └─ The container will be rolled back using the exact digest from the snapshot")
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

        if choice == 2:
            env_path = ".env.manager"
        elif choice == 1:
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
    current_version = compose_mgr.extract_version_from_image(details['image'])
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
    if compose_service and compose_files:
        service_files = [f for f in compose_files if f != 'docker-compose.yml']
        target_file = service_files[0] if service_files else compose_files[0]
    else:
        target_file = "your compose file"
    
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
    click.echo("Compose sync enabled! Future rollbacks will automatically")
    click.echo("update .env.manager. You can run docker-compose whenever")
    click.echo("you want to apply the changes.")
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
    current_version = tracker.get_current_version(container_name)
    if current_version:
        container_ver = compose_mgr.extract_version_from_image(current_version)
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

if __name__ == '__main__':
    cli()