from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "RestroMind API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:5173"

    postgres_db: str = "restromind"
    postgres_user: str = "restromind_user"
    postgres_password: str
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
