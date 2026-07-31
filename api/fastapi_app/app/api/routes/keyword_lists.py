from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.keyword_list_service import (
    create_keyword_list,
    get_user_keyword_lists,
    add_keywords_to_list,
    remove_keyword_from_list,
    delete_keyword_list,
    export_keyword_list_csv,
)

router = APIRouter(prefix="/keyword-lists", tags=["keyword-lists"])


@router.post("/")
async def create_list(
    name: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    keyword_list = create_keyword_list(db, current_user["userId"], name)
    return ok("Keyword list created", {"id": keyword_list.id})


@router.get("/")
async def list_lists(
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    lists = get_user_keyword_lists(db, current_user["userId"])
    return ok("Keyword lists retrieved", {"lists": lists})


@router.post("/{list_id}/items")
async def add_items(
    list_id: str,
    keywords: list[str],
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    keyword_list = add_keywords_to_list(db, current_user["userId"], list_id, keywords)
    return ok("Keywords added", {"id": keyword_list.id})


@router.delete("/{list_id}/items/{item_id}")
async def remove_item(
    list_id: str,
    item_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    remove_keyword_from_list(db, current_user["userId"], list_id, item_id)
    return ok("Keyword removed")


@router.delete("/{list_id}")
async def delete_list(
    list_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    delete_keyword_list(db, current_user["userId"], list_id)
    return ok("Keyword list deleted")


@router.get("/{list_id}/export")
async def export_list(
    list_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    csv_data = export_keyword_list_csv(db, current_user["userId"], list_id)
    from fastapi.responses import Response
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=keyword-list-{list_id}.csv"})
