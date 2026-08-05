from fastapi import APIRouter, Body, Depends, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
import os
import uuid

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.project_service import create_project, delete_project, get_project_by_id, get_projects, update_project
from app.services.plan_service import get_user_or_404, get_effective_plan_key
from app.core.security import enforce_limits
from app.core.config import get_settings
from app.db.models import Project

router = APIRouter(prefix="/projects", tags=["projects"])

settings = get_settings()
LOGO_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "logos")
os.makedirs(LOGO_UPLOAD_DIR, exist_ok=True)


@router.post("")
@enforce_limits(resource_type='project')
def create(
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> JSONResponse:
    project = create_project(db, user["userId"], payload)
    return JSONResponse(status_code=201, content=ok("Project created", project))


@router.get("")
def list_projects(user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    projects = get_projects(db, user["userId"])
    return ok("Projects fetched", projects)


@router.get("/{project_id}")
def get_one(project_id: str, user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    project = get_project_by_id(db, user["userId"], project_id)
    return ok("Project fetched", project)


@router.put("/{project_id}")
def update_one(project_id: str, payload: dict = Body(...), user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    project = update_project(db, user["userId"], project_id, payload)
    return ok("Project updated successfully", project)


@router.delete("/{project_id}")
def remove_project(project_id: str, user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    delete_project(db, user["userId"], project_id)
    return ok("Project deleted successfully", None)


@router.post("/{project_id}/upload-logo")
async def upload_project_logo(
    project_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    db_user = get_user_or_404(db, user["userId"])
    effective_plan = get_effective_plan_key(db_user)
    if effective_plan not in {"agency", "custom"}:
        raise HTTPException(status_code=403, detail="White-label logo upload is only available for Agency and Custom plans")

    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user["userId"])
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/svg+xml"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload JPG, PNG, WebP, or SVG.")

    ext = os.path.splitext(file.filename)[1].lower() or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(LOGO_UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    public_path = f"/static/logos/{filename}"
    project.client_logo_url = public_path
    db.add(project)
    db.commit()
    db.refresh(project)

    return ok("Logo uploaded successfully", {"client_logo_url": public_path})
