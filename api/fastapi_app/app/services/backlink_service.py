from sqlalchemy import desc, select, func
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import Backlink, Project
from app.utils.serializers import model_to_dict


def ensure_project_access(db: Session, user_id: str, project_id: str) -> None:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")


def get_project_backlinks(db: Session, user_id: str, project_id: str, page: int = 1, page_size: int = 50) -> dict:
    ensure_project_access(db, user_id, project_id)

    query = select(Backlink).where(Backlink.projectId == project_id).order_by(desc(Backlink.checkedAt))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    items = db.scalars(
        query.offset((page - 1) * page_size).limit(page_size)
    ).all()

    return {
        "backlinks": [model_to_dict(item) for item in items],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        },
    }
