import secrets
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

# Define Free Plan Limits
FREE_PLAN_LIMITS = {
    "projects": 1,
    "keywords": 25,
    "competitors": 3,
    "reports_per_month": 2
}

GST_RATE = 0.18

class Settings(BaseSettings):
    # App Basics
    APP_NAME: str = "RankCare API"
    ENV: str = "development"
    PORT: int = 4000
    FRONTEND_URL: str = "http://localhost:5173"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ACCESS_SECRET: str = "dev-secret-key-change-in-production"
    JWT_ACCESS_EXPIRES_IN_DAYS: int = 1
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    
    # Database
    DATABASE_URL: Optional[str] = None
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "rankcare"

    #DataForSEO
    DATAFORSEO_LOGIN: Optional[str] = None
    DATAFORSEO_PASSWORD: Optional[str] = None
    
    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    
    @computed_field
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    # Email
    RESEND_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "noreply@rankcare.com"
    EMAIL_VERIFY_EXPIRE_HOURS: int = 24
    
    # Razorpay
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    
    # SERP / DataForSEO
    SERP_API_LOGIN: Optional[str] = None
    SERP_API_KEY: Optional[str] = None
    
    # Trial
    TRIAL_DAYS: int = 10

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()

def get_settings() -> Settings:
    return settings