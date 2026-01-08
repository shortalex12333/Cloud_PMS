"""
CelesteOS Local Agent
Version: 1.1

A lightweight macOS daemon for ingesting NAS documents into CelesteOS cloud.
Supports resumable uploads, file change detection, and telemetry logging.
"""

__version__ = "1.1.0"
__author__ = "CelesteOS Engineering"

from .config import Config
from .database import Database
from .logger import get_logger
from .scanner import FileScanner, NASWatcher
from .change_detector import ChangeDetector, ChangeType, FileChange
from .telemetry import TelemetryCollector, TelemetryEvent
from .uploader import FileUploader
from .hasher import FileHasher
from .chunker import FileChunker

__all__ = [
    "Config",
    "Database",
    "get_logger",
    "FileScanner",
    "NASWatcher",
    "ChangeDetector",
    "ChangeType",
    "FileChange",
    "TelemetryCollector",
    "TelemetryEvent",
    "FileUploader",
    "FileHasher",
    "FileChunker",
    "__version__"
]
