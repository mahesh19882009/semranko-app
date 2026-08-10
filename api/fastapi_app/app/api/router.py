from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.projects import router as projects_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.keywords import router as keywords_router
from app.api.routes.rankings import router as rankings_router
from app.api.routes.competitors import router as competitors_router
from app.api.routes.pricing import router as pricing_router
from app.api.routes.payments import router as payments_router
from app.api.routes.keyword_research import router as keyword_research_router
from app.api.routes.serp_features import router as serp_features_router
from app.api.routes.competitor_rankings import router as competitor_rankings_router
from app.api.routes.credits import router as credits_router
from app.api.routes.keyword_metrics import router as keyword_metrics_router
from app.api.routes.marketing import router as marketing_router
from app.api.routes.tracked_keywords import router as tracked_keywords_router
from app.api.routes.reports import router as reports_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes.settings import router as settings_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(dashboard_router)
api_router.include_router(keywords_router)
api_router.include_router(rankings_router)
api_router.include_router(competitors_router)
api_router.include_router(pricing_router)
api_router.include_router(payments_router)
api_router.include_router(keyword_research_router)
api_router.include_router(serp_features_router)
api_router.include_router(competitor_rankings_router)
api_router.include_router(credits_router)
api_router.include_router(keyword_metrics_router)
api_router.include_router(marketing_router)
api_router.include_router(tracked_keywords_router)
api_router.include_router(reports_router)
api_router.include_router(webhooks_router)
api_router.include_router(settings_router)
