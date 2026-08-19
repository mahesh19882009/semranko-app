import secrets
from pathlib import Path
from typing import Optional, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field, BaseModel, model_validator


class PlanDefinition(BaseModel):
    key: str
    name: str
    monthly_price_inr: float
    yearly_price_inr: float
    monthly_price_usd: float = 0
    yearly_price_usd: float = 0
    domain_limit: int
    keyword_limit: int
    competitor_spy_limit: int
    manual_refresh_limit: int
    keyword_research_limit: int
    competitors_per_project: int
    reports_per_month: int
    monthly_credits: int
    automatic_credits: int
    refresh_frequency: str
    individual_discount_pct: float
    cta: str
    highlighted: bool
    description: str
    dfs_cost_ceiling_usd: float = 0.0


class TopUpConfig(BaseModel):
    credits_per_100_inr: int = 600
    base_price_inr: int = 100
    min_multiplier: int = 1
    no_bulk_discount: bool = True


class ConversionConfig(BaseModel):
    rate: float = 95.23
    fee_pct: float = 3.0


class BillingConfig(BaseModel):
    gst_rate: float = 0.18
    gstin: str = "06FHDPK2516L1ZB"
    company_name: str = "CodMonks Technologies"
    company_address: str = "HOUSE NO 769, Sector-64, Ballabhgarh, Faridabad-121004, Haryana"
    company_email: str = "mahesh1988.2009@gmail.com"
    company_state: str = "Haryana"
    company_state_code: str = "06"


class PlanConfig(BaseModel):
    plans: dict[str, PlanDefinition]
    credit_costs: dict[str, float]
    dataforseo_costs: dict[str, float]
    serp_priorities: dict[str, int | None] = {
        "add_keyword": None,
        "bulk_add": None,
        "manual_refresh": None,
        "automatic": None,
        "weekly": None,
        "monthly": None,
    }
    top_up: TopUpConfig
    conversion: ConversionConfig
    billing: BillingConfig
    trial_days: int = 0


# Define Free Plan Limits
FREE_PLAN_LIMITS = {
    "projects": 1,
    "keywords": 5,
    "competitors": 3,
    "reports_per_month": 2
}

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

