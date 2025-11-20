"""
Structured logging for CelesteOS Local Agent.
Provides JSON and console logging with rotation.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pythonjsonlogger import jsonlogger
from typing import Optional


class CelesteOSFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to log records."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = self.formatTime(record, self.datefmt)

        # Add level
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname

        # Add component
        log_record['component'] = 'celesteos-agent'


def setup_logger(
    name: str,
    log_dir: Optional[Path] = None,
    log_level: str = "INFO",
    console: bool = True,
    json_logs: bool = True
) -> logging.Logger:
    """Setup logger with file and console handlers.

    Args:
        name: Logger name
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        console: Enable console logging
        json_logs: Use JSON format for file logs

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers = []

    # Console handler (human-readable)
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))

        console_format = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

    # File handler
    if log_dir:
        log_dir = Path(log_dir).expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / "celesteos-agent.log"

        # Timed rotating file handler (daily rotation, 7 day retention)
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))

        if json_logs:
            # JSON format for file logs (easier to parse)
            json_format = CelesteOSFormatter(
                fmt='%(timestamp)s %(level)s %(name)s %(message)s'
            )
            file_handler.setFormatter(json_format)
        else:
            # Standard format
            file_format = logging.Formatter(
                fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_format)

        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "celesteos_agent") -> logging.Logger:
    """Get or create logger for a module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Global logger instance
_global_logger: Optional[logging.Logger] = None


def init_global_logger(
    log_dir: Optional[Path] = None,
    log_level: str = "INFO",
    console: bool = True
) -> logging.Logger:
    """Initialize global logger.

    Args:
        log_dir: Directory for log files
        log_level: Logging level
        console: Enable console logging

    Returns:
        Global logger instance
    """
    global _global_logger

    if _global_logger is None:
        _global_logger = setup_logger(
            name="celesteos_agent",
            log_dir=log_dir,
            log_level=log_level,
            console=console,
            json_logs=True
        )

    return _global_logger


def get_global_logger() -> logging.Logger:
    """Get global logger (initialize if needed).

    Returns:
        Global logger instance
    """
    global _global_logger

    if _global_logger is None:
        _global_logger = init_global_logger()

    return _global_logger
