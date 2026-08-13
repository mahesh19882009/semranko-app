import logging
import json
import re
from datetime import datetime, timedelta

from sqlalchemy import select, update, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import ProcessingJob, Keyword, RankResult, SerpFeature, User, Project, RefreshJob, TrackedKeyword
from app.services.credit_service import consume_reserved, deduct_credits
from app.services.dataforseo_client import _build_serp_cache_key, _set_cached_serp, _log_dataforseo_cost
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PROCESSING_BATCH_SIZE = 50
PROCESSING_TIMEOUT_HOURS = 1


def _dfs_visibility(position):
    if position is None or position > 100:
        return 0.0
    if 1 <= position <= 10:
        return round(1.0 - (position - 1) * 0.1, 2)
    if 11 <= position <= 20:
        return 0.05
    return 0.0


def claim_processing_jobs(db: Session, batch_size: int = PROCESSING_BATCH_SIZE) -> list[ProcessingJob]:
    """
    Atomically claim a batch of pending ProcessingJobs.
    Returns the claimed jobs, or empty list if none available.
    """
    jobs = db.scalars(
        select(ProcessingJob)
        .where(ProcessingJob.status.in_(["pending", "retry"]))
        .order_by(ProcessingJob.createdAt.asc())
        .limit(batch_size)
    ).all()
    
    if not jobs:
        return []
    
    job_ids = [job.id for job in jobs]
    result = db.execute(
        update(ProcessingJob)
        .where(ProcessingJob.id.in_(job_ids))
        .where(ProcessingJob.status.in_(["pending", "retry"]))
        .values(
            status="processing",
            attempts=ProcessingJob.attempts + 1,
            processingTimeoutAt=datetime.utcnow() + timedelta(hours=PROCESSING_TIMEOUT_HOURS),
            updatedAt=datetime.utcnow(),
        )
    ).rowcount
    
    if result == len(jobs):
        db.commit()
        return jobs
    
    db.rollback()
    return []