class Settings(BaseSettings):
    # App Basics
    APP_NAME: str = "Semranko API"
    ENV: str = "development"
    PORT: int = 4000
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: Optional[str] = None
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ACCESS_SECRET: str = "dev-secret-key-change-in-production"
    JWT_ACCESS_EXPIRES_IN_DAYS: int = 1
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    AUTH_COOKIE_NAME: str = "semranko_access"
    SESSION_COOKIE_NAME: str = "semranko_session"
    CSRF_COOKIE_NAME: str = "semranko_csrf"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    AUTH_COOKIE_SAMESITE: str = "lax"
    TURNSTILE_SECRET_KEY: Optional[str] = None
    # Comma-separated emergency/bootstrap allow-list. Durable administrator
    # assignment is User.isAdmin and should be managed through controlled ops.
    ADMIN_EMAILS: str = ""

    @model_validator(mode='after')
    def validate_production_secrets(self):
        if self.ENV == "production":
            if not self.JWT_ACCESS_SECRET or self.JWT_ACCESS_SECRET == "dev-secret-key-change-in-production":
                raise ValueError("JWT_ACCESS_SECRET must be set to a secure value in production")
            if not self.DATAFORSEO_LOGIN or not self.DATAFORSEO_PASSWORD:
                raise ValueError("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD must be set in production")
            if not self.RAZORPAY_KEY_ID or not self.RAZORPAY_KEY_SECRET:
                raise ValueError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set in production")
            if not self.RAZORPAY_WEBHOOK_SECRET:
                raise ValueError("RAZORPAY_WEBHOOK_SECRET must be set in production")
            if not self.DATAFORSEO_WEBHOOK_SECRET:
                raise ValueError("DATAFORSEO_WEBHOOK_SECRET must be set in production")
            if not self.RESEND_API_KEY:
                raise ValueError("RESEND_API_KEY must be set in production")
            if not self.TURNSTILE_SECRET_KEY:
                raise ValueError("TURNSTILE_SECRET_KEY must be set in production")
        return self
    
    # Database
    DATABASE_URL: Optional[str] = None
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "semranko"

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
    EMAIL_FROM: str = "noreply@semranko.com"
    EMAIL_VERIFY_EXPIRE_HOURS: int = 24
    
    # Razorpay
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    # Display pricing may be shown in USD, but checkout remains disabled until
    # the Razorpay account has been approved for international USD payments.
    RAZORPAY_USD_CHECKOUT_ENABLED: bool = False
    
    # SERP / DataForSEO
    SERP_API_LOGIN: Optional[str] = None
    SERP_API_KEY: Optional[str] = None
    PINGBACK_URL: Optional[str] = None
    DFO_MOCK_PINGBACK: bool = False
    DATAFORSEO_WEBHOOK_SECRET: Optional[str] = None

    plan_config: PlanConfig = PlanConfig(
        plans={
            "free_trial": PlanDefinition(
                key="free_trial",
                name="Free",
                monthly_price_inr=0,
                yearly_price_inr=0,
                monthly_price_usd=0,
                yearly_price_usd=0,
                domain_limit=1,
                keyword_limit=5,
                competitor_spy_limit=0,
                manual_refresh_limit=0,
                keyword_research_limit=0,
                competitors_per_project=3,
                reports_per_month=2,
                monthly_credits=100,
                automatic_credits=0,
                refresh_frequency="none",
                individual_discount_pct=0,
                cta="Start Free",
                highlighted=False,
                description="Permanent Free plan for core keyword tracking.",
                dfs_cost_ceiling_usd=5.0,
            ),
            "starter": PlanDefinition(
                key="starter",
                name="Starter",
                monthly_price_inr=999,
                yearly_price_inr=10989,
                monthly_price_usd=14,
                yearly_price_usd=154,
                domain_limit=1,
                keyword_limit=100,
                competitor_spy_limit=3,
                manual_refresh_limit=10,
                keyword_research_limit=10,
                competitors_per_project=3,
                reports_per_month=5,
                monthly_credits=8000,
                automatic_credits=5000,
                refresh_frequency="monthly",
                individual_discount_pct=0,
                cta="Start Starter",
                highlighted=False,
                description="Best for freelancers and small websites starting SEO tracking.",
                dfs_cost_ceiling_usd=25.0,
            ),
            "pro": PlanDefinition(
                key="pro",
                name="Pro",
                monthly_price_inr=3999,
                yearly_price_inr=43989,
                monthly_price_usd=52,
                yearly_price_usd=572,
                domain_limit=5,
                keyword_limit=500,
                competitor_spy_limit=10,
                manual_refresh_limit=50,
                keyword_research_limit=30,
                competitors_per_project=10,
                reports_per_month=10,
                monthly_credits=40000,
                automatic_credits=25000,
                refresh_frequency="monthly",
                individual_discount_pct=0,
                cta="Start Pro",
                highlighted=True,
                description="Ideal for growing businesses that need stronger reporting and tracking.",
                dfs_cost_ceiling_usd=100.0,
            ),
            "agency": PlanDefinition(
                key="agency",
                name="Agency",
                monthly_price_inr=9999,
                yearly_price_inr=109989,
                monthly_price_usd=130,
                yearly_price_usd=1430,
                domain_limit=20,
                keyword_limit=1500,
                competitor_spy_limit=25,
                manual_refresh_limit=150,
                keyword_research_limit=75,
                competitors_per_project=20,
                reports_per_month=50,
                monthly_credits=120000,
                automatic_credits=75000,
                refresh_frequency="monthly",
                individual_discount_pct=0,
                cta="Start Agency",
                highlighted=False,
                description="Built for agencies handling multiple clients and organized client delivery.",
                dfs_cost_ceiling_usd=250.0,
            ),
            "enterprise": PlanDefinition(
                key="enterprise",
                name="Enterprise",
                monthly_price_inr=0,
                yearly_price_inr=0,
                monthly_price_usd=0,
                yearly_price_usd=0,
                domain_limit=999,
                keyword_limit=999999,
                competitor_spy_limit=5000,
                manual_refresh_limit=999999,
                keyword_research_limit=999999,
                competitors_per_project=999,
                reports_per_month=999,
                monthly_credits=999999,
                automatic_credits=0,
                refresh_frequency="monthly",
                individual_discount_pct=0,
                cta="Contact Sales",
                highlighted=False,
                description="Custom bulk allocation for large accounts. Contact sales for pricing.",
                dfs_cost_ceiling_usd=1000.0,
            ),
        },
        credit_costs={
            "add_keyword": 20,
            "weekly_refresh_per_keyword": 10,
            "monthly_refresh_per_keyword": 10,
            "manual_refresh_per_keyword": 20,
            "keyword_research": 20,
            "competitor_spy": 30,
            "extra_project": 10,
            "tracked_keyword": 20,
            "download_report": 10,
            "bulk_add_keyword": 20,
        },
        dataforseo_costs={
            "serp_live_advanced": 0.024,
            "labs_keyword_overview": 0.013,
            "labs_keyword_ideas": 0.018,
            "labs_serp_competitors": 0.132,
            "labs_domain_rank_overview": 0.013,
            "labs_bulk_traffic_estimation": 0.132,
            "labs_keyword_suggestions": 0.018,
            "labs_keywords_for_keywords": 0.018,
            "serp_async_task": 0.012,
        },
        top_up=TopUpConfig(),
        conversion=ConversionConfig(),
        billing=BillingConfig(),
        trial_days=0,
    )

    # Legacy fields kept for backward compatibility with existing code that reads settings.USER_CREDIT_COSTS etc.
    USER_CREDIT_COSTS: dict = {}
    DATAFORSEO_CREDIT_COSTS: dict = {}
    PLAN_KEYWORD_LIMITS: dict = {}
    PLAN_MONTHLY_CREDITS: dict = {}
    PLAN_AUTOMATIC_CREDITS: dict = {}
    PLAN_COMPETITOR_SPY_LIMITS: dict = {}
    CREDIT_TOP_UP_CONFIG: dict = {}
    CONVERSION_RATE_USD_TO_INR: float = 0.0
    CONVERSION_FEE_PCT: float = 0.0
    GST_RATE: float = 0.0
    TRIAL_DAYS: int = 0

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        case_sensitive=True,
        extra="ignore",
    )

    @model_validator(mode='after')
    def sync_legacy_config(self):
        self.USER_CREDIT_COSTS = self.plan_config.credit_costs
        self.DATAFORSEO_CREDIT_COSTS = self.plan_config.dataforseo_costs
        self.PLAN_KEYWORD_LIMITS = {k: v.keyword_limit for k, v in self.plan_config.plans.items()}
        self.PLAN_MONTHLY_CREDITS = {k: v.monthly_credits for k, v in self.plan_config.plans.items()}
        self.PLAN_AUTOMATIC_CREDITS = {k: v.automatic_credits for k, v in self.plan_config.plans.items()}
        self.PLAN_COMPETITOR_SPY_LIMITS = {k: v.competitor_spy_limit for k, v in self.plan_config.plans.items()}
        self.CREDIT_TOP_UP_CONFIG = self.plan_config.top_up.model_dump()
        self.CONVERSION_RATE_USD_TO_INR = self.plan_config.conversion.rate
        self.CONVERSION_FEE_PCT = self.plan_config.conversion.fee_pct
        self.GST_RATE = self.plan_config.billing.gst_rate
        self.TRIAL_DAYS = self.plan_config.trial_days
        return self


settings = Settings()

# Backward-compatible module-level aliases (canonical source is settings.plan_config)
USER_CREDIT_COSTS = settings.plan_config.credit_costs
DATAFORSEO_CREDIT_COSTS = settings.plan_config.dataforseo_costs
PLAN_KEYWORD_LIMITS = {k: v.keyword_limit for k, v in settings.plan_config.plans.items()}
PLAN_MONTHLY_CREDITS = {k: v.monthly_credits for k, v in settings.plan_config.plans.items()}
PLAN_AUTOMATIC_CREDITS = {k: v.automatic_credits for k, v in settings.plan_config.plans.items()}
PLAN_COMPETITOR_SPY_LIMITS = {k: v.competitor_spy_limit for k, v in settings.plan_config.plans.items()}
CREDIT_TOP_UP_CONFIG = settings.plan_config.top_up.model_dump()
CONVERSION_RATE_USD_TO_INR = settings.plan_config.conversion.rate
CONVERSION_FEE_PCT = settings.plan_config.conversion.fee_pct
GST_RATE = settings.plan_config.billing.gst_rate
TRIAL_DAYS = settings.plan_config.trial_days


def get_settings() -> Settings:
    return settings
