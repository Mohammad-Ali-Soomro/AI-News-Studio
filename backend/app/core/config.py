from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from backend/.env and environment variables."""

    PROJECT_NAME: str = "AI News Studio"
    API_V1_STR: str = "/api/v1"

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = ""

    MAX_ARTICLES_PER_FEED: int = 5
    MEDIA_STORAGE_DIR: str = str(BACKEND_DIR / "media")

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
