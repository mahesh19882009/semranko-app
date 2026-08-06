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
    FRONTEND_URL: str = "http://localhost:3000"
    
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
    def effective_serp_login(self) -> Optional[str]:
        return self.DATAFORSEO_LOGIN

    @computed_field
    @property
    def effective_serp_key(self) -> Optional[str]:
        return self.DATAFORSEO_PASSWORD
    
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
    PINGBACK_URL: Optional[str] = None
    DFO_MOCK_PINGBACK: bool = False

    DATAFORSEO_CREDIT_COSTS: dict = {
        "serp_live_advanced": 0.024,
        "labs_keyword_overview": 0.013,
        "labs_keyword_ideas": 0.018,
        "labs_serp_competitors": 0.132,
        "labs_domain_rank_overview": 0.013,
        "labs_bulk_traffic_estimation": 0.132,
        "labs_keyword_suggestions": 0.018,
        "labs_keywords_for_keywords": 0.018,
        "serp_async_task": 0.012,
    }

    USER_CREDIT_COSTS: dict = {
        "add_keyword": 20,
        "weekly_refresh_per_keyword": 10,
        "keyword_research": 20,
        "competitor_spy": 20,
        "extra_project": 10,
        "tracked_keyword": 20,
        "download_report": 10,
        "team_member": 10,
    }

    PLAN_KEYWORD_LIMITS: dict = {
        "free_trial": 5,
        "starter": 100,
        "pro": 500,
        "agency": 1500,
    }

    PLAN_MONTHLY_CREDITS: dict = {
        "free_trial": 100,
        "starter": 6000,
        "pro": 30000,
        "agency": 80000,
    }

    PLAN_COMPETITOR_SPY_LIMITS: dict = {
        "free_trial": 5,
        "starter": 50,
        "pro": 200,
        "agency": 500,
    }
    
    # Credit top-up: 600 credits per ₹100, multiples of 600 only
    CREDIT_TOP_UP_CONFIG: dict = {
        "credits_per_100_inr": 600,
        "base_price_inr": 100,
        "min_multiplier": 1,
        "no_bulk_discount": True,
    }

    # USD/INR conversion
    CONVERSION_RATE_USD_TO_INR: float = 95.23
    CONVERSION_FEE_PCT: float = 3.0  # 3% conversion margin for USD display

    # GST / Invoice details
    GST_RATE: float = 0.18
    GSTIN: str = "06FHDPK2516L1ZB"
    COMPANY_NAME: str = "CodMonks Technologies"
    COMPANY_ADDRESS: str = "HOUSE NO 769, Sector-64, Ballabhgarh, Faridabad-121004, Haryana"
    COMPANY_EMAIL: str = "mahesh1988.2009@gmail.com"
    COMPANY_STATE: str = "Haryana"
    COMPANY_STATE_CODE: str = "06"

    # Trial
    TRIAL_DAYS: int = 10

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()

def get_settings() -> Settings:
    return settings