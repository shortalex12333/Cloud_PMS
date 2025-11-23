"""
Scheduler for CelesteOS Local Agent.
Manages periodic tasks (scanning, uploading, cleanup).
"""

import time
from datetime import datetime, timedelta
from typing import Callable, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from .logger import get_logger

logger = get_logger(__name__)


class AgentScheduler:
    """Manages scheduled tasks for the agent."""

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = BackgroundScheduler()
        self.is_running = False

    def add_scan_job(
        self,
        scan_func: Callable,
        interval_minutes: int = 15
    ) -> None:
        """Schedule periodic NAS scanning.

        Args:
            scan_func: Function to call for scanning
            interval_minutes: Scan interval in minutes
        """
        self.scheduler.add_job(
            func=scan_func,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id='nas_scan',
            name='NAS Full Scan',
            max_instances=1,
            replace_existing=True
        )

        logger.info(f"Scheduled NAS scan every {interval_minutes} minutes")

    def add_deep_scan_job(
        self,
        deep_scan_func: Callable,
        interval_hours: int = 1
    ) -> None:
        """Schedule periodic deep scan with hash verification.

        Args:
            deep_scan_func: Function to call for deep scanning
            interval_hours: Scan interval in hours
        """
        self.scheduler.add_job(
            func=deep_scan_func,
            trigger=IntervalTrigger(hours=interval_hours),
            id='deep_scan',
            name='Deep Scan with Hash Verification',
            max_instances=1,
            replace_existing=True
        )

        logger.info(f"Scheduled deep scan every {interval_hours} hours")

    def add_upload_job(
        self,
        upload_func: Callable,
        interval_minutes: int = 5
    ) -> None:
        """Schedule periodic upload processing.

        Args:
            upload_func: Function to call for upload processing
            interval_minutes: Processing interval in minutes
        """
        self.scheduler.add_job(
            func=upload_func,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id='upload_processing',
            name='Process Upload Queue',
            max_instances=1,
            replace_existing=True
        )

        logger.info(f"Scheduled upload processing every {interval_minutes} minutes")

    def add_cleanup_job(
        self,
        cleanup_func: Callable,
        hour: int = 3  # 3 AM
    ) -> None:
        """Schedule daily cleanup of old chunks.

        Args:
            cleanup_func: Function to call for cleanup
            hour: Hour of day (0-23) to run cleanup
        """
        self.scheduler.add_job(
            func=cleanup_func,
            trigger=CronTrigger(hour=hour, minute=0),
            id='cleanup',
            name='Daily Cleanup',
            max_instances=1,
            replace_existing=True
        )

        logger.info(f"Scheduled daily cleanup at {hour}:00")

    def add_update_check_job(
        self,
        update_check_func: Callable,
        interval_hours: int = 24
    ) -> None:
        """Schedule periodic update checks.

        Args:
            update_check_func: Function to call for update checking
            interval_hours: Check interval in hours
        """
        self.scheduler.add_job(
            func=update_check_func,
            trigger=IntervalTrigger(hours=interval_hours),
            id='update_check',
            name='Check for Updates',
            max_instances=1,
            replace_existing=True
        )

        logger.info(f"Scheduled update check every {interval_hours} hours")

    def start(self) -> None:
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        logger.info("Starting scheduler")
        self.scheduler.start()
        self.is_running = True

        # Log scheduled jobs
        jobs = self.scheduler.get_jobs()
        logger.info(f"Scheduler started with {len(jobs)} jobs")
        for job in jobs:
            logger.debug(f"  - {job.name} (next run: {job.next_run_time})")

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self.is_running:
            return

        logger.info("Stopping scheduler")
        self.scheduler.shutdown(wait=True)
        self.is_running = False

        logger.info("Scheduler stopped")

    def pause(self) -> None:
        """Pause all scheduled jobs."""
        logger.info("Pausing scheduler")
        self.scheduler.pause()

    def resume(self) -> None:
        """Resume all scheduled jobs."""
        logger.info("Resuming scheduler")
        self.scheduler.resume()

    def get_jobs(self) -> list:
        """Get list of scheduled jobs.

        Returns:
            List of job objects
        """
        return self.scheduler.get_jobs()

    def remove_job(self, job_id: str) -> None:
        """Remove a scheduled job.

        Args:
            job_id: Job ID to remove
        """
        self.scheduler.remove_job(job_id)
        logger.info(f"Removed job: {job_id}")
