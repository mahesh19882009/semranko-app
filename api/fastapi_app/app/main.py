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

login = settings.effective_serp_login
key = settings.effective_serp_key
logger.info(f"DataForSEO login configured: {bool(login)} value={login}")
logger.info(f"DataForSEO key configured: {bool(key)} value={key[:10]}..." if key else "DataForSEO key configured: False")

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

        if "project" in table_names:
            columns = [c["name"] for c in inspector.get_columns("Project")]
            if "client_logo_url" not in columns:
                with engine.connect() as conn:
                    conn.execute(text('ALTER TABLE "Project" ADD COLUMN client_logo_url VARCHAR(500)'))
                    conn.commit()
                logger.info("Added client_logo_url column to Project")

        if "keyword" in table_names:
            columns = [c["name"] for c in inspector.get_columns("Keyword")]
            keyword_alters = []
            if "userId" not in columns:
                keyword_alters.append('ADD COLUMN "userId" VARCHAR NOT NULL DEFAULT \'\'')
            if "position" not in columns:
                keyword_alters.append('ADD COLUMN "position" INTEGER')
            if "ai_badge" not in columns:
                keyword_alters.append('ADD COLUMN "ai_badge" VARCHAR')
            if "visibility" not in columns:
                keyword_alters.append('ADD COLUMN "visibility" FLOAT')
            if "isActive" not in columns:
                keyword_alters.append('ADD COLUMN "isActive" BOOLEAN NOT NULL DEFAULT TRUE')
            if "updatedAt" not in columns:
                keyword_alters.append('ADD COLUMN "updatedAt" TIMESTAMP NOT NULL DEFAULT NOW()')
            if keyword_alters:
                with engine.connect() as conn:
                    conn.execute(text(f'ALTER TABLE "Keyword" {", ".join(keyword_alters)}'))
                    conn.commit()
                logger.info("Added missing Keyword columns: %s", ", ".join(keyword_alters))

        if "rankeresult" in table_names:
            columns = [c["name"] for c in inspector.get_columns("RankResult")]
            if "etv" not in columns:
                with engine.connect() as conn:
                    conn.execute(text('ALTER TABLE "RankResult" ADD COLUMN "etv" FLOAT'))
                    conn.commit()
                logger.info("Added etv column to RankResult")
            indexes = [c["name"] for c in inspector.get_indexes("RankResult")]
            if "RankResult_projectId_keywordId_checkedAt_idx" not in indexes:
                with engine.connect() as conn:
                    conn.execute(text('CREATE INDEX "RankResult_projectId_keywordId_checkedAt_idx" ON "RankResult" ("projectId", "keywordId", "checkedAt")'))
                    conn.commit()
                logger.info("Created RankResult history index")

        if "aiotracking" in table_names:
            columns = [c["name"] for c in inspector.get_columns("AIOTracking")]
            aio_alters = []
            if "aiOverviewTitle" not in columns:
                aio_alters.append('ADD COLUMN "aiOverviewTitle" VARCHAR')
            if "aiOverviewMarkdown" not in columns:
                aio_alters.append('ADD COLUMN "aiOverviewMarkdown" TEXT')
            if "references" not in columns:
                aio_alters.append('ADD COLUMN "references" JSON')
            if "images" not in columns:
                aio_alters.append('ADD COLUMN "images" JSON')
            if "aiOverviewType" not in columns:
                aio_alters.append('ADD COLUMN "aiOverviewType" VARCHAR')
            if aio_alters:
                with engine.connect() as conn:
                    conn.execute(text(f'ALTER TABLE "AIOTracking" {", ".join(aio_alters)}'))
                    conn.commit()
                logger.info("Added missing AIOTracking columns: %s", ", ".join(aio_alters))
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
