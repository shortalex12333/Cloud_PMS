"""
CelesteOS Search Engine Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # OpenAI
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "info"

    # Security
    jwt_secret: str
    jwt_algorithm: str = "HS256"

    # Search
    default_top_k: int = 15
    graph_max_depth: int = 3
    chunk_overlap_percentage: float = 0.15

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
