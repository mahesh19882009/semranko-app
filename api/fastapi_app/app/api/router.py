from fastapi import APIRouter

from app.api.routes.audits import router as audits_router
from app.api.routes.auth import router as auth_router
from app.api.routes.competitors import router as competitors_router
from app.api.routes.contact import router as contact_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.keywords import router as keywords_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.pricing import router as pricing_router
from app.api.routes.projects import router as projects_router
from app.api.routes.rankings import router as rankings_router
from app.api.routes.reports import router as reports_router
from app.api.routes.search import router as search_router
from app.api.routes.settings import router as settings_router
from app.api.routes.payments import router as payments_router
from app.api.routes import backlinks

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(dashboard_router)
api_router.include_router(audits_router)
api_router.include_router(keywords_router)
api_router.include_router(rankings_router)
api_router.include_router(competitors_router)
api_router.include_router(reports_router)
api_router.include_router(settings_router)
api_router.include_router(notifications_router)
api_router.include_router(search_router)
api_router.include_router(pricing_router)
api_router.include_router(payments_router)
api_router.include_router(backlinks.router)
api_router.include_router(contact_router)