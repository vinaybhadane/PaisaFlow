"""Application configuration module."""

from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """PaisaFlow application settings."""

    # Application & Environment
    APP_ENV: str = "development"
    PROJECT_NAME: str = "PaisaFlow API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Database & Storage
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/paisaflow"
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Configuration (Explanations & Natural Language Assistance)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"

    # Supabase Cloud Database & Storage
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    # Security & CORS
    SESSION_SECRET: str = "dev-insecure-secret-key-change-in-production"
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Localization & Financial Standards
    DEFAULT_CURRENCY: str = "INR"
    DEFAULT_LOCALE: str = "en-IN"
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"
    SUPPORTED_UPLOAD_FORMATS: List[str] = ["csv", "pdf"]
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

