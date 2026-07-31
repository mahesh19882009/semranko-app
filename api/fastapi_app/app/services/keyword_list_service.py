import csv
import io
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import KeywordList, KeywordListItem, User
from app.services.plan_service import get_user_plan_limits
from app.core.errors import ApiError

logger = logging.getLogger(__name__)


def create_keyword_list(db: Session, user_id: str, name: str) -> KeywordList:
    keyword_list = KeywordList(userId=user_id, name=name)
    db.add(keyword_list)
    db.commit()
    db.refresh(keyword_list)
    return keyword_list


def get_user_keyword_lists(db: Session, user_id: str) -> list[KeywordList]:
    return db.scalars(select(KeywordList).where(KeywordList.userId == user_id).order_by(KeywordList.createdAt.desc())).all()


def add_keywords_to_list(db: Session, user_id: str, list_id: str, keywords: list[str]) -> KeywordList:
    keyword_list = db.scalar(select(KeywordList).where(KeywordList.id == list_id, KeywordList.userId == user_id))
    if not keyword_list:
        raise ApiError(404, "Keyword list not found")

    for kw in keywords:
        item = KeywordListItem(listId=list_id, keyword=kw)
        db.add(item)

    db.commit()
    db.refresh(keyword_list)
    return keyword_list


def remove_keyword_from_list(db: Session, user_id: str, list_id: str, item_id: str) -> None:
    item = db.scalar(
        select(KeywordListItem)
        .join(KeywordList, KeywordList.id == KeywordListItem.listId)
        .where(KeywordListItem.id == item_id, KeywordList.userId == user_id)
    )
    if not item:
        raise ApiError(404, "Keyword list item not found")

    db.delete(item)
    db.commit()


def delete_keyword_list(db: Session, user_id: str, list_id: str) -> None:
    keyword_list = db.scalar(select(KeywordList).where(KeywordList.id == list_id, KeywordList.userId == user_id))
    if not keyword_list:
        raise ApiError(404, "Keyword list not found")

    db.delete(keyword_list)
    db.commit()


def export_keyword_list_csv(db: Session, user_id: str, list_id: str) -> str:
    keyword_list = db.scalar(select(KeywordList).where(KeywordList.id == list_id, KeywordList.userId == user_id))
    if not keyword_list:
        raise ApiError(404, "Keyword list not found")

    items = db.scalars(select(KeywordListItem).where(KeywordListItem.listId == list_id)).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["keyword"])
    for item in items:
        writer.writerow([item.keyword])

    return output.getvalue()
