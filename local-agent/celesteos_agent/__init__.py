"""
CelesteOS Local Agent
Version: 1.0

A lightweight macOS daemon for ingesting NAS documents into CelesteOS cloud.
"""

__version__ = "1.0.0"
__author__ = "CelesteOS Engineering"

from .config import Config
from .database import Database
from .logger import get_logger

__all__ = ["Config", "Database", "get_logger", "__version__"]
