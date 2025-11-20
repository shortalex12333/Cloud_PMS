#!/usr/bin/env python3
"""
CelesteOS Local Agent Daemon
Main background process for NAS document ingestion.
"""

import sys
import time
from pathlib import Path

from celesteos_agent import get_logger
from celesteos_agent.config import ConfigManager
from celesteos_agent.database import Database
from celesteos_agent.keychain import KeychainManager
from celesteos_agent.scanner import FileScanner, NASWatcher
from celesteos_agent.hasher import FileHasher
from celesteos_agent.uploader import UploadManager
from celesteos_agent.api_client import RetryableAPIClient
from celesteos_agent.scheduler import AgentScheduler
from celesteos_agent.utils import (
    ensure_single_instance,
    remove_pid_file,
    setup_signal_handlers,
    test_nas_connectivity
)

logger = get_logger(__name__)


class CelesteOSDaemon:
    """Main daemon process for CelesteOS Local Agent."""

    def __init__(self):
        """Initialize daemon."""
        self.config_manager = ConfigManager()
        self.config = None
        self.db = None
        self.keychain = None
        self.scanner = None
        self.watcher = None
        self.uploader = None
        self.scheduler = None
        self.running = False

    def initialize(self) -> bool:
        """Initialize all components.

        Returns:
            True if successful
        """
        try:
            # Load configuration
            logger.info("Loading configuration")
            self.config = self.config_manager.load()

            # Initialize logger with config
            from celesteos_agent.logger import init_global_logger
            init_global_logger(
                log_dir=Path(self.config.log_dir).expanduser(),
                log_level=self.config.log_level,
                console=True
            )

            logger.info("=" * 60)
            logger.info("CelesteOS Local Agent Daemon Starting")
            logger.info("=" * 60)

            # Ensure directories exist
            logger.info("Creating required directories")
            self.config_manager.ensure_directories()

            # Initialize database
            logger.info("Initializing database")
            self.db = Database(self.config.db_path)

            # Initialize keychain
            logger.info("Initializing keychain")
            self.keychain = KeychainManager()

            # Test NAS connectivity
            logger.info("Testing NAS connectivity")
            if not test_nas_connectivity(self.config.nas_path):
                logger.error("NAS connectivity test failed")
                return False

            # Load yacht identity from database
            yacht_identity = self.db.get_yacht_identity()
            if not yacht_identity:
                logger.error("Yacht identity not configured. Run setup first.")
                return False

            logger.info(f"Yacht: {yacht_identity.get('yacht_name', 'Unknown')}")

            # Retrieve Supabase service role key from keychain
            logger.info("Retrieving Supabase credentials from Keychain")
            supabase_service_key = self.keychain.get_credential('supabase_service_role_key')

            if not supabase_service_key:
                logger.warning("Supabase service role key not found in Keychain")
                logger.warning("Agent will attempt to connect without Supabase authentication")
                logger.warning("This may cause authentication errors. Run setup to configure.")

            # Initialize API client
            logger.info("Initializing API client")
            api_client = RetryableAPIClient(
                api_endpoint=self.config.api_endpoint,
                yacht_signature=self.config.yacht_signature,
                supabase_service_key=supabase_service_key,
                timeout=self.config.api_timeout,
                verify_ssl=self.config.api_verify_ssl,
                max_retries=self.config.max_retries
            )

            # Test API connectivity
            logger.info("Testing API connectivity")
            if not api_client.ping():
                logger.warning("API ping failed - uploads may fail")
                logger.warning("Verify Supabase Edge Functions are deployed")

            # Initialize scanner
            logger.info("Initializing file scanner")
            ignore_patterns = self.db.get_ignore_patterns()
            self.scanner = FileScanner(
                db=self.db,
                nas_path=self.config.nas_path,
                ignore_patterns=ignore_patterns
            )

            # Initialize file watcher (if enabled)
            if self.config.watch_enabled:
                logger.info("Initializing file watcher")
                self.watcher = NASWatcher(
                    scanner=self.scanner,
                    db=self.db
                )

            # Initialize upload manager
            logger.info("Initializing upload manager")
            self.uploader = UploadManager(
                db=self.db,
                api_client=api_client,
                chunk_size_mb=self.config.chunk_size_mb,
                temp_dir=self.config.temp_dir,
                max_concurrent_uploads=self.config.max_concurrent_uploads
            )

            # Initialize scheduler
            logger.info("Initializing scheduler")
            self.scheduler = AgentScheduler()

            # Schedule tasks
            self.scheduler.add_scan_job(
                scan_func=self.run_scan,
                interval_minutes=self.config.scan_interval_minutes
            )

            self.scheduler.add_deep_scan_job(
                deep_scan_func=self.run_deep_scan,
                interval_hours=self.config.deep_scan_interval_hours
            )

            self.scheduler.add_upload_job(
                upload_func=self.process_uploads,
                interval_minutes=5
            )

            self.scheduler.add_cleanup_job(
                cleanup_func=self.run_cleanup,
                hour=3  # 3 AM
            )

            if self.config.auto_update_enabled:
                self.scheduler.add_update_check_job(
                    update_check_func=self.check_updates,
                    interval_hours=24
                )

            logger.info("Initialization complete")

            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            return False

    def run_scan(self) -> None:
        """Run full NAS scan."""
        try:
            logger.info("Starting scheduled NAS scan")
            stats = self.scanner.scan(
                full_scan=True,
                max_depth=self.config.scanner_max_depth
            )
            logger.info(f"Scan complete: {stats}")

            # Queue pending files for upload
            self.queue_pending_uploads()

        except Exception as e:
            logger.error(f"Scan failed: {e}", exc_info=True)

    def run_deep_scan(self) -> None:
        """Run deep scan with hash verification."""
        try:
            logger.info("Starting deep scan with hash verification")
            # Implement deep scan logic (re-hash all files to detect corruption)
            pass

        except Exception as e:
            logger.error(f"Deep scan failed: {e}", exc_info=True)

    def queue_pending_uploads(self) -> None:
        """Queue pending files for upload."""
        try:
            pending_files = self.db.get_pending_files(limit=100)

            logger.info(f"Queueing {len(pending_files)} files for upload")

            for file_record in pending_files:
                file_path = Path(self.config.nas_path) / file_record['file_path']

                upload_queue_id = self.uploader.prepare_file_for_upload(
                    file_path=str(file_path),
                    file_id=file_record['id']
                )

                if upload_queue_id:
                    logger.debug(f"Queued: {file_record['filename']}")

        except Exception as e:
            logger.error(f"Failed to queue uploads: {e}", exc_info=True)

    def process_uploads(self) -> None:
        """Process upload queue."""
        try:
            logger.debug("Processing upload queue")
            stats = self.uploader.process_upload_queue()

            if stats['processed'] > 0:
                logger.info(f"Upload processing complete: {stats}")

        except Exception as e:
            logger.error(f"Upload processing failed: {e}", exc_info=True)

    def run_cleanup(self) -> None:
        """Run daily cleanup tasks."""
        try:
            logger.info("Running daily cleanup")

            # Cleanup old chunks
            deleted = self.uploader.chunker.cleanup_old_chunks(max_age_hours=24)
            logger.info(f"Cleaned up {deleted} old chunks")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}", exc_info=True)

    def check_updates(self) -> None:
        """Check for agent updates."""
        try:
            logger.info("Checking for updates")
            # Implement update check logic
            pass

        except Exception as e:
            logger.error(f"Update check failed: {e}", exc_info=True)

    def start(self) -> None:
        """Start the daemon."""
        # Ensure single instance
        if not ensure_single_instance():
            logger.error("Another instance is already running")
            sys.exit(1)

        # Initialize components
        if not self.initialize():
            logger.error("Initialization failed")
            remove_pid_file()
            sys.exit(1)

        # Setup signal handlers
        setup_signal_handlers(self.shutdown)

        # Update daemon status
        self.db.update_sync_state({
            'daemon_status': 'running',
            'daemon_started_at': int(time.time())
        })

        self.db.log_activity('daemon_started', 'Daemon started successfully')

        # Start file watcher
        if self.watcher:
            self.watcher.start()

        # Start scheduler
        self.scheduler.start()

        # Mark as running
        self.running = True

        logger.info("=" * 60)
        logger.info("CelesteOS Local Agent Daemon Running")
        logger.info("=" * 60)

        # Run initial scan
        logger.info("Running initial scan")
        self.run_scan()

        # Main loop
        try:
            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")

        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Shutdown the daemon gracefully."""
        if not self.running:
            return

        logger.info("=" * 60)
        logger.info("Shutting down CelesteOS Local Agent")
        logger.info("=" * 60)

        self.running = False

        # Stop scheduler
        if self.scheduler:
            self.scheduler.stop()

        # Stop file watcher
        if self.watcher:
            self.watcher.stop()

        # Shutdown uploader
        if self.uploader:
            self.uploader.shutdown()

        # Update daemon status
        if self.db:
            self.db.update_sync_state({'daemon_status': 'stopped'})
            self.db.log_activity('daemon_stopped', 'Daemon stopped')

        # Remove PID file
        remove_pid_file()

        logger.info("Shutdown complete")


def main():
    """Main entry point."""
    daemon = CelesteOSDaemon()
    daemon.start()


if __name__ == "__main__":
    main()
