from sqlalchemy.orm import mapped_collection
import logging
import json
import re
from datetime import datetime, timedelta

from sqlalchemy import select, update, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import ProcessingJob, Keyword, RankResult, SerpFeature, User, Project, RefreshJob, TrackedKeyword
from app.services.credit_service import (
    consume_reserved,
    deduct_credits,
    consume_automatic_reserved,
    refund_reserved,
)
from app.services.keyword_update_events import publish_keyword_update
from app.services.dataforseo_client import _build_serp_cache_key, _set_cached_serp, _log_dataforseo_cost
from app.core.config import get_settings
from app.db.session import SessionLocal

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
    cutoff = now
    
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
        local_pack_position = payload.get("local_pack_position")
        local_pack_url = payload.get("local_pack_url")
        has_aio_badge = payload.get("has_aio_badge")
        ai_description = payload.get("ai_description")
        task_id = payload.get("task_id")
        location_code = payload.get("location_code", 2840)
        first_block = payload.get("first_block")
        project_id = payload.get("project_id")
        payload_user_id = payload.get("user_id")
        action = payload.get("action")
        language_code = payload.get("language_code", "en")
        device = payload.get("device", "desktop")
        depth = payload.get("depth", 100)
        
        keyword_query = select(Keyword).where(
            Keyword.keyword == job.keywordText,
            Keyword.location == job.location,
            Keyword.isActive == True,
        )

        if project_id:
            keyword_query = keyword_query.where(
                Keyword.projectId == project_id
            )

        keyword_rows = db.scalars(keyword_query).all()
        
        if not keyword_rows:
            now = datetime.utcnow()

            try:
                skipped_payload = json.loads(job.payload or "{}")
            except Exception:
                skipped_payload = {}

            skipped_payload["skipped"] = True
            skipped_payload["skip_reason"] = "keyword_deleted_or_inactive"
            skipped_payload["skipped_at"] = now.isoformat()

            action = skipped_payload.get("action")
            credit_reference = skipped_payload.get("credit_reference")
            cost_per_keyword = skipped_payload.get("cost_per_keyword")
            payload_user_id = skipped_payload.get("user_id")

            # The keyword was deleted/inactivated before its async result
            # could be applied. Return any still-reserved user credits.
            if (
                action in ("add_keyword", "bulk_add", "manual_refresh", "weekly")
                and payload_user_id
                and credit_reference
                and cost_per_keyword
            ):
                try:
                    refund_reserved(
                        db=db,
                        user_id=payload_user_id,
                        reference=credit_reference,
                        amount=float(cost_per_keyword),
                        description=f"Refund: keyword deleted before {action} completed",
                        project_id=project_id,
                        task_id=task_id,
                    )
                except Exception as refund_exc:
                    logger.warning(
                        "Could not refund reserved credits for skipped ProcessingJob "
                        "job=%s keyword=%s: %s",
                        job.id,
                        job.keywordText,
                        refund_exc,
                    )

            job.payload = json.dumps(skipped_payload)
            job.status = "success"
            job.processingTimeoutAt = None
            job.updatedAt = now

            db.add(job)
            db.commit()

            logger.info(
                "ProcessingJob skipped because keyword was deleted or inactive: "
                "job=%s keyword=%s project=%s",
                job.id,
                job.keywordText,
                project_id,
            )

            return True
        
        if first_block is None:
            now = datetime.utcnow()

            for keyword_row in keyword_rows:
                keyword_row.weeklyRefreshStatus = "failed"
                keyword_row.processingTimeoutAt = None
                keyword_row.updatedAt = now
                db.add(keyword_row)

            job.status = "failed"
            job.processingTimeoutAt = None
            job.updatedAt = now
            db.add(job)
            db.commit()

            logger.warning(
                "ProcessingJob failed because DataForSEO result is missing: "
                "job=%s keyword=%s task_id=%s",
                job.id,
                job.keywordText,
                task_id,
            )

            return False

        now = datetime.utcnow()
        for keyword_row in keyword_rows:
            user_id = keyword_row.project.userId if keyword_row.project else None
            payload_data = json.loads(job.payload or "{}")
            action = payload_data.get("action")
            credit_reference = payload_data.get("credit_reference")
            cost_per_keyword = payload_data.get("cost_per_keyword")

            if user_id:
                try:
                    if action in ("weekly_serp", "monthly_metrics", "automatic"):
                        reference = f"auto:weekly:{job.refreshJobId}:{user_id}" if job.refreshJobId else credit_reference
                        consume_automatic_reserved(
                            db=db,
                            user_id=user_id,
                            reference=reference,
                            amount=settings.plan_config.credit_costs.get("weekly_refresh_per_keyword", cost_per_keyword or 10),
                            description=f"Weekly tracking: {job.keywordText}",
                            project_id=keyword_row.projectId,
                            keyword_id=keyword_row.id,
                            task_id=task_id,
                        )
                    elif action in ("add_keyword", "bulk_add", "manual_refresh", "weekly"):
                        consume_reserved(
                            db=db,
                            user_id=user_id,
                            reference=credit_reference or f"user:{action}:{job.id}:{user_id}",
                            amount=cost_per_keyword or settings.plan_config.credit_costs.get("manual_refresh_per_keyword", 20),
                            action_type="charge",
                            description=f"{action.replace('_', ' ').title()}: {job.keywordText}",
                            project_id=keyword_row.projectId,
                            keyword_id=keyword_row.id,
                            task_id=task_id,
                        )
                    else:
                        if job.refreshJobId:
                            consume_automatic_reserved(
                                db=db,
                                user_id=user_id,
                                reference=f"auto:weekly:{job.refreshJobId}:{user_id}",
                                amount=settings.plan_config.credit_costs.get("weekly_refresh_per_keyword", 10),
                                description=f"Weekly tracking: {job.keywordText}",
                                project_id=keyword_row.projectId,
                                keyword_id=keyword_row.id,
                                task_id=task_id,
                            )
                        else:
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
                    logger.error("Skipping result without credits keyword=%s user=%s: %s", job.keywordText, user_id, credit_exc)
                    continue

            keyword_row.position = position
            keyword_row.check_url = url
            keyword_row.localPackPosition = local_pack_position
            keyword_row.localPackUrl = local_pack_url
            keyword_row.visibility = _dfs_visibility(position)
            keyword_row.ai_badge = has_aio_badge

            if isinstance(ai_description, str):
                ai_description = re.sub(
                    r'\.{3}\s*Read more$',
                    '',
                    ai_description.strip(),
                ) or None

            keyword_row.ai_description = ai_description
            keyword_row.updatedAt = now

            if action in ("weekly_serp", "weekly", "automatic"):
                keyword_row.lastWeeklyRefreshAt = now
                keyword_row.weeklyRefreshStatus = "success"

            keyword_row.processingTimeoutAt = None
            db.add(keyword_row)
            
            rank_result = RankResult(
                projectId=keyword_row.projectId,
                keywordText=job.keywordText,
                position=position,
                url=url,
                device=device,
                location=job.location,
                checkedAt=now,
                keywordId=keyword_row.id,
            )
            db.add(rank_result)
            
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
                task_type=action or "weekly_serp",
                endpoint="/serp/google/organic/task_post",
                method="POST",
                keyword_count=1,
                priority=1,
                depth=depth,
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
                language_code,
                device,
                "unknown",
                depth,
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
                "device": device,
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

        publish_keyword_update(
            user_id=payload_user_id,
            project_id=project_id,
            keyword=job.keywordText,
            status="success",
        )

        return True
        
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to process ProcessingJob {job.id}: {exc}")
        job.status = "failed"
        job.updatedAt = datetime.utcnow()
        db.add(job)
        db.commit()
        return False

