from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import Keyword, Project, RankResult, User, Competitor
from app.queues.rank_check_queue import get_rank_check_queue
from app.utils.serializers import model_to_dict


def run_rank_check(db: Session, user_id: str, project_id: str) -> dict:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    keywords = db.scalars(select(Keyword).where(Keyword.projectId == project_id)).all()
    if not keywords:
        raise ApiError(400, "Add at least one keyword before running rank check")

    queue = get_rank_check_queue()
    payload_keywords = [model_to_dict(keyword) for keyword in keywords]
    job = queue.enqueue("fastapi_app.app.workers.tasks.process_rank_check_job", project.id, project.domain, payload_keywords, job_timeout="600")

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


def queue_rank_checks_for_all_projects(db: Session) -> dict:
    projects = db.scalars(select(Project)).all()

    queued_projects = 0
    queued_keywords = 0
    job_ids: list[str] = []

    for project in projects:
        result = queue_rank_check_for_project(db, project.id)
        if not result:
            continue

        queued_projects += 1
        queued_keywords += result["keywordCount"]
        job_ids.append(result["jobId"])

    return {
        "queued": True,
        "projectsQueued": queued_projects,
        "keywordsQueued": queued_keywords,
        "jobIds": job_ids,
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


def queue_labs_metrics_refresh_for_project(db: Session, project_id: str) -> dict | None:
    project = db.scalar(select(Project).where(Project.id == project_id))
    if not project:
        return None

    keywords = db.scalars(select(Keyword).where(Keyword.projectId == project_id)).all()
    if not keywords:
        return None

    queue = get_rank_check_queue()
    payload_keywords = [model_to_dict(keyword) for keyword in keywords]
    job = queue.enqueue(
        "fastapi_app.app.workers.tasks.process_labs_metrics_job",
        project.id,
        payload_keywords,
    )

    return {
        "queued": True,
        "jobId": job.id,
        "projectId": project.id,
        "keywordCount": len(payload_keywords),
    }


def queue_weekly_tracking_for_all_projects(db: Session) -> dict:
    projects = db.scalars(select(Project)).all()

    queued_projects = 0
    rank_jobs = []
    competitor_jobs = []
    labs_jobs = []

    for project in projects:
        rank_result = queue_rank_check_for_project(db, project.id)
        if rank_result:
            queued_projects += 1
            rank_jobs.append(rank_result["jobId"])

        competitor_result = queue_competitor_tracking_for_project(db, project.id)
        if competitor_result:
            competitor_jobs.append(competitor_result["jobId"])

        labs_result = queue_labs_metrics_refresh_for_project(db, project.id)
        if labs_result:
            labs_jobs.append(labs_result["jobId"])

    return {
        "queued": True,
        "projectsQueued": queued_projects,
        "rankJobIds": rank_jobs,
        "competitorJobIds": competitor_jobs,
        "labsJobIds": labs_jobs,
    }