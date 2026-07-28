from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.keyword_service import add_keyword, add_keywords_bulk, delete_keyword, delete_keywords_bulk, get_project_keywords

router = APIRouter(prefix="/keywords", tags=["keywords"])


@router.post("/{project_id}")
def create_keyword(
    project_id: str,
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> JSONResponse:
    keyword = add_keyword(db, user["userId"], project_id, payload)
    return JSONResponse(status_code=201, content={"success": True, "message": "Keyword added", "data": keyword})


@router.post("/{project_id}/bulk")
def bulk_create_keywords(
    project_id: str,
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    keywords = payload.get("keywords", [])
    result = add_keywords_bulk(db, user["userId"], project_id, keywords)
    return {
        "success": True,
        "message": f"Added {result['added']} keywords, skipped {result['skipped']} duplicates",
        "data": result,
    }


@router.get("/{project_id}")
def list_keywords(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    keywords = get_project_keywords(db, user["userId"], project_id)
    return {"success": True, "message": "Keywords fetched", "data": keywords}


@router.delete("/bulk")
def bulk_delete_keywords(
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    keyword_ids = payload.get("keyword_ids", [])
    deleted = delete_keywords_bulk(db, user["userId"], keyword_ids)
    return ok(f"Deleted {deleted} keywords", None)


@router.delete("/{keyword_id}")
def remove_keyword(keyword_id: str, user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    delete_keyword(db, user["userId"], keyword_id)
    return ok("Keyword deleted successfully", None)
