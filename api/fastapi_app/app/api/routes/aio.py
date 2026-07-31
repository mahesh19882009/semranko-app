from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.aio_service import track_aio_for_project, get_aio_dashboard, get_citation_share_of_voice

router = APIRouter(prefix="/aio", tags=["aio"])


@router.post("/{project_id}/track")
async def track_aio(
    project_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    try:
        result = track_aio_for_project(db, current_user["userId"], project_id)
        return ok("AIO tracking completed", result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/dashboard")
async def aio_dashboard(
    project_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    try:
        result = get_aio_dashboard(db, current_user["userId"], project_id)
        return ok("AIO dashboard retrieved", result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/citations")
async def aio_citations(
    project_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    try:
        result = get_citation_share_of_voice(db, current_user["userId"], project_id)
        return ok("Citation share of voice retrieved", {"citations": result})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
