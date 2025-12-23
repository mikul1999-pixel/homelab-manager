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
    click.echo(f"{'ID':<5} {'TIMESTAMP':<20} {'VERSION':<40} {'ACTION':<10}")
    click.echo("-" * 85)
    
    for h in history:
        click.echo(f"{h.id:<5} {str(h.timestamp):<20} {h.image_version:<40} {h.action:<10}")

@cli.command()
@click.argument('container_name')
@click.argument('snapshot_id', type=int)
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
def rollback(container_name, snapshot_id, force):
    """Rollback container to a previous snapshot"""
    from homelab.core.models import init_db
    from homelab.core.version_tracker import VersionTracker
    from homelab.config import DATABASE_URL
    
    Session = init_db(DATABASE_URL)
    session = Session()
    tracker = VersionTracker(session)
    
    # Get snapshot details
    snapshot = tracker.get_snapshot_by_id(snapshot_id)
    if not snapshot:
        click.echo(f"✗ Snapshot {snapshot_id} not found", err=True)
        return 1
    
    # Get current version
    current_version = tracker.get_current_version(container_name)
    
    # Show rollback info
    click.echo(f"\nRollback {container_name} to snapshot #{snapshot_id}:")
    click.echo(f"  Current version:  {current_version or 'unknown'}")
    click.echo(f"  Target version:   {snapshot.image_version}")
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
        click.echo(f"\nSuccessfully rolled back to {snapshot.image_version}")
        click.echo(f"Rollback recorded (ID: {result.id})")
        
        click.echo(f"\nℹ  Note: This was a direct container rollback.")
        click.echo(f"   Your docker-compose files were not modified.")
        
    except Exception as e:
        click.echo(f"\nRollback failed: {e}", err=True)
        raise

if __name__ == '__main__':
    cli()