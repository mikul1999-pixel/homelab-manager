import logging
import time
from datetime import datetime
from homelab.core.models import init_db, AutoUpdateConfig
from homelab.core.update_manager import UpdateManager
from homelab.core.update_checker import UpdateChecker
from homelab.core.version_tracker import VersionTracker
from homelab.core.health_checker import HealthChecker

logger = logging.getLogger(__name__)

def check_updates_job(database_url: str):
    """Main scheduled job - checks for updates and applies them"""
    logger.info("=== Starting scheduled update check ===")
    
    Session = init_db(database_url)
    session = Session()
    checker = UpdateChecker(session)
    tracker = VersionTracker(session)
    
    # Get all containers with auto-update enabled
    auto_update_containers = session.query(AutoUpdateConfig)\
        .filter_by(enabled=True)\
        .all()
    
    if not auto_update_containers:
        logger.info("No containers configured for auto-update")
        return

    logger.info(f"Checking {len(auto_update_containers)} containers for updates")
    
    for config in auto_update_containers:
        try:
            logger.info(f"Checking {config.container_name}...")
            
            # Check if update available
            update_info = checker.check_for_update(config.container_name)
            
            if not update_info:
                logger.info(f"  No update available for {config.container_name}")
                config.last_checked = datetime.utcnow()
                session.commit()
                continue
            
            logger.info(f"  Update available for {config.container_name}")
            logger.info(f"    Current: {update_info['current_digest'][:20]}...")
            logger.info(f"    Latest:  {update_info['latest_digest'][:20]}...")
            
            # Apply update with health monitoring
            if not config.check_only: 
                success = apply_update_with_monitoring(
                    container_name=config.container_name,
                    tracker=tracker,
                    health_check_duration=config.health_check_duration,
                    auto_rollback=config.auto_rollback
                )
            
            # Update config
            config.last_checked = datetime.utcnow()
            if success:
                config.last_updated = datetime.utcnow()
            session.commit()
            
        except Exception as e:
            logger.error(f"Error processing {config.container_name}: {e}", exc_info=True)
    
    logger.info("=== Scheduled update check complete ===")

def apply_update_with_monitoring(
    container_name: str,
    tracker: VersionTracker,
    updater: UpdateManager,
    health_check_duration: int = 600,
    auto_rollback: bool = True
) -> bool:
    """Apply update with health monitoring and optional auto-rollback"""
    health_checker = HealthChecker()
    
    logger.info(f"Starting update process for {container_name}")
    
    # Step 1: Perform update
    logger.info(f"  Attempting update...")

    update_result = updater.update_container(container_name)
    pre_snapshot_id = update_result.get("before_snapshot")

    if not update_result.get("updated"):
        logger.error(f" Update failed: {update_result.get('reason')}")
        if update_result.get('error') is not None:
            logger.error(f"Error: {update_result.get('error')}")
            return False

    # Success summary
    logger.info(f"\nSuccessfully updated {container_name}")
    logger.info(f"\nSnapshots created:")
    logger.info(f"  • Before update: ID {update_result['before_snapshot']}")
    logger.info(f"  • After update:  ID {update_result['after_snapshot']}")
    logger.info(f"\n")
        
    # Step 2: Health monitoring
    logger.info(f"  Monitoring health for {health_check_duration} seconds...")
    
    healthy = monitor_health(
        container_name=container_name,
        health_checker=health_checker,
        duration=health_check_duration
    )
    
    if healthy:
        logger.info(f"  Health check passed - update successful")
        return True
    else:
        logger.error(f"  Health check failed")
        
        if auto_rollback:
            logger.info(f"  Auto-rollback enabled - rolling back...")
            try:
                tracker.rollback_container(container_name, pre_snapshot_id)
                logger.info(f"  Rolled back to snapshot {pre_snapshot_id}")
            except Exception as e:
                logger.error(f"  Rollback failed: {e}")
        else:
            logger.warning(f"  Auto-rollback disabled - container left in updated state")
        
        return False

def monitor_health(
    container_name: str,
    health_checker: HealthChecker,
    duration: int = 600,
    check_interval: int = 30
) -> bool:
    """Monitor container health for a duration"""
    start_time = time.time()
    checks_performed = 0
    failures = 0
    max_consecutive_failures = 3
    
    logger.info(f"    Starting health monitoring (duration: {duration}s, interval: {check_interval}s)")
    
    # Grace period for startup
    logger.info(f"    Waiting 60s for container startup...")
    time.sleep(60)
    
    while time.time() - start_time < duration:
        checks_performed += 1
        elapsed = int(time.time() - start_time)
        
        try:
            health = health_checker.check_container_health(container_name)
            
            if health['overall_healthy']:
                logger.info(f"    [{elapsed}s] Health check #{checks_performed}: healthy")
                failures = 0  # Reset failure counter
            else:
                failures += 1
                logger.warning(f"    [{elapsed}s] Health check #{checks_performed}: unhealthy ({failures}/{max_consecutive_failures})")
                logger.warning(f"      Details: {health}")
                
                if failures >= max_consecutive_failures:
                    logger.error(f"    {max_consecutive_failures} consecutive failures - marking as unhealthy")
                    return False
        
        except Exception as e:
            failures += 1
            logger.error(f"    [{elapsed}s] Health check error: {e}")
            
            if failures >= max_consecutive_failures:
                return False
        
        # Wait before next check
        time.sleep(check_interval)
    
    # Final check
    logger.info(f"    Performing final health check...")
    try:
        final_health = health_checker.check_container_health(container_name)
        if final_health['overall_healthy']:
            logger.info(f"    Final check passed - container is healthy")
            return True
        else:
            logger.error(f"    Final check failed: {final_health}")
            return False
    except Exception as e:
        logger.error(f"    Final check error: {e}")
        return False