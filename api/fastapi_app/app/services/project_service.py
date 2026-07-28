from sqlalchemy import delete, desc, select, update
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import Keyword, Project, RankResult, Notification
from app.services.notification_service import create_notification
from app.services.plan_service import ensure_project_limit
from app.utils.serializers import model_to_dict


def create_project(db: Session, user_id: str, payload: dict) -> dict:
    name = payload.get("name")
    domain = payload.get("domain")

    if not name or not domain:
        raise ApiError(400, "Name and domain are required")

    ensure_project_limit(db, user_id)

    project = Project(
        name=name.strip(),
        domain=domain.strip(),
        userId=user_id,
    )
    db.add(project)
    db.flush()

    create_notification(
        db,
        user_id=user_id,
        project_id=project.id,
        type="PROJECT_CREATED",
        title="Project created",
        message=f"{project.name} project was created successfully.",
        severity="info",
        entity_type="project",
        entity_id=project.id,
        metadata={
            "projectId": project.id,
            "projectName": project.name,
            "event": "PROJECT_CREATED",
        },
    )

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
        project.domain = domain.strip()

    db.flush()

    create_notification(
        db,
        user_id=user_id,
        project_id=project.id,
        type="PROJECT_UPDATED",
        title="Project updated",
        message=f"{project.name} project was updated successfully.",
        severity="info",
        entity_type="project",
        entity_id=project.id,
        metadata={
            "projectId": project.id,
            "projectName": project.name,
            "event": "PROJECT_UPDATED",
        },
    )

    db.commit()
    db.refresh(project)

    return model_to_dict(project)


def delete_project(db: Session, user_id: str, project_id: str) -> None:
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        raise ApiError(404, "Project not found")

    project_name = project.name

    create_notification(
        db,
        user_id=user_id,
        project_id=project_id,
        type="PROJECT_DELETED",
        title="Project deleted",
        message=f"{project_name} project was deleted successfully.",
        severity="info",
        entity_type="project",
        entity_id=project_id,
        metadata={
            "projectId": project_id,
            "projectName": project_name,
            "event": "PROJECT_DELETED",
        },
    )

    db.execute(
        update(Notification)
        .where(Notification.projectId == project_id)
        .values(projectId=None)
    )

    db.execute(delete(RankResult).where(RankResult.projectId == project_id))
    db.execute(delete(Keyword).where(Keyword.projectId == project_id))
    db.execute(delete(Project).where(Project.id == project_id))

    db.commit()