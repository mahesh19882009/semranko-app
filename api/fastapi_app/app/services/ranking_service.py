from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from app.core.errors import ApiError
from app.db.models import Keyword, Project, RankResult, User, Competitor
from app.queues.rank_check_queue import get_rank_check_queue
from app.utils.serializers import model_to_dict
from app.services.credit_service import reserve_credits, consume_reserved, refund_reserved
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def run_rank_check(db: Session, user_id: str, project_id: str) -> dict:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    keywords = db.scalars(select(Keyword).where(Keyword.projectId == project_id)).all()
    if not keywords:
        raise ApiError(400, "Add at least one keyword before running rank check")

    refresh_cost = settings.plan_config.credit_costs.get("weekly_refresh_per_keyword", 10)
    total_required = len(keywords) * refresh_cost
    reference = f"rankcheck:{project_id}:{datetime.utcnow().timestamp()}"
    try:
        reserve_credits(
            db,
            user_id,
            float(total_required),
            "reservation",
            f"Rank check reservation: {len(keywords)} keyword(s) for project {project_id}",
            reference=reference,
            project_id=project_id,
        )
    except Exception as exc:
        logger.error(f"Rank check credit reservation failed: {exc}")
        raise ApiError(402, f"Insufficient credits for rank check. Required: {total_required}")

    queue = get_rank_check_queue()
    payload_keywords = [model_to_dict(keyword) for keyword in keywords]
    job = queue.enqueue("fastapi_app.app.workers.tasks.process_rank_check_job", project.id, project.domain, payload_keywords, user_id, reference, job_timeout="600")

    return {
        "queued": True,
        "jobId": job.id,
        "projectId": project.id,
        "keywordCount": len(payload_keywords),
    }


def queue_rank_check_for_project(db: Session, project_id: str) -> dict | None:
    project = db.scalar(select(Project).where(Project.id == project_id))
    if not project:
        return None

    keywords = db.scalars(select(Keyword).where(Keyword.projectId == project_id)).all()
    if not keywords:
        return None

    queue = get_rank_check_queue()
    payload_keywords = [model_to_dict(keyword) for keyword in keywords]
    job = queue.enqueue("fastapi_app.app.workers.tasks.process_rank_check_job", project.id, project.domain, payload_keywords, job_timeout="600")

    return {
        "queued": True,
        "jobId": job.id,
        "projectId": project.id,
        "keywordCount": len(payload_keywords),
    }


def get_project_rankings(db: Session, user_id: str, project_id: str) -> list[dict]:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    rows = db.scalars(
        select(RankResult)
        .where(RankResult.projectId == project_id)
        .order_by(desc(RankResult.checkedAt))
    ).all()
    return [model_to_dict(item) for item in rows]


def delete_rankings_bulk(db: Session, user_id: str, ranking_ids: list[str]) -> int:
    count = 0
    for ranking_id in ranking_ids:
        ranking = db.scalar(
            select(RankResult)
            .join(Project, Project.id == RankResult.projectId)
            .where(RankResult.id == ranking_id, Project.userId == user_id)
        )
        if ranking:
            db.execute(delete(RankResult).where(RankResult.id == ranking_id))
            count += 1
    db.commit()
    return count


def delete_ranking(db: Session, user_id: str, ranking_id: str) -> None:
    ranking = db.scalar(
        select(RankResult)
        .join(Project, Project.id == RankResult.projectId)
        .where(RankResult.id == ranking_id, Project.userId == user_id)
    )

    if not ranking:
        raise ApiError(404, "Ranking not found")

    db.execute(delete(RankResult).where(RankResult.id == ranking_id))
    db.commit()


def delete_project_rankings(db: Session, user_id: str, project_id: str) -> None:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    db.execute(delete(RankResult).where(RankResult.projectId == project_id))
    db.commit()


def queue_competitor_tracking_for_project(db: Session, project_id: str) -> dict | None:
    project = db.scalar(select(Project).where(Project.id == project_id))
    if not project:
        return None

    competitors = db.scalars(select(Competitor).where(Competitor.projectId == project_id)).all()
    keywords = db.scalars(select(Keyword).where(Keyword.projectId == project_id)).all()

    if not competitors or not keywords:
        return None

    queue = get_rank_check_queue()
    payload_keywords = [model_to_dict(keyword) for keyword in keywords]
    competitor_ids = [comp.id for comp in competitors]
    job = queue.enqueue(
        "fastapi_app.app.workers.tasks.process_competitor_rank_job",
        project.id,
        project.domain,
        competitor_ids,
        payload_keywords,
        job_timeout="600",
    )

    return {
        "queued": True,
        "jobId": job.id,
        "projectId": project.id,
        "competitorCount": len(competitors),
        "keywordCount": len(payload_keywords),
    }


def queue_weekly_tracking_for_all_projects(db: Session) -> dict:
    projects = db.scalars(select(Project)).all()

    queued_projects = 0
    rank_jobs = []
    competitor_jobs = []

    for project in projects:
        rank_result = queue_rank_check_for_project(db, project.id)
        if rank_result:
            queued_projects += 1
            rank_jobs.append(rank_result["jobId"])

        competitor_result = queue_competitor_tracking_for_project(db, project.id)
        if competitor_result:
            competitor_jobs.append(competitor_result["jobId"])

    return {
        "queued": True,
        "projectsQueued": queued_projects,
        "rankJobIds": rank_jobs,
        "competitorJobIds": competitor_jobs,
    }