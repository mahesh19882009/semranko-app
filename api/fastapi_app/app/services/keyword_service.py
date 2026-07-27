from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import Keyword, Project
from app.services.plan_service import ensure_keyword_limit, count_user_keywords, get_user_plan_limits, get_user_or_404
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


def add_keywords_bulk(db: Session, user_id: str, project_id: str, keywords: list[str]) -> dict:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    user = get_user_or_404(db, user_id)
    current_count = count_user_keywords(db, user_id)
    limits = get_user_plan_limits(user)
    max_keywords = limits.get("keywords", 0)

    if current_count + len(keywords) > max_keywords:
        raise ApiError(
            400,
            f"Keyword limit exceeded. You can add {max_keywords - current_count} more keywords.",
        )

    normalized_keywords = []
    for kw in keywords:
        kw = kw.strip().lower()
        if kw:
            normalized_keywords.append(kw)

    existing = db.scalars(
        select(Keyword.keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword.in_(normalized_keywords),
        )
    ).all()
    existing_set = set(existing)

    added = []
    for kw in normalized_keywords:
        if kw in existing_set:
            continue

        keyword = Keyword(
            projectId=project_id,
            keyword=kw,
            location=None,
            device="desktop",
        )
        db.add(keyword)
        added.append(kw)
        existing_set.add(kw)

    db.commit()

    return {
        "added": len(added),
        "skipped": len(normalized_keywords) - len(added),
        "keywords": added,
    }


def delete_keywords_bulk(db: Session, user_id: str, keyword_ids: list[str]) -> int:
    count = 0
    for keyword_id in keyword_ids:
        keyword = db.scalar(
            select(Keyword)
            .join(Project, Project.id == Keyword.projectId)
            .where(Keyword.id == keyword_id, Project.userId == user_id)
        )
        if keyword:
            db.execute(delete(Keyword).where(Keyword.id == keyword_id))
            count += 1
    db.commit()
    return count


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