def finalize_refresh_jobs(db: Session, refresh_job_ids: set[str]) -> None:
    """
    Finalize parent RefreshJob records once all child ProcessingJobs
    have reached a terminal state.
    """
    if not refresh_job_ids:
        return

    now = datetime.utcnow()

    for refresh_job_id in refresh_job_ids:
        processing_jobs = db.scalars(
            select(ProcessingJob).where(
                ProcessingJob.refreshJobId == refresh_job_id
            )
        ).all()

        if not processing_jobs:
            continue

        active_jobs = [
            job
            for job in processing_jobs
            if job.status in ("pending", "processing", "retry")
        ]

        if active_jobs:
            continue

        success_count = sum(
            1 for job in processing_jobs if job.status == "success"
        )
        failed_count = sum(
            1 for job in processing_jobs if job.status == "failed"
        )

        refresh_job = db.scalar(
            select(RefreshJob).where(
                RefreshJob.id == refresh_job_id
            )
        )

        if not refresh_job:
            continue

        try:
            result_summary = json.loads(
                refresh_job.resultSummary or "{}"
            )
        except Exception:
            result_summary = {}

        result_summary["processed_count"] = success_count
        result_summary["failed_count"] = failed_count

        refresh_job.resultSummary = json.dumps(result_summary)
        refresh_job.completedAt = now

        if failed_count == len(processing_jobs):
            refresh_job.status = "failed"
        else:
            refresh_job.status = "success"

        db.add(refresh_job)

    db.commit()

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
    refresh_job_ids = set()

    for job in claimed_jobs:
        refresh_job_ids.add(job.refreshJobId)

        if process_processing_job(db, job):
            processed += 1
        else:
            failed += 1

    finalize_refresh_jobs(db, refresh_job_ids)

    return {
        "status": "completed",
        "processed": processed,
        "failed": failed,
    }


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
