"""Application configuration."""
import os
from pathlib import Path
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    host: str = "0.0.0.0"
    port: int = 8000
    secret_key: str = "dev-secret-key-change-in-production"
    openai_api_key: str = ""  # Set OPENAI_API_KEY in .env for AI extraction
    upload_dir: str = "./uploads"
    output_dir: str = "./outputs"
    storage_type: str = "local"
    database_url: str = "sqlite:///./pdf_extractor.db"
    max_upload_files: int = 500
    max_file_size_mb: int = 50
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        env_nested_delimiter = "__"
    
    @property
    def upload_path(self) -> Path:
        p = Path(os.getenv("UPLOAD_DIR", self.upload_dir))
        p.mkdir(parents=True, exist_ok=True)
        return p
    
    @property
    def output_path(self) -> Path:
        p = Path(os.getenv("OUTPUT_DIR", self.output_dir))
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache()
def get_settings() -> Settings:
    return Settings()
