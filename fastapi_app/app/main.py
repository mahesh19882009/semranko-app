from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.db.models import Base
from app.db.session import engine
from app.jobs.rank_scheduler import start_scheduler, stop_scheduler

settings = get_settings()

app = FastAPI(title=settings.APP_NAME)

origins = [settings.FRONTEND_URL] if settings.FRONTEND_URL else ["*"]

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
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/health")
def health_check() -> dict:
    return {"success": True, "message": "API is running"}


app.include_router(api_router)
register_exception_handlers(app)