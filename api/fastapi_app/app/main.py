from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import inspect as sa_inspect, text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.db.models import Base
from app.db.session import engine
from app.jobs.rank_scheduler import start_scheduler, stop_scheduler
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

origins = [settings.FRONTEND_URL] if settings.FRONTEND_URL else ["*"]

# Properly add CORS middleware
app = FastAPI(
    title=settings.APP_NAME,
    description="RankCare SEO Analytics API - Track rankings, analyze competitors, and optimize your SEO strategy",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)

    try:
        inspector = sa_inspect(engine)
        table_names = [name.lower() for name in inspector.get_table_names()]
        
        if "paymentorder" in table_names:
            columns = [c["name"] for c in inspector.get_columns("PaymentOrder")]
            if "credit_applied_paise" not in columns:
                with engine.connect() as conn:
                    conn.execute(text('ALTER TABLE "PaymentOrder" ADD COLUMN credit_applied_paise INTEGER'))
                    conn.commit()
                logger.info("Added credit_applied_paise column to PaymentOrder")
        
        if "user" in table_names:
            columns = [c["name"] for c in inspector.get_columns("User")]
            if "pendingPlanChange" not in columns:
                with engine.connect() as conn:
                    conn.execute(text('ALTER TABLE "User" ADD COLUMN pendingPlanChange VARCHAR'))
                    conn.commit()
                logger.info("Added pendingPlanChange column to User")
    except Exception as exc:
        logger.error(f"Startup migration failed: {exc}")

    start_scheduler()

@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()

@app.get("/health")
def health_check() -> dict:
    return {"success": True, "message": "API is running"}

app.include_router(api_router)
