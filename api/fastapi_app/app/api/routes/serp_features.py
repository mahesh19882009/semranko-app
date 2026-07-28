from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.db.models import User
from app.schemas.common import ok
from app.services.serp_feature_service import (
    get_serp_features_for_keyword,
    get_serp_features_summary,
    get_keywords_with_serp_features,
    sync_serp_features_from_rank_results,
)

router = APIRouter(prefix="/serp-features", tags=["serp-features"])


@router.get("/keyword")
async def get_keyword_serp_features(
    project_id: str = Query(..., description="Project ID"),
    keyword: str = Query(..., description="Keyword"),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get SERP features for a specific keyword
    """
    features = get_serp_features_for_keyword(db, project_id, keyword)
    return ok("SERP features retrieved", {"features": features})


@router.get("/summary")
async def get_serp_features_summary_endpoint(
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get SERP features summary for a project
    """
    summary = get_serp_features_summary(db, project_id)
    return ok("SERP features summary retrieved", summary)


@router.get("/keywords")
async def get_keywords_with_features_endpoint(
    project_id: str = Query(..., description="Project ID"),
    limit: int = Query(50, description="Number of keywords to return"),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get keywords that have SERP features
    """
    keywords = get_keywords_with_serp_features(db, project_id, limit)
    return ok("Keywords with SERP features retrieved", {"keywords": keywords})


@router.post("/sync")
async def sync_serp_features_endpoint(
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Sync SERP features from latest rank results
    """
    synced_count = sync_serp_features_from_rank_results(db, project_id)
    return ok("SERP features synced", {"syncedCount": synced_count})
