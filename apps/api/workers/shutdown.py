"""
Shared graceful shutdown utility for CelesteOS background workers.

Usage:
    from workers.shutdown import register_shutdown, is_shutting_down

    register_shutdown()

    while not is_shutting_down():
        # do work
"""

import signal
import logging

_shutdown = False
_logger = logging.getLogger("workers.shutdown")


def _signal_handler(signum, frame):
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global _shutdown
    _logger.info("Received shutdown signal, finishing current batch...")
    _shutdown = True


def register_shutdown():
    """Register SIGINT/SIGTERM handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)


def is_shutting_down() -> bool:
    """Check if a shutdown signal has been received."""
    return _shutdown
