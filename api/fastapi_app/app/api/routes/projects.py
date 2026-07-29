from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.project_service import create_project, delete_project, get_project_by_id, get_projects, update_project
from app.core.security import enforce_limits

router = APIRouter(prefix="/projects", tags=["projects"])


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
