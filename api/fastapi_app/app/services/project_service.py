import json
from sqlalchemy import delete, desc, select, update
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import Keyword, Project, RankResult
from app.services.plan_service import ensure_project_limit, ensure_domain_limit
from app.utils.serializers import model_to_dict


def _normalize_domain(domain: str) -> str:
    domain = domain.strip().lower()
    for prefix in ("https://", "http://", "www."):
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
    domain = domain.rstrip("/")
    if ":" in domain:
        domain = domain.split(":", 1)[0]
    return domain


def create_project(db: Session, user_id: str, payload: dict) -> dict:
    name = payload.get("name")
    domain = payload.get("domain")

    if not name or not domain:
        raise ApiError(400, "Name and domain are required")

    ensure_project_limit(db, user_id)
    ensure_domain_limit(db, user_id)

    location = payload.get("location")
    location_code = payload.get("locationCode")
    if location_code is None and isinstance(location, dict):
        location_code = location.get("locationCode")

    device = payload.get("device")

    project = Project(
        name=name.strip(),
        domain=_normalize_domain(domain),
        userId=user_id,
        location=json.dumps(location) if isinstance(location, dict) else location,
        locationCode=location_code,
        device=device,
    )
    db.add(project)
    db.flush()

    db.commit()
    db.refresh(project)

    return model_to_dict(project)


def get_projects(db: Session, user_id: str) -> list[dict]:
    projects = db.scalars(
        select(Project).where(Project.userId == user_id).order_by(desc(Project.createdAt))
    ).all()
    return [model_to_dict(project) for project in projects]


def get_project_by_id(db: Session, user_id: str, project_id: str) -> dict:
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        raise ApiError(404, "Project not found")
    return model_to_dict(project)


def update_project(db: Session, user_id: str, project_id: str, payload: dict) -> dict:
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        raise ApiError(404, "Project not found")

    name = payload.get("name")
    domain = payload.get("domain")

    if name:
        project.name = name.strip()
    if domain:
        project.domain = _normalize_domain(domain)
    if "location" in payload:
        loc = payload["location"]
        project.location = json.dumps(loc) if isinstance(loc, dict) else loc
        if "locationCode" not in payload and isinstance(loc, dict) and loc.get("locationCode"):
            project.locationCode = loc["locationCode"]
    if "locationCode" in payload:
        project.locationCode = payload["locationCode"]
    if "device" in payload:
        project.device = payload["device"]

    db.commit()
    db.refresh(project)

    return model_to_dict(project)


def delete_project(db: Session, user_id: str, project_id: str) -> None:
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        raise ApiError(404, "Project not found")

    db.execute(delete(RankResult).where(RankResult.projectId == project_id))
    db.execute(delete(Keyword).where(Keyword.projectId == project_id))
    db.execute(delete(Project).where(Project.id == project_id))

    db.commit()
