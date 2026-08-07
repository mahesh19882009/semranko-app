from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user, verify_user_access_privileges, verify_user_access_privileges
from app.schemas.common import ok
from app.services.aio_service import get_aio_dashboard, get_citation_share_of_voice, get_aio_detail
from app.db.models import AIOTracking
from sqlalchemy import select

router = APIRouter(prefix="/aio", tags=["aio"])


@router.get("/{project_id}/dashboard")
async def aio_dashboard(
    project_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    verify_user_access_privileges(db, current_user)
    
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
    verify_user_access_privileges(db, current_user)
    
    try:
        result = get_citation_share_of_voice(db, current_user["userId"], project_id)
        return ok("Citation share of voice retrieved", {"citations": result})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/keyword/{keyword_text}")
async def aio_keyword_detail(
    project_id: str,
    keyword_text: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    verify_user_access_privileges(db, current_user)
    
    try:
        result = get_aio_detail(db, current_user["userId"], project_id, keyword_text)
        if not result:
            raise HTTPException(status_code=404, detail="AIO tracking not found for this keyword")
        return ok("AIO detail retrieved", result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
