"""
Configuration management for CelesteOS Cloud API
Loads settings from environment variables
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "CelesteOS Cloud API"
    API_VERSION: str = "v1"
    ENVIRONMENT: str = "development"  # development, staging, production

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://app.celesteos.com"
    ]

    # Storage
    STORAGE_BUCKET_UPLOADS: str = "yacht-uploads"
    STORAGE_BUCKET_DOCUMENTS: str = "yacht-documents"
    MAX_UPLOAD_SIZE_MB: int = 500
    MAX_CHUNK_SIZE_MB: int = 20

    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 100

    # Indexing (n8n workflow webhook)
    # Indexing is triggered via n8n webhook, not a separate service
    INDEXING_WEBHOOK_URL: str = "https://api.celeste7.ai/webhook/v1/ingest/index"

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Initialize settings
settings = Settings()
