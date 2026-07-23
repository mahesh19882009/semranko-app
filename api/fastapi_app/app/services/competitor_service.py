from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import Competitor, Project
from app.services.plan_service import ensure_competitor_limit
from app.utils.serializers import model_to_dict


def normalize_domain(value: str = "") -> str:
    return (
        value.strip()
        .lower()
        .removeprefix("https://")
        .removeprefix("http://")
        .removeprefix("www.")
        .rstrip("/")
    )


def ensure_project_access(db: Session, user_id: str, project_id: str) -> None:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")


def create_competitor(db: Session, user_id: str, payload: dict) -> dict:
    project_id = payload.get("projectId")
    name = payload.get("name")
    domain = payload.get("domain")

    if not project_id or not name or not domain:
        raise ApiError(400, "Project, name and domain are required")

    ensure_project_access(db, user_id, project_id)
    clean_domain = normalize_domain(domain)

    existing = db.scalar(
        select(Competitor).where(
            Competitor.projectId == project_id,
            Competitor.domain == clean_domain,
        )
    )
    if existing:
        raise ApiError(409, "Competitor domain already exists for this project")

    ensure_competitor_limit(db, user_id, project_id)

    competitor = Competitor(projectId=project_id, name=name.strip(), domain=clean_domain)
    db.add(competitor)
    db.commit()
    db.refresh(competitor)
    return model_to_dict(competitor)


def get_competitors_by_project(db: Session, user_id: str, project_id: str) -> list[dict]:
    ensure_project_access(db, user_id, project_id)

    competitors = db.scalars(
        select(Competitor)
        .where(Competitor.projectId == project_id)
        .order_by(desc(Competitor.createdAt))
    ).all()
    return [model_to_dict(item) for item in competitors]


def update_competitor(db: Session, user_id: str, competitor_id: str, payload: dict) -> dict:
    competitor = db.scalar(
        select(Competitor)
        .join(Project, Project.id == Competitor.projectId)
        .where(Competitor.id == competitor_id, Project.userId == user_id)
    )

    if not competitor:
        raise ApiError(404, "Competitor not found")

    next_name = (payload.get("name") or competitor.name).strip()
    next_domain = normalize_domain(payload.get("domain") or competitor.domain)

    if not next_name or not next_domain:
        raise ApiError(400, "Name and domain are required")

    duplicate = db.scalar(
        select(Competitor).where(
            Competitor.projectId == competitor.projectId,
            Competitor.domain == next_domain,
            Competitor.id != competitor_id,
        )
    )
    if duplicate:
        raise ApiError(409, "Another competitor with this domain already exists")

    competitor.name = next_name
    competitor.domain = next_domain
    db.commit()
    db.refresh(competitor)
    return model_to_dict(competitor)


def delete_competitor(db: Session, user_id: str, competitor_id: str) -> None:
    competitor = db.scalar(
        select(Competitor)
        .join(Project, Project.id == Competitor.projectId)
        .where(Competitor.id == competitor_id, Project.userId == user_id)
    )

    if not competitor:
        raise ApiError(404, "Competitor not found")

    db.execute(delete(Competitor).where(Competitor.id == competitor_id))
    db.commit()
    