"""
Configuration for CelesteOS Cloud Ingestion API
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    DEBUG: bool = False

    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str  # Service role key for backend operations
    SUPABASE_JWT_SECRET: str
    SUPABASE_STORAGE_BUCKET: str = "celesteos-documents"

    # Storage Configuration
    TEMP_UPLOAD_DIR: str = "/var/celesteos/uploads"
    MAX_CHUNK_SIZE: int = 67108864  # 64MB in bytes
    UPLOAD_TIMEOUT_HOURS: int = 6

    # Security
    ALLOWED_FILE_EXTENSIONS: list[str] = [
        ".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".msg", ".eml",
        ".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif"
    ]
    MAX_FILE_SIZE: int = 5368709120  # 5GB

    # Rate Limiting
    RATE_LIMIT_PER_YACHT_MINUTE: int = 60
    RATE_LIMIT_PER_YACHT_HOUR: int = 1000

    # n8n Configuration
    N8N_WEBHOOK_URL: str
    N8N_WEBHOOK_SECRET: Optional[str] = None

    # Retry Configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
