"""
Configuration management for CelesteOS Local Agent.
Handles loading, validation, and persistence of configuration.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class Config(BaseModel):
    """Configuration model with validation."""

    # Yacht identity
    yacht_signature: str = Field(..., min_length=1, description="Unique yacht signature from CelesteOS")
    yacht_name: Optional[str] = Field(None, description="Human-readable yacht name")

    # API settings
    api_endpoint: str = Field(..., description="CelesteOS cloud API endpoint")
    api_timeout: int = Field(300, description="API request timeout in seconds")
    api_verify_ssl: bool = Field(True, description="Verify SSL certificates")

    # NAS settings
    nas_path: str = Field(..., description="Path to NAS mount point")
    nas_type: str = Field("smb", description="NAS type: smb, nfs, or local")
    nas_host: Optional[str] = Field(None, description="NAS hostname or IP")
    nas_share: Optional[str] = Field(None, description="NAS share name")
    nas_username: Optional[str] = Field(None, description="NAS username (password in keychain)")

    # Scanning settings
    scan_interval_minutes: int = Field(15, ge=1, le=1440, description="Full scan interval in minutes")
    deep_scan_interval_hours: int = Field(1, ge=1, le=24, description="Deep scan with hash verification interval")
    watch_enabled: bool = Field(True, description="Enable real-time file watching")

    # Upload settings
    chunk_size_mb: int = Field(64, ge=1, le=512, description="Chunk size in MB")
    max_concurrent_uploads: int = Field(3, ge=1, le=10, description="Maximum concurrent uploads")
    max_retries: int = Field(5, ge=1, le=10, description="Maximum retry attempts per upload")

    # Performance settings
    hasher_workers: int = Field(4, ge=1, le=16, description="Number of parallel hash workers")
    scanner_max_depth: int = Field(100, ge=1, le=1000, description="Maximum folder depth to scan")

    # Storage settings
    temp_dir: str = Field("~/.celesteos/tmp", description="Temporary storage for chunks")
    log_dir: str = Field("~/.celesteos/logs", description="Log file directory")
    db_path: str = Field("~/.celesteos/celesteos.db", description="SQLite database path")

    # Logging settings
    log_level: str = Field("INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR")
    log_rotation_days: int = Field(7, ge=1, le=90, description="Log retention in days")

    # Feature flags
    enabled: bool = Field(True, description="Master enable/disable switch")
    auto_update_enabled: bool = Field(True, description="Enable automatic updates")
    telemetry_enabled: bool = Field(True, description="Enable anonymous telemetry")

    @validator('api_endpoint')
    def validate_api_endpoint(cls, v):
        """Ensure API endpoint is HTTPS."""
        if not v.startswith('http://') and not v.startswith('https://'):
            raise ValueError('API endpoint must start with http:// or https://')
        if not v.startswith('https://'):
            # Warn but allow HTTP for local development
            import warnings
            warnings.warn('Using HTTP instead of HTTPS is insecure!')
        return v.rstrip('/')

    @validator('nas_type')
    def validate_nas_type(cls, v):
        """Validate NAS type."""
        allowed = ['smb', 'nfs', 'local']
        if v.lower() not in allowed:
            raise ValueError(f'NAS type must be one of: {", ".join(allowed)}')
        return v.lower()

    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed:
            raise ValueError(f'Log level must be one of: {", ".join(allowed)}')
        return v.upper()

    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class ConfigManager:
    """Manages configuration file loading and saving."""

    DEFAULT_CONFIG_PATH = Path.home() / ".celesteos" / "config.json"

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config manager.

        Args:
            config_path: Optional custom config path
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: Optional[Config] = None

    def load(self) -> Config:
        """Load configuration from file.

        Returns:
            Config object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                "Run setup wizard or create config manually."
            )

        with open(self.config_path, 'r') as f:
            data = json.load(f)

        self._config = Config(**data)
        return self._config

    def save(self, config: Config) -> None:
        """Save configuration to file.

        Args:
            config: Config object to save
        """
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write config
        with open(self.config_path, 'w') as f:
            json.dump(
                config.dict(exclude_none=True),
                f,
                indent=2,
                sort_keys=True
            )

        # Set restrictive permissions (owner only)
        os.chmod(self.config_path, 0o600)

        self._config = config

    def get(self) -> Config:
        """Get current configuration (load if not cached).

        Returns:
            Config object
        """
        if self._config is None:
            self._config = self.load()
        return self._config

    def update(self, updates: Dict[str, Any]) -> Config:
        """Update configuration fields.

        Args:
            updates: Dictionary of fields to update

        Returns:
            Updated Config object
        """
        config = self.get()
        updated_data = config.dict()
        updated_data.update(updates)

        new_config = Config(**updated_data)
        self.save(new_config)

        return new_config

    def reset(self) -> None:
        """Delete configuration file."""
        if self.config_path.exists():
            self.config_path.unlink()
        self._config = None

    def ensure_directories(self) -> None:
        """Create all required directories."""
        config = self.get()

        # Expand paths
        temp_dir = Path(config.temp_dir).expanduser()
        log_dir = Path(config.log_dir).expanduser()
        db_dir = Path(config.db_path).expanduser().parent

        # Create directories
        for directory in [temp_dir, log_dir, db_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            os.chmod(directory, 0o700)  # Owner only

    @classmethod
    def create_example_config(cls, path: Optional[Path] = None) -> None:
        """Create an example configuration file.

        Args:
            path: Optional path for example config
        """
        example_path = path or (Path.cwd() / "config.example.json")

        example_config = {
            "yacht_signature": "YOUR_YACHT_SIGNATURE_HERE",
            "yacht_name": "MY YACHT",
            "api_endpoint": "https://api.celesteos.io",
            "api_timeout": 300,
            "api_verify_ssl": True,
            "nas_path": "/Volumes/YachtNAS/Engineering",
            "nas_type": "smb",
            "nas_host": "192.168.1.100",
            "nas_share": "Engineering",
            "nas_username": "yacht_user",
            "scan_interval_minutes": 15,
            "deep_scan_interval_hours": 1,
            "watch_enabled": True,
            "chunk_size_mb": 64,
            "max_concurrent_uploads": 3,
            "max_retries": 5,
            "hasher_workers": 4,
            "scanner_max_depth": 100,
            "temp_dir": "~/.celesteos/tmp",
            "log_dir": "~/.celesteos/logs",
            "db_path": "~/.celesteos/celesteos.db",
            "log_level": "INFO",
            "log_rotation_days": 7,
            "enabled": True,
            "auto_update_enabled": True,
            "telemetry_enabled": True
        }

        with open(example_path, 'w') as f:
            json.dump(example_config, f, indent=2, sort_keys=True)

        print(f"Example configuration created at: {example_path}")
        print("Edit this file and save as ~/.celesteos/config.json")
