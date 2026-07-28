from fastapi import APIRouter

from app.api.routes.audits import router as audits_router
from app.api.routes.auth import router as auth_router
from app.api.routes.api_keys import router as api_keys_router
from app.api.routes.competitors import router as competitors_router
from app.api.routes.contact import router as contact_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.keyword_research import router as keyword_research_router
from app.api.routes.keywords import router as keywords_router
from app.api.routes.lhf import router as lhf_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.pricing import router as pricing_router
from app.api.routes.projects import router as projects_router
from app.api.routes.rankings import router as rankings_router
from app.api.routes.reports import router as reports_router
from app.api.routes.scheduled_reports import router as scheduled_reports_router
from app.api.routes.search import router as search_router
from app.api.routes.serp_features import router as serp_features_router
from app.api.routes.settings import router as settings_router
from app.api.routes.payments import router as payments_router
from app.api.routes.teams import router as teams_router
from app.api.routes.white_label import router as white_label_router
from app.api.routes.agency_dashboard import router as agency_dashboard_router
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
api_router.include_router(keyword_research_router)
api_router.include_router(lhf_router)
api_router.include_router(serp_features_router)
api_router.include_router(api_keys_router)
api_router.include_router(scheduled_reports_router)
api_router.include_router(teams_router)
api_router.include_router(white_label_router)
api_router.include_router(agency_dashboard_router)