from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.services.search_service import search_global

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def global_search(
    q: str = Query(..., min_length=1),
    projectId: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    data = search_global(db, user["userId"], q, projectId)
    return {
        "success": True,
        "message": "Search results fetched successfully",
        "data": data,
    }