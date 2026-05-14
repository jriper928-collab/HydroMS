"""Application configuration via pydantic-settings, loaded from .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./agrovibe.db"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Media directories
    MEDIA_RAW_DIR: Path = Path("./media/raw")
    MEDIA_PROCESSED_DIR: Path = Path("./media/processed")

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Meta / Instagram
    META_ACCESS_TOKEN: str = ""
    META_INSTAGRAM_ID: str = ""
    META_API_VERSION: str = "v22.0"
    META_BASE_URL: str = "https://graph.facebook.com"

    # Google OAuth2
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # OpenRouter (vision API for metadata generation)
    OPENROUTER_API_KEY: str = ""

    # Public base URL (used to construct video URLs for Instagram)
    BASE_URL: str = "https://hydroms-production.up.railway.app"


settings = Settings()
