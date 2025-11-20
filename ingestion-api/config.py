"""
CelesteOS Ingestion API Configuration
"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""

    # Supabase
    supabase_url: str
    supabase_service_role_key: str

    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False

    # Storage
    upload_temp_dir: str = "/tmp/celesteos-uploads"
    max_file_size: int = 5368709120  # 5GB
    max_chunk_size: int = 33554432  # 32MB

    # Queue
    n8n_webhook_url: str = "http://localhost:5678/webhook/indexing"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Ensure upload directory exists
Path(settings.upload_temp_dir).mkdir(parents=True, exist_ok=True)
