from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "RankCare API"
    ENV: str = "development"
    PORT: int = 4000

    DATABASE_URL: str

    REDIS_URL: Optional[str] = None
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    JWT_ACCESS_SECRET: str
    JWT_ACCESS_EXPIRES_IN_DAYS: int = 1

    FRONTEND_URL: Optional[str] = None
    SERP_API_KEY: Optional[str] = None

    RESEND_API_KEY: Optional[str] = None
    MAIL_FROM: Optional[str] = None
    EMAIL_VERIFY_EXPIRE_HOURS: int = 24
    GOOGLE_CLIENT_ID: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
