from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.queues.backlink_check_queue import get_backlink_check_queue
from app.db.models import Project

router = APIRouter(prefix="/backlinks", tags=["Backlinks"])

@router.post("/check/{project_id}")
def trigger_backlink_check(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.userId == current_user.id).first()
    if not project: return {"error": "Project not found"}
    
    queue = get_backlink_check_queue()
    job = queue.enqueue("fastapi_app.app.workers.tasks.process_backlink_job", project.id, project.domain)
    return {"queued": True, "jobId": job.id}