def recover_stale_processing_jobs(db: Session, timeout_hours: int = PROCESSING_TIMEOUT_HOURS) -> dict:
    """
    Recovery logic for stale ProcessingJobs stuck in 'processing' status.
    Uses atomic state transition to prevent duplicate recovery.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=timeout_hours)
    
    result = db.execute(
        update(ProcessingJob)
        .where(
            ProcessingJob.status == "processing",
            ProcessingJob.processingTimeoutAt != None,
            ProcessingJob.processingTimeoutAt <= cutoff,
            ProcessingJob.retryCount < ProcessingJob.maxRetries,
        )
        .values(
            status="retry",
            retryCount=ProcessingJob.retryCount + 1,
            updatedAt=now,
        )
        .returning(ProcessingJob.id)
    )
    
    recovered_ids = [row[0] for row in result.fetchall()]
    if recovered_ids:
        db.commit()
        logger.info(f"Recovered {len(recovered_ids)} stale ProcessingJobs for retry: {recovered_ids}")
    
    failed_result = db.execute(
        update(ProcessingJob)
        .where(
            ProcessingJob.status == "processing",
            ProcessingJob.processingTimeoutAt != None,
            ProcessingJob.processingTimeoutAt <= cutoff,
            ProcessingJob.retryCount >= ProcessingJob.maxRetries,
        )
        .values(
            status="failed",
            updatedAt=now,
        )
        .returning(ProcessingJob.id)
    )
    
    failed_ids = [row[0] for row in failed_result.fetchall()]
    if failed_ids:
        db.commit()
        logger.info(f"Marked {len(failed_ids)} ProcessingJobs as failed (max retries exceeded): {failed_ids}")
    
    return {"recovered": len(recovered_ids), "failed": len(failed_ids)}


def process_processing_job(db: Session, job: ProcessingJob) -> bool:
    """
    Process a single ProcessingJob.
    Returns True on success, False on failure.
    """
    if job.status == "success":
        return True
    
    try:
        payload = json.loads(job.payload or "{}")
        position = payload.get("position")
        url = payload.get("url")
        has_aio_badge = payload.get("has_aio_badge")
        ai_description = payload.get("ai_description")
        task_id = payload.get("task_id")
        location_code = payload.get("location_code", 2840)
        first_block = payload.get("first_block")
        
        keyword_rows = db.scalars(
            select(Keyword).where(
                Keyword.keyword == job.keywordText,
                Keyword.location == job.location,
                Keyword.isActive == True,
            )
        ).all()
        
        if not keyword_rows:
            job.status = "failed"
            job.updatedAt = datetime.utcnow()
            db.add(job)
            db.commit()
            return False
        
        now = datetime.utcnow()
        for keyword_row in keyword_rows:
            keyword_row.position = position
            keyword_row.visibility = _dfs_visibility(position)
            keyword_row.ai_badge = has_aio_badge
            if isinstance(ai_description, str):
                ai_description = re.sub(r'\.{3}\s*Read more$', '', ai_description.strip()) or None
            keyword_row.ai_description = ai_description
            keyword_row.updatedAt = now
            keyword_row.lastWeeklyRefreshAt = now
            keyword_row.weeklyRefreshStatus = "success"
            keyword_row.processingTimeoutAt = None
            db.add(keyword_row)
            
            rank_result = RankResult(
                projectId=keyword_row.projectId,
                keywordText=job.keywordText,
                position=position,
                url=url,
                device="desktop",
                location=job.location,
                checkedAt=now,
                keywordId=keyword_row.id,
            )
            db.add(rank_result)
            
            user_id = keyword_row.project.userId if keyword_row.project else None
            if user_id:
                user = db.scalar(select(User).where(User.id == user_id))
                if user and user.subscriptionStatus == "active":
                    try:
                        cost = settings.plan_config.credit_costs.get("weekly_refresh_per_keyword", 10)
                        deduct_credits(
                            db=db,
                            user_id=user_id,
                            amount=cost,
                            action_type="charge",
                            description=f"Weekly tracking: {job.keywordText}",
                            project_id=keyword_row.projectId,
                            keyword_id=keyword_row.id,
                            task_id=task_id,
                        )
                    except Exception as credit_exc:
                        logger.error(f"Worker credit deduction failed for keyword={job.keywordText} user={user_id}: {credit_exc}")
            
            tracked_aio = db.scalar(
                select(TrackedKeyword).where(
                    TrackedKeyword.userId == user_id,
                    TrackedKeyword.keyword == job.keywordText,
                    TrackedKeyword.isActive == True,
                    TrackedKeyword.trackAio == True,
                )
            )
            expand_ai_overview = tracked_aio is not None
            
            _log_dataforseo_cost(
                db=db,
                user_id=user_id,
                task_type="weekly_serp",
                endpoint="/serp/google/organic/task_post",
                method="POST",
                keyword_count=1,
                priority=1,
                depth=10,
                expand_ai_overview=expand_ai_overview,
                cache_hit=False,
                success=True,
                project_id=keyword_row.projectId,
                keyword_id=keyword_row.id,
                task_id=task_id,
            )
            
            cache_key = _build_serp_cache_key(
                job.keywordText,
                location_code,
                "en",
                "desktop",
                "unknown",
                10,
                expand_ai_overview,
            )
            organic_items = [i for i in (first_block.get("items", []) or []) if i.get("type") == "organic"] if first_block else []
            cited_domains = {}
            if first_block:
                for item in (first_block.get("items", []) or []):
                    if item.get("type") == "ai_overview":
                        for ref in (item.get("ai_overview_reference", []) or item.get("references", []) or []):
                            d = ref.get("domain") or ref.get("source_domain") or ref.get("url")
                            if d:
                                cited_domains[d] = cited_domains.get(d, 0) + 1
            _set_cached_serp(cache_key, {
                "keyword": job.keywordText,
                "location": job.location,
                "device": "desktop",
                "items": first_block.get("items", []) or [] if first_block else [],
                "organic_items": organic_items,
                "featured_snippet": None,
                "people_also_ask": [],
                "ai_overview": None,
                "ai_answer": None,
                "cited_domains": cited_domains,
            }, ttl=86400)
        
        job.status = "success"
        job.updatedAt = datetime.utcnow()
        db.add(job)
        db.commit()
        return True
        
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to process ProcessingJob {job.id}: {exc}")
        job.status = "failed"
        job.updatedAt = datetime.utcnow()
        db.add(job)
        db.commit()
        return False


def process_pending_processing_jobs(db: Session) -> dict:
    """
    Process pending ProcessingJob records in bounded batches.
    Uses atomic claim to prevent duplicate processing.
    """
    claimed_jobs = claim_processing_jobs(db, PROCESSING_BATCH_SIZE)
    
    if not claimed_jobs:
        return {"status": "completed", "processed": 0, "failed": 0}
    
    processed = 0
    failed = 0
    
    for job in claimed_jobs:
        if process_processing_job(db, job):
            processed += 1
        else:
            failed += 1
    
    return {"status": "completed", "processed": processed, "failed": failed}


def run_refresh_worker() -> dict:
    """
    Main entry point for refresh worker.
    Processes pending ProcessingJobs.
    """
    db = SessionLocal()
    try:
        result = process_pending_processing_jobs(db)
        return result
    except Exception as exc:
        logger.exception(f"Refresh worker failed: {exc}")
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()
