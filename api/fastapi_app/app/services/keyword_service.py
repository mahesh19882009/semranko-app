from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import Keyword, Project
from app.services.plan_service import ensure_keyword_limit
from app.utils.serializers import model_to_dict


def add_keyword(db: Session, user_id: str, project_id: str, payload: dict) -> dict:
    keyword_text = payload.get("keyword")

    if not keyword_text:
        raise ApiError(400, "Keyword is required")

    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    normalized_keyword = keyword_text.strip().lower()
    if not normalized_keyword:
        raise ApiError(400, "Keyword is required")

    existing = db.scalar(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword == normalized_keyword,
        )
    )
    if existing:
        raise ApiError(409, "Keyword already exists for this project")

    ensure_keyword_limit(db, user_id)

    keyword = Keyword(
        projectId=project_id,
        keyword=normalized_keyword,
        location=(payload.get("location") or None),
        device=(payload.get("device") or "desktop"),
    )
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return model_to_dict(keyword)


def get_project_keywords(db: Session, user_id: str, project_id: str) -> list[dict]:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    keywords = db.scalars(
        select(Keyword).where(Keyword.projectId == project_id).order_by(desc(Keyword.createdAt))
    ).all()
    return [model_to_dict(keyword) for keyword in keywords]


def delete_keyword(db: Session, user_id: str, keyword_id: str) -> None:
    keyword = db.scalar(
        select(Keyword)
        .join(Project, Project.id == Keyword.projectId)
        .where(Keyword.id == keyword_id, Project.userId == user_id)
    )

    if not keyword:
        raise ApiError(404, "Keyword not found")

    db.execute(delete(Keyword).where(Keyword.id == keyword_id))
    db.commit()