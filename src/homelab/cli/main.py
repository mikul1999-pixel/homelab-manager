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
    import click
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
    
    Session = init_db()
    session = Session()
    tracker = VersionTracker(session)
    
    snap = tracker.create_snapshot(container_name)
    click.echo(f"Snapshot created for {container_name} at {snap.timestamp}")

@cli.command()
@click.argument('container_name')
def history(container_name):
    """Show version history for a container"""
    from homelab.core.models import init_db
    from homelab.core.version_tracker import VersionTracker
    
    Session = init_db()
    session = Session()
    tracker = VersionTracker(session)
    
    history = tracker.get_history(container_name)
    
    click.echo(f"\nVersion History for {container_name}:")
    for h in history:
        click.echo(f"  {h.timestamp} - {h.image_version} ({h.action})")

if __name__ == '__main__':
    cli()