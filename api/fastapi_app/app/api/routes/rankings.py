from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.ranking_service import (
    delete_project_rankings,
    delete_ranking,
    get_project_rankings,
    run_rank_check,
)

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("/{project_id}")
def list_rankings(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    rankings = get_project_rankings(db, user["userId"], project_id)
    return {"success": True, "message": "Rankings fetched", "data": rankings}


@router.post("/{project_id}/run")
def create_rank_check(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> JSONResponse:
    result = run_rank_check(db, user["userId"], project_id)
    return JSONResponse(
        status_code=202,
        content={
            "success": True,
            "message": "Rank check queued successfully",
            "data": result,
        },
    )


@router.delete("/project/{project_id}")
def clear_rankings_by_project(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    delete_project_rankings(db, user["userId"], project_id)
    return ok("Project rankings cleared successfully", None)


@router.delete("/{ranking_id}")
def remove_ranking(
    ranking_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    delete_ranking(db, user["userId"], ranking_id)
    return ok("Ranking deleted successfully", None)