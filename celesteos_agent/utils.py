"""
Utility functions for CelesteOS Local Agent.
"""

import os
import sys
import signal
from pathlib import Path
from typing import Optional
from .logger import get_logger

logger = get_logger(__name__)


def format_bytes(bytes_size: int) -> str:
    """Format bytes as human-readable string.

    Args:
        bytes_size: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


def format_duration(seconds: int) -> str:
    """Format seconds as human-readable duration.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "2h 15m")
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"


def ensure_single_instance(pid_file: str = "~/.celesteos/celesteos-agent.pid") -> bool:
    """Ensure only one instance of agent is running.

    Args:
        pid_file: Path to PID file

    Returns:
        True if this is the only instance
    """
    pid_file_path = Path(pid_file).expanduser()

    if pid_file_path.exists():
        # Check if process is still running
        try:
            with open(pid_file_path, 'r') as f:
                old_pid = int(f.read().strip())

            # Check if process exists
            try:
                os.kill(old_pid, 0)
                logger.error(f"Another instance is already running (PID {old_pid})")
                return False
            except OSError:
                # Process doesn't exist, remove stale PID file
                logger.warning(f"Removing stale PID file for process {old_pid}")
                pid_file_path.unlink()
        except Exception as e:
            logger.warning(f"Error checking PID file: {e}")
            pid_file_path.unlink()

    # Write our PID
    pid_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(pid_file_path, 'w') as f:
        f.write(str(os.getpid()))

    logger.info(f"PID file created: {pid_file_path}")

    return True


def remove_pid_file(pid_file: str = "~/.celesteos/celesteos-agent.pid") -> None:
    """Remove PID file.

    Args:
        pid_file: Path to PID file
    """
    pid_file_path = Path(pid_file).expanduser()

    if pid_file_path.exists():
        pid_file_path.unlink()
        logger.info("PID file removed")


def setup_signal_handlers(shutdown_callback) -> None:
    """Setup signal handlers for graceful shutdown.

    Args:
        shutdown_callback: Function to call on shutdown signals
    """
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        shutdown_callback()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.debug("Signal handlers registered")


def test_nas_connectivity(nas_path: str) -> bool:
    """Test NAS connectivity.

    Args:
        nas_path: Path to NAS mount

    Returns:
        True if accessible
    """
    nas_path_obj = Path(nas_path).expanduser()

    try:
        if not nas_path_obj.exists():
            logger.error(f"NAS path does not exist: {nas_path}")
            return False

        if not nas_path_obj.is_dir():
            logger.error(f"NAS path is not a directory: {nas_path}")
            return False

        # Try to list directory
        list(nas_path_obj.iterdir())

        logger.info(f"NAS connectivity test passed: {nas_path}")
        return True

    except PermissionError:
        logger.error(f"Permission denied accessing NAS: {nas_path}")
        return False

    except Exception as e:
        logger.error(f"NAS connectivity test failed: {e}")
        return False


def validate_yacht_signature(yacht_signature: str) -> bool:
    """Validate yacht signature format.

    Args:
        yacht_signature: Yacht signature

    Returns:
        True if valid format
    """
    if not yacht_signature:
        return False

    if len(yacht_signature) < 6:
        return False

    # Could add more validation (e.g., regex pattern)

    return True
