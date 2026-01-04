from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

def create_scheduler(database_url: str):
    """Create and configure APScheduler"""
    
    jobstores = {
        'default': SQLAlchemyJobStore(url=database_url)
    }
    
    executors = {
        'default': ThreadPoolExecutor(max_workers=3)
    }
    
    job_defaults = {
        'coalesce': True,   # Combine multiple missed runs into one
        'max_instances': 1  # Job concurrency
    }
    
    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults
    )
    
    return scheduler

def start_scheduler(database_url: str):
    """Start the background scheduler"""
    scheduler = create_scheduler(database_url)
    from homelab.scheduler.jobs import check_updates_job
    
    # Run every x hours
    scheduler.add_job(
        check_updates_job,
        'interval',
        hours=12,  
        id='check_updates',
        replace_existing=True,
        args=[database_url]
    )
    
    scheduler.start()
    logger.info("Scheduler started - checking for updates every 12 hours")
    
    return scheduler