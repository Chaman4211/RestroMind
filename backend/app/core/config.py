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
    rtsp_encryption_key: str | None = None
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    owner_setup_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
