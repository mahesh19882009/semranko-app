"""
Queue-Based Refresh Architecture for Weekly/Monthly Rank Tracking

This service handles scheduled refresh with:
1. Keyset-paginated eligibility collection (5K batches)
2. RefreshJob records for bounded internal batching
3. Atomic job claiming and state transitions
4. DataForSEO submission respecting official limits
5. Processing timeout/recovery with duplicate protection
6. Retry support
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import requests
from fastapi import HTTPException
from sqlalchemy import select, func, update, or_, text
from sqlalchemy.orm import Session

from app.db.models import (
    AsyncTaskQueue, 
    Keyword, 
    Project, 
    User, 
    RankResult, 
    Competitor,
    CompetitorRank,
    RefreshJob,
    ProcessingJob,
    TrackedKeyword,
    CreditLedger,
)
from app.core.config import get_settings
from app.services.credit_service import deduct_credits, reserve_credits, consume_reserved, refund_reserved

logger = logging.getLogger(__name__)
settings = get_settings()

# DataForSEO async endpoint allows up to 100 tasks per POST request.
# See: https://docs.dataforseo.com/v3/serp/google/organic/task_post/
ASYNC_BULK_MAX_TASKS = 100

# Internal application batch size for RefreshJob records.
# Independent from DataForSEO request limits.
REFRESH_JOB_BATCH_SIZE = 5000

# Processing timeout: if a job is not completed within this time,
# it becomes eligible for retry.
PROCESSING_TIMEOUT_HOURS = 24


def _paginate_eligible_keywords(db: Session, job_type: str = "weekly") -> list[list[dict]]:
    """
    Keyset-paginated collection of eligible keywords.
    
    Returns a list of batches, where each batch contains up to REFRESH_JOB_BATCH_SIZE
    deduplicated keyword dicts.
    
    Weekly eligibility:
    - Keyword is active
    - User subscription is active
    - Keyword.lastWeeklyRefreshAt is NULL or >= 6 days ago
    - Keyword.weeklyRefreshStatus is not "processing" (or timeout expired)
    
    Monthly eligibility:
    - Keyword is active
    - User subscription is active
    - Keyword.lastMonthlyMetricsRefreshAt is NULL or >= 14 days ago
    - User.refreshFrequency is monthly or None
    """
    now = datetime.utcnow()
    batches = []
    last_id = None
    
    while True:
        query = (
            select(Keyword)
            .join(Project, Project.id == Keyword.projectId)
            .join(User, User.id == Project.userId)
            .where(Keyword.isActive == True)
            .order_by(Keyword.id.asc())
        )
        
        if job_type == "weekly":
            cutoff = now - timedelta(days=6)
            query = query.where(
                User.subscriptionStatus == "active",
                (Keyword.lastWeeklyRefreshAt == None) | (Keyword.lastWeeklyRefreshAt <= cutoff),
                (Keyword.weeklyRefreshStatus == None) |
                (Keyword.weeklyRefreshStatus != "processing") |
                ((Keyword.processingTimeoutAt != None) & (Keyword.processingTimeoutAt <= now)),
            )
        elif job_type == "monthly":
            cutoff = now - timedelta(days=14)
            query = query.where(
                User.subscriptionStatus == "active",
                User.refreshFrequency.in_(["monthly", None, ""]),
                (Keyword.lastMonthlyMetricsRefreshAt == None) | (Keyword.lastMonthlyMetricsRefreshAt <= cutoff),
            )
        else:
            break
        
        if last_id is not None:
            query = query.where(Keyword.id > last_id)
        
        query = query.limit(REFRESH_JOB_BATCH_SIZE)
        batch = db.scalars(query).all()
        
        if not batch:
            break
        
        keyword_map = {}
        for kw in batch:
            key = (kw.keyword.lower().strip(), kw.location or "India")
            if key not in keyword_map:
                keyword_map[key] = []
            keyword_map[key].append(kw)
        
        unique_keywords = [
            {"keyword": key[0], "location": key[1]}
            for key in keyword_map.keys()
        ]
        
        if unique_keywords:
            batches.append(unique_keywords)
        
        last_id = batch[-1].id
        
        if len(batch) < REFRESH_JOB_BATCH_SIZE:
            break
    
    return batches


def create_refresh_jobs(db: Session, job_type: str, keyword_batches: list[list[dict]]) -> list[RefreshJob]:
    """
    Create RefreshJob records for each keyword batch.
    """
    jobs = []
    total_batches = len(keyword_batches)
    
    for index, keywords in enumerate(keyword_batches):
        job = RefreshJob(
            jobType=job_type,
            status="queued",
            batchIndex=index,
            totalBatches=total_batches,
            keywordCount=len(keywords),
            keywordsJson=json.dumps(keywords),
        )
        db.add(job)
        jobs.append(job)
    
    db.commit()
    for job in jobs:
        db.refresh(job)
    
    logger.info(
        f"Created {len(jobs)} RefreshJob(s) for {job_type} "
        f"with {sum(j.keywordCount for j in jobs)} total keywords"
    )
    return jobs


def create_async_bulk_task(
    db: Session,
    keywords: list[dict],
    task_type: str = "rank_tracking",
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    domain: Optional[str] = None,
) -> AsyncTaskQueue:
    """
    Create an async task queue entry for bulk processing.
    Kept for backward compatibility with existing code paths.
    """
    task = AsyncTaskQueue(
        taskType=task_type,
        status="pending",
        keywordsJson=json.dumps(keywords),
        userId=user_id,
        projectId=project_id,
        locationCode=2840,
        device="desktop",
        domain=domain,
    )
    db.add(task)
    db.flush()
    db.refresh(task)
    
    logger.info(f"Created async task {task.id} for {len(keywords)} keywords")
    return task


def claim_refresh_job(db: Session, job_id: str) -> Optional[RefreshJob]:
    """
    Atomically claim a RefreshJob for processing.
    Returns the job if claimed, None if already claimed by another worker.
    """
    now = datetime.utcnow()
    result = db.execute(
        update(RefreshJob)
        .where(RefreshJob.id == job_id)
        .where(RefreshJob.status == "queued")
        .values(
            status="processing",
            updatedAt=now,
        )
        .returning(RefreshJob.id)
    ).fetchone()
    
    if result:
        db.commit()
        return db.scalar(select(RefreshJob).where(RefreshJob.id == job_id))
    return None


def mark_keywords_processing_atomic(db: Session, keyword_texts: list[str], location: str = "India") -> int:
    """
    Atomically mark keywords as processing.
    Returns the number of keywords successfully marked.
    """
    now = datetime.utcnow()
    timeout_at = now + timedelta(hours=PROCESSING_TIMEOUT_HOURS)
    
    result = db.execute(
        update(Keyword)
        .where(
            Keyword.keyword.in_(keyword_texts),
            Keyword.location == location,
            Keyword.isActive == True,
            (
                (Keyword.weeklyRefreshStatus == None) |
                (Keyword.weeklyRefreshStatus != "processing") |
                ((Keyword.processingTimeoutAt != None) & (Keyword.processingTimeoutAt <= now))
            ),
        )
        .values(
            weeklyRefreshStatus="processing",
            processingTimeoutAt=timeout_at,
            updatedAt=now,
        )
    )
    
    affected = result.rowcount
    db.commit()
    return affected


def submit_refresh_job_to_dataforseo(db: Session, job: RefreshJob) -> bool:
    """
    Submit a RefreshJob to DataForSEO.
    Weekly: async task_post, max 100 tasks per request.
    Monthly: sync labs endpoint, max 700 keywords per request.
    """
    if job.status not in ("queued", "processing", "retry"):
        logger.warning(f"RefreshJob {job.id} is not eligible for submission, status={job.status}")
        return False
    
    keywords = json.loads(job.keywordsJson or "[]")
    if not keywords:
        job.status = "failed"
        job.errorMessage = "No keywords in job"
        job.completedAt = datetime.utcnow()
        db.add(job)
        db.commit()
        return False
    
    keyword_texts = [kw.get("keyword") for kw in keywords if kw.get("keyword")]
    if not keyword_texts:
        job.status = "failed"
        job.errorMessage = "No valid keywords in job"
        job.completedAt = datetime.utcnow()
        db.add(job)
        db.commit()
        return False
    
    if job.status not in ("processing", "submitted", "retry"):
        logger.warning(f"RefreshJob {job.id} is not in a submit-able state, status={job.status}")
        return False
    
    location = keywords[0].get("location", "India") if keywords else "India"
    
    try:
        if job.jobType == "weekly_serp":
            return _submit_weekly_refresh(db, job, keyword_texts)
        elif job.jobType == "monthly_metrics":
            return _submit_monthly_refresh(db, job, keyword_texts)
        else:
            job.status = "failed"
            job.errorMessage = f"Unknown job type: {job.jobType}"
            job.completedAt = datetime.utcnow()
            db.add(job)
            db.commit()
            return False
    except Exception as exc:
        logger.error(f"Failed to submit RefreshJob {job.id}: {exc}")
        job.status = "failed"
        job.errorMessage = str(exc)
        job.completedAt = datetime.utcnow()
        db.add(job)
        db.commit()
        return False


def _submit_weekly_refresh(db: Session, job: RefreshJob, keyword_texts: list[str]) -> bool:
    """
    Submit weekly SERP refresh to DataForSEO async endpoint.
    """
    location_code = 2840
    pingback_url = f"{settings.FRONTEND_URL}/api/webhooks/dataforseo"
    if settings.DATAFORSEO_WEBHOOK_SECRET:
        pingback_url = f"{pingback_url}?secret={settings.DATAFORSEO_WEBHOOK_SECRET}"
    
    aio_keyword_texts = set(
        row.keyword
        for row in db.scalars(
            select(TrackedKeyword).where(
                TrackedKeyword.isActive == True,
                TrackedKeyword.trackAio == True,
                TrackedKeyword.keyword.in_(keyword_texts),
            )
        ).all()
    )
    
    uncached_keywords = []
    cached_count = 0
    for kw in keyword_texts:
        aio_flag = kw in aio_keyword_texts
        from app.services.dataforseo_client import _build_serp_cache_key, _get_cached_serp
        cache_key = _build_serp_cache_key(kw, location_code, "en", "desktop", "unknown", 10, aio_flag)
        if _get_cached_serp(cache_key):
            cached_count += 1
        else:
            uncached_keywords.append(kw)
    
    if cached_count > 0:
        logger.info(f"RefreshJob {job.id}: {cached_count} keywords cached, {len(uncached_keywords)} need DFS")
    
    if not uncached_keywords:
        job.status = "success"
        job.completedAt = datetime.utcnow()
        job.resultSummary = json.dumps({"cached_count": cached_count, "skipped": True})
        db.add(job)
        db.commit()
        
        from app.db.models import Project
        for kw_text in keyword_texts:
            kw = db.scalar(
                select(Keyword).where(
                    Keyword.keyword == kw_text,
                    Keyword.location == "India",
                    Keyword.isActive == True,
                )
            )
            if kw:
                project = db.scalar(select(Project).where(Project.id == kw.projectId))
                if project:
                    user_id = project.userId
                    user = db.scalar(select(User).where(User.id == user_id))
                    if user and user.subscriptionStatus == "active":
                        cache_hit_ref = f"cache_hit:{job.id}:{kw.id}"
                        existing_charge = db.scalar(
                            select(CreditLedger).where(
                                CreditLedger.description.like(f"%{cache_hit_ref}%"),
                                CreditLedger.userId == user_id,
                                CreditLedger.actionType == "charge",
                                CreditLedger.status == "completed",
                            )
                        )
                        if not existing_charge:
                            try:
                                cost = settings.plan_config.credit_costs.get("weekly_refresh_per_keyword", 10)
                                deduct_credits(
                                    db=db,
                                    user_id=user_id,
                                    amount=cost,
                                    action_type="charge",
                                    description=f"Weekly tracking (cache hit): {kw_text} [{cache_hit_ref}]",
                                    project_id=kw.projectId,
                                    keyword_id=kw.id,
                                )
                            except Exception as credit_exc:
                                logger.error(f"Cache-hit credit deduction failed for keyword={kw_text} user={user_id}: {credit_exc}")
        
        db.commit()
        return True
    
    from app.services.dataforseo_client import check_dfs_cost_ceiling
    from app.db.models import Keyword as KwModel
    
    keyword_user_map = {}
    for kw_text in uncached_keywords:
        matching = db.scalars(
            select(KwModel).where(
                KwModel.keyword == kw_text,
                KwModel.location == "India",
                KwModel.isActive == True,
            )
        ).all()
        for kw in matching:
            keyword_user_map.setdefault(kw.userId, []).append(kw_text)
    
    excluded_users = set()
    cost_per_keyword = 0.006
    for user_id, user_keywords in keyword_user_map.items():
        estimated_cost = len(user_keywords) * cost_per_keyword
        try:
            check_dfs_cost_ceiling(db, user_id, estimated_cost)
        except HTTPException:
            excluded_users.add(user_id)
    
    if excluded_users:
        uncached_keywords = [
            kw_text for kw_text in uncached_keywords
            if not any(
                kw_text in keyword_user_map.get(uid, [])
                for uid in excluded_users
            )
        ]
        logger.info(f"RefreshJob {job.id}: excluded {len(excluded_users)} users due to DFS cost ceiling")
    
    if not uncached_keywords:
        job.status = "success"
        job.completedAt = datetime.utcnow()
        job.resultSummary = json.dumps({"cached_count": cached_count, "skipped": True, "ceiling_excluded": True})
        db.add(job)
        db.commit()
        return True
    
    chunks = [
        uncached_keywords[i:i + ASYNC_BULK_MAX_TASKS]
        for i in range(0, len(uncached_keywords), ASYNC_BULK_MAX_TASKS)
    ]
    
    auth = (settings.effective_serp_login, settings.effective_serp_key)
    all_task_ids = []
    failed_chunks = 0
    
    for chunk in chunks:
        serp_payload = []
        for kw in chunk:
            task_payload = {
                "keyword": kw,
                "location_code": location_code,
                "language_code": "en",
                "device": "desktop",
                "depth": 10,
                "pingback_url": pingback_url,
                "priority": 1,
                "expand_ai_overview": kw in aio_keyword_texts,
            }
            serp_payload.append(task_payload)
        
        post_res = requests.post(
            "https://api.dataforseo.com/v3/serp/google/organic/task_post",
            json=serp_payload,
            auth=auth,
            timeout=60,
        )
        
        if "application/json" not in post_res.headers.get("Content-Type", ""):
            logger.error(f"DataForSEO task_post error for RefreshJob {job.id} chunk: {post_res.text[:500]}")
            failed_chunks += 1
            continue
        
        post_response = post_res.json()
        chunk_task_ids = []
        if "tasks" in post_response and post_response["tasks"]:
            for t in post_response["tasks"]:
                if t.get("id"):
                    chunk_task_ids.append(t["id"])
        
        all_task_ids.extend(chunk_task_ids)
    
    if not all_task_ids:
        job.status = "failed"
        job.errorMessage = "No task IDs returned from DataForSEO"
        job.completedAt = datetime.utcnow()
        db.add(job)
        db.commit()
        return False
    
    # Store task IDs and mark as submitted
    existing_ids = json.loads(job.dataforseoRequestIds or "[]")
    existing_ids.extend(all_task_ids)
    job.dataforseoRequestIds = json.dumps(existing_ids)
    job.status = "submitted"
    job.processingTimeoutAt = datetime.utcnow() + timedelta(hours=PROCESSING_TIMEOUT_HOURS)
    db.add(job)
    db.commit()
    
    from app.services.dataforseo_client import _log_dataforseo_cost
    for dfs_task_id in all_task_ids:
        _log_dataforseo_cost(
            db=db,
            user_id=None,
            task_type="weekly_serp",
            endpoint="/serp/google/organic/task_post",
            method="POST",
            keyword_count=len(uncached_keywords),
            priority=1,
            depth=10,
            expand_ai_overview=True,
            cache_hit=False,
            success=True,
            task_id=dfs_task_id,
        )
    
    if failed_chunks > 0:
        logger.warning(
            f"RefreshJob {job.id}: submitted {len(all_task_ids)} tasks across "
            f"{len(chunks)} chunks, {failed_chunks} chunks failed"
        )
    else:
        logger.info(f"RefreshJob {job.id}: submitted {len(all_task_ids)} task(s) across {len(chunks)} chunk(s)")
    
    return True


def _submit_monthly_refresh(db: Session, job: RefreshJob, keyword_texts: list[str]) -> bool:
    """
    Submit monthly metrics refresh to DataForSEO Labs endpoint.
    """
    from app.services.dataforseo_client import _build_kw_metrics_cache_key, _get_cached_kw_metrics, _log_dataforseo_cost
    from app.db.models import Keyword, Project, User
    
    location_code = 2840
    results = {}
    missing_keywords = []
    cached_keywords = []
    
    for kw in keyword_texts:
        cache_key = _build_kw_metrics_cache_key(kw, location_code, "en")
        cached = _get_cached_kw_metrics(cache_key)
        if cached:
            results[kw] = cached
            cached_keywords.append(kw)
        else:
            missing_keywords.append(kw)
    
    if not missing_keywords:
        job.status = "success"
        job.completedAt = datetime.utcnow()
        job.resultSummary = json.dumps({
            "results": results,
            "results_count": len(results),
            "chunks_processed": 0,
            "skipped": True,
        })
        db.add(job)
        db.commit()
        
        monthly_cost = settings.plan_config.credit_costs.get("monthly_refresh_per_keyword", 10)
        for kw_text in cached_keywords:
            kw = db.scalar(
                select(Keyword).where(
                    Keyword.keyword == kw_text,
                    Keyword.location == "India",
                    Keyword.isActive == True,
                )
            )
            if kw:
                project = db.scalar(select(Project).where(Project.id == kw.projectId))
                if project:
                    user_id = project.userId
                    user = db.scalar(select(User).where(User.id == user_id))
                    if user and user.subscriptionStatus == "active":
                        cache_hit_ref = f"cache_hit_monthly:{job.id}:{kw.id}"
                        existing_charge = db.scalar(
                            select(CreditLedger).where(
                                CreditLedger.description.like(f"%{cache_hit_ref}%"),
                                CreditLedger.userId == user_id,
                                CreditLedger.actionType == "charge",
                                CreditLedger.status == "completed",
                            )
                        )
                        if not existing_charge:
                            try:
                                deduct_credits(
                                    db=db,
                                    user_id=user_id,
                                    amount=monthly_cost,
                                    action_type="charge",
                                    description=f"Monthly metrics (cache hit): {kw_text} [{cache_hit_ref}]",
                                    project_id=kw.projectId,
                                    keyword_id=kw.id,
                                )
                            except Exception as credit_exc:
                                logger.error(f"Monthly cache-hit credit deduction failed for keyword={kw_text} user={user_id}: {credit_exc}")
        
        db.commit()
        return True
    
    from app.services.dataforseo_client import check_dfs_cost_ceiling
    
    keyword_user_map = {}
    for kw_text in missing_keywords:
        matching = db.scalars(
            select(Keyword).where(
                Keyword.keyword == kw_text,
                Keyword.location == "India",
                Keyword.isActive == True,
            )
        ).all()
        for kw in matching:
            keyword_user_map.setdefault(kw.userId, []).append(kw_text)
    
    excluded_users = set()
    cost_per_keyword = 0.013
    for user_id, user_keywords in keyword_user_map.items():
        estimated_cost = len(user_keywords) * cost_per_keyword
        try:
            check_dfs_cost_ceiling(db, user_id, estimated_cost)
        except HTTPException:
            excluded_users.add(user_id)
    
    if excluded_users:
        missing_keywords = [
            kw_text for kw_text in missing_keywords
            if not any(
                kw_text in keyword_user_map.get(uid, [])
                for uid in excluded_users
            )
        ]
        logger.info(f"Monthly RefreshJob {job.id}: excluded {len(excluded_users)} users due to DFS cost ceiling")
    
    if not missing_keywords:
        job.status = "success"
        job.completedAt = datetime.utcnow()
        job.resultSummary = json.dumps({
            "results": results,
            "results_count": len(results),
            "chunks_processed": 0,
            "skipped": True,
        })
        db.add(job)
        db.commit()
        return True
    
    chunks = [
        missing_keywords[i:i + 700]
        for i in range(0, len(missing_keywords), 700)
    ]
    
    url = f"{getattr(settings, 'DATAFORSEO_BASE_URL', None) or 'https://api.dataforseo.com/v3'}/dataforseo_labs/google/keyword_overview/live"
    
    for chunk in chunks:
        payload = [
            {
                "keywords": chunk,
                "language_code": "en",
                "item_types": ["organic", "paid", "ai_overview_reference"],
            }
        ]
        
        response = requests.post(
            url,
            json=payload,
            auth=(settings.effective_serp_login, settings.effective_serp_key),
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        
        tasks = data.get("tasks", []) or []
        for task in tasks:
            result = task.get("result")
            if not result:
                continue
            if isinstance(result, list) and result:
                result = result[0]
            if not isinstance(result, dict):
                continue
            
            items = result.get("items") or []
            if not isinstance(items, list) or not items:
                continue
            
            item = items[0]
            keyword_properties = item.get("keyword_properties", {}) or {}
            keyword_info = item.get("keyword_info", {}) or {}
            avg_backlinks_info = item.get("avg_backlinks_info", {}) or {}
            search_intent_info = item.get("search_intent_info", {}) or {}
            
            kw = item.get("keyword") or (task.get("data") or {}).get("keyword")
            if not kw:
                continue
            kw = kw.lower().strip()
            
            metric_entry = {
                "volume": keyword_info.get("search_volume"),
                "kd": keyword_properties.get("keyword_difficulty"),
                "cpc": keyword_info.get("cpc"),
                "competition": keyword_info.get("competition"),
                "backlinks": avg_backlinks_info.get("backlinks"),
                "referring_domains": avg_backlinks_info.get("referring_domains"),
                "intent": search_intent_info.get("main_intent"),
            }
            results[kw] = metric_entry
            
            cache_key = _build_kw_metrics_cache_key(kw, location_code, "en")
            from app.services.dataforseo_client import _set_cached_kw_metrics
            _set_cached_kw_metrics(cache_key, metric_entry, ttl=604800)
            
            _log_dataforseo_cost(
                db=db,
                user_id=None,
                task_type="monthly_metrics",
                endpoint="/dataforseo_labs/google/keyword_overview/live",
                method="POST",
                keyword_count=1,
                priority=1,
                depth=100,
                expand_ai_overview=True,
                cache_hit=False,
                success=True,
            )
    
    job.status = "success"
    job.completedAt = datetime.utcnow()
    job.resultSummary = json.dumps({
        "results": results,
        "results_count": len(results),
        "chunks_processed": len(chunks),
    })
    db.add(job)
    db.commit()
    return True


def process_completed_async_task(
    db: Session,
    task: AsyncTaskQueue,
    serp_results: dict,
) -> None:
    """
    Process completed async task results and update all relevant tables.
    Updates RankResult, Keyword.position, Keyword.visibility, Keyword.ai_badge.
    Consumes reserved credits for eligible users.
    """
    try:
        keywords = json.loads(task.keywordsJson or "[]")
        keyword_entries = []
        for kw_entry in keywords:
            keyword_text = kw_entry.get("keyword", "").lower().strip()
            location = kw_entry.get("location", "India")
            keyword_entries.append((keyword_text, location))
        
        keyword_map = {}
        BATCH_SIZE = 20
        for i in range(0, len(keyword_entries), BATCH_SIZE):
            batch = keyword_entries[i:i + BATCH_SIZE]
            conditions = []
            for kw_text, location in batch:
                conditions.append(
                    (Keyword.keyword == kw_text) &
                    (Keyword.location == location) &
                    (Keyword.isActive == True)
                )
            
            if conditions:
                matching_keywords = db.scalars(
                    select(Keyword).where(or_(*conditions))
                ).all()
                
                for kw_obj in matching_keywords:
                    key = (kw_obj.keyword.lower().strip(), kw_obj.location or "India")
                    if key not in keyword_map:
                        keyword_map[key] = []
                    keyword_map[key].append(kw_obj)
        
        now = datetime.utcnow()
        updated_count = 0
        credit_failures = []
        
        for keyword_text, serp_data in serp_results.items():
            location = serp_data.get("location", "India")
            key = (keyword_text.lower().strip(), location)
            
            organic_items = serp_data.get("organic_items", [])
            position = None
            url = None
            has_aio_badge = None
            
            if task.domain:
                for item in organic_items:
                    item_domain = item.get("domain", "")
                    if task.domain.lower() in item_domain.lower():
                        position = item.get("rank_group") or item.get("rank_absolute")
                        url = item.get("url")
                        break
            
            ai_overview_items = [i for i in serp_data.get("items", []) if i.get("type") == "ai_overview"]
            if ai_overview_items:
                has_aio_badge = "AIO"
            
            if key in keyword_map:
                for kw_obj in keyword_map[key]:
                    try:
                        rank_result = RankResult(
                            projectId=kw_obj.projectId,
                            keywordText=keyword_text,
                            position=position,
                            url=url,
                            device=task.device or "desktop",
                            location=location,
                            checkedAt=now,
                            keywordId=kw_obj.id
                        )
                        db.add(rank_result)
                        
                        kw_obj.position = position
                        kw_obj.visibility = _dfs_visibility(position)
                        kw_obj.ai_badge = has_aio_badge
                        kw_obj.updatedAt = now
                        kw_obj.lastWeeklyRefreshAt = now
                        kw_obj.weeklyRefreshStatus = "success"
                        kw_obj.processingTimeoutAt = None
                        db.add(kw_obj)
                        
                        updated_count += 1
                        
                        try:
                            user_id = kw_obj.project.userId if kw_obj.project else task.userId
                            reference = f"bulk:{task.id}:{user_id}"
                            consume_reserved(
                                db=db,
                                user_id=user_id,
                                reference=reference,
                                amount=settings.plan_config.credit_costs.get("weekly_refresh_per_keyword", 10),
                                action_type="charge",
                                description=f"Weekly tracking: {keyword_text}",
                                project_id=kw_obj.projectId,
                                keyword_id=kw_obj.id,
                            )
                        except Exception as credit_exc:
                            logger.error(f"Failed to consume reserved credits for keyword {keyword_text}: {credit_exc}")
                            credit_failures.append({
                                "keyword": keyword_text,
                                "user_id": kw_obj.project.userId if kw_obj.project else task.userId,
                                "error": str(credit_exc),
                            })
                    except Exception as e:
                        logger.error(f"Failed to update keyword {keyword_text} for user: {e}")
                        continue
        
        task.status = "completed"
        task.completedAt = now
        task.resultJson = json.dumps({
            "updated_count": updated_count,
            "credit_failures": credit_failures,
        })
        db.add(task)
        db.commit()
        
        logger.info(
            f"Processed task {task.id}: updated {updated_count} rank results, {len(credit_failures)} credit failures"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to process task {task.id}: {e}")
        task.status = "failed"
        task.errorMessage = str(e)
        db.add(task)
        db.commit()
        raise


def _dfs_visibility(position):
    if position is None or position > 100:
        return 0.0
    if 1 <= position <= 10:
        return round(1.0 - (position - 1) * 0.1, 2)
    if 11 <= position <= 20:
        return 0.05
    return 0.0


def run_weekly_bulk_update_job(db: Session) -> dict:
    """
    Main entry point for the weekly bulk update job.
    Runs every Sunday night to refresh all active tracked keywords.
    Uses keyset pagination and RefreshJob records.
    """
    logger.info("Starting weekly bulk update job")
    
    try:
        keyword_batches = _paginate_eligible_keywords(db, job_type="weekly")
        
        if not keyword_batches:
            logger.info("No eligible keywords found for bulk update")
            return {
                "status": "completed",
                "keywords_processed": 0,
                "tasks_created": 0
            }
        
        jobs = create_refresh_jobs(db, "weekly_serp", keyword_batches)
        
        logger.info(
            f"Weekly bulk update job completed: "
            f"{len(jobs)} RefreshJobs created for {sum(j.keywordCount for j in jobs)} keywords"
        )
        
        return {
            "status": "queued",
            "keywords_processed": sum(j.keywordCount for j in jobs),
            "tasks_created": len(jobs),
            "job_ids": [j.id for j in jobs]
        }
        
    except Exception as e:
        logger.exception(f"Weekly bulk update job failed: {e}")
        db.rollback()
        return {
            "status": "failed",
            "error": str(e)
        }


def run_weekly_refresh_worker(db: Session) -> dict:
    """
    Worker that processes queued RefreshJobs and submits them to DataForSEO.
    Uses atomic claim to prevent duplicate submission.
    """
    job = db.scalar(
        select(RefreshJob)
        .where(RefreshJob.jobType == "weekly_serp")
        .where(RefreshJob.status.in_(["queued", "retry"]))
        .order_by(RefreshJob.createdAt.asc())
        .limit(1)
    )
    
    if not job:
        return {"status": "completed", "processed": 0}
    
    result = db.execute(
        update(RefreshJob)
        .where(RefreshJob.id == job.id)
        .where(RefreshJob.status.in_(["queued", "retry"]))
        .values(status="processing", updatedAt=datetime.utcnow())
    ).rowcount
    
    if result == 0:
        db.rollback()
        return {"status": "completed", "processed": 0}
    
    db.commit()
    
    try:
        keywords = json.loads(job.keywordsJson or "[]")
        keyword_texts = [kw.get("keyword") for kw in keywords if kw.get("keyword")]
        location = keywords[0].get("location", "India") if keywords else "India"
        if keyword_texts:
            mark_keywords_processing_atomic(db, keyword_texts, location)
        
        success = submit_refresh_job_to_dataforseo(db, job)
        return {"status": "completed", "processed": 1 if success else 0}
    except Exception as exc:
        logger.error(f"Failed to process RefreshJob {job.id}: {exc}")
        return {"status": "failed", "error": str(exc)}


def recover_stale_weekly_jobs(db: Session) -> dict:
    """
    Recovery logic for stale weekly RefreshJobs.
    Uses atomic state transition to prevent duplicate recovery.
    """
    now = datetime.utcnow()
    result = db.execute(
        update(RefreshJob)
        .where(
            RefreshJob.jobType == "weekly_serp",
            RefreshJob.status.in_(["processing", "submitted"]),
            RefreshJob.processingTimeoutAt <= now,
            RefreshJob.retryCount < RefreshJob.maxRetries,
        )
        .values(
            status="retry",
            retryCount=RefreshJob.retryCount + 1,
            processingTimeoutAt=now + timedelta(hours=PROCESSING_TIMEOUT_HOURS),
            updatedAt=now,
        )
        .returning(RefreshJob.id)
    )
    
    recovered_ids = [row[0] for row in result.fetchall()]
    if recovered_ids:
        db.commit()
        logger.info(f"Recovered {len(recovered_ids)} stale weekly RefreshJobs for retry: {recovered_ids}")
    
    return {"recovered": len(recovered_ids)}


def submit_bulk_to_dataforseo(
    db: Session,
    task: AsyncTaskQueue,
) -> bool:
    """
    Submit the bulk task to DataForSEO async API.
    Uses the cheaper async endpoint instead of live API.
    Splits into chunks respecting ASYNC_BULK_MAX_TASKS.
    Kept for backward compatibility.
    """
    try:
        keywords = json.loads(task.keywordsJson or "[]")
        if not keywords:
            logger.warning(f"Task {task.id} has no keywords to process")
            return False
        
        keyword_texts = [kw.get("keyword") for kw in keywords if kw.get("keyword")]
        if not keyword_texts:
            logger.warning(f"Task {task.id} has no valid keywords")
            return False
        
        location_code = task.locationCode or 2840
        pingback_url = f"{settings.FRONTEND_URL}/api/webhooks/dataforseo"
        if settings.DATAFORSEO_WEBHOOK_SECRET:
            pingback_url = f"{pingback_url}?secret={settings.DATAFORSEO_WEBHOOK_SECRET}"
        
        from app.services.dataforseo_client import _build_serp_cache_key, _get_cached_serp, _log_dataforseo_cost
        from app.db.models import TrackedKeyword
        
        aio_keyword_texts = set(
            row.keyword
            for row in db.scalars(
                select(TrackedKeyword).where(
                    TrackedKeyword.isActive == True,
                    TrackedKeyword.trackAio == True,
                    TrackedKeyword.keyword.in_(keyword_texts),
                )
            ).all()
        )
        
        uncached_keywords = []
        cached_count = 0
        for kw in keyword_texts:
            aio_flag = kw in aio_keyword_texts
            cache_key = _build_serp_cache_key(kw, location_code, "en", "desktop", "unknown", 10, aio_flag)
            if _get_cached_serp(cache_key):
                cached_count += 1
            else:
                uncached_keywords.append(kw)
        
        if cached_count > 0:
            logger.info(f"Task {task.id}: {cached_count} keywords found in cache, {len(uncached_keywords)} need DataForSEO")
        
        if not uncached_keywords:
            logger.info(f"Task {task.id}: all keywords cached, skipping DataForSEO submission")
            _log_dataforseo_cost(
                db=db,
                user_id=task.userId,
                task_type="weekly_serp_cache_hit",
                endpoint="/serp/google/organic/task_post",
                method="GET",
                keyword_count=cached_count,
                priority=1,
                depth=10,
                expand_ai_overview=True,
                cache_hit=True,
                success=True,
            )
            task.status = "completed"
            task.completedAt = datetime.utcnow()
            task.resultJson = json.dumps({
                "dataforseo_task_ids": [],
                "processed_task_ids": [],
                "cached_count": cached_count,
                "skipped": True,
            })
            db.add(task)
            db.commit()
            return True
        
        chunks = [
            uncached_keywords[i:i + ASYNC_BULK_MAX_TASKS]
            for i in range(0, len(uncached_keywords), ASYNC_BULK_MAX_TASKS)
        ]
        
        auth = (settings.effective_serp_login, settings.effective_serp_key)
        all_task_ids = []
        failed_chunks = 0
        
        for chunk in chunks:
            serp_payload = []
            for kw in chunk:
                task_payload = {
                    "keyword": kw,
                    "location_code": location_code,
                    "language_code": "en",
                    "device": "desktop",
                    "depth": 10,
                    "pingback_url": pingback_url,
                    "priority": 1,
                    "expand_ai_overview": kw in aio_keyword_texts,
                }
                serp_payload.append(task_payload)
            
            post_res = requests.post(
                "https://api.dataforseo.com/v3/serp/google/organic/task_post",
                json=serp_payload,
                auth=auth,
                timeout=60,
            )
            
            if "application/json" not in post_res.headers.get("Content-Type", ""):
                logger.error("DataForSEO task_post error for chunk: %s", post_res.text[:500])
                failed_chunks += 1
                continue
            
            post_response = post_res.json()
            chunk_task_ids = []
            if "tasks" in post_response and post_response["tasks"]:
                for t in post_response["tasks"]:
                    if t.get("id"):
                        chunk_task_ids.append(t["id"])
            
            all_task_ids.extend(chunk_task_ids)
        
        if not all_task_ids:
            logger.warning(f"DataForSEO: no task IDs returned for task {task.id}")
            task.status = "failed"
            task.errorMessage = "No task IDs returned from DataForSEO"
            db.add(task)
            db.commit()
            return False
        
        task.resultJson = json.dumps({
            "dataforseo_task_ids": all_task_ids,
            "processed_task_ids": [],
            "chunk_count": len(chunks),
            "failed_chunks": failed_chunks,
        })
        task.status = "processing"
        db.add(task)
        db.commit()
        
        now = datetime.utcnow()
        if uncached_keywords:
            db_keywords = db.scalars(
                select(Keyword).where(
                    Keyword.keyword.in_(uncached_keywords),
                    Keyword.isActive == True,
                )
            ).all()
            keyword_status_map = {kw.keyword: kw for kw in db_keywords}
            for kw_text in uncached_keywords:
                db_keyword = keyword_status_map.get(kw_text)
                if db_keyword:
                    db_keyword.weeklyRefreshStatus = "processing"
                    db.add(db_keyword)
            db.commit()
        
        for dfs_task_id in all_task_ids:
            _log_dataforseo_cost(
                db=db,
                user_id=task.userId,
                task_type="weekly_serp",
                endpoint="/serp/google/organic/task_post",
                method="POST",
                keyword_count=len(uncached_keywords),
                priority=1,
                depth=10,
                expand_ai_overview=True,
                cache_hit=False,
                success=True,
                task_id=dfs_task_id,
            )
        
        from app.services.credit_service import reserve_credits
        from app.db.models import Keyword, Project, User
        
        refresh_cost = settings.plan_config.credit_costs.get("weekly_refresh_per_keyword", 10)
        user_reserve_map = {}
        for kw_text in uncached_keywords:
            db_keyword = db.scalar(
                select(Keyword)
                .join(Project, Project.id == Keyword.projectId)
                .join(User, User.id == Project.userId)
                .where(
                    Keyword.keyword == kw_text,
                    Keyword.isActive == True,
                    User.subscriptionStatus == "active",
                )
            )
            if db_keyword:
                user_id = db_keyword.userId
                user_reserve_map[user_id] = user_reserve_map.get(user_id, 0) + refresh_cost
        
        for uid, amount in user_reserve_map.items():
            try:
                reserve_credits(
                    db=db,
                    user_id=uid,
                    amount=float(amount),
                    action_type="reservation",
                    description=f"Weekly SERP bulk reservation: task {task.id}",
                    reference=f"bulk:{task.id}:{uid}",
                    task_id=task.id,
                )
            except Exception as exc:
                logger.error(f"Failed to reserve credits for bulk task {task.id} user {uid}: {exc}")
        
        if failed_chunks > 0:
            logger.warning(
                f"Task {task.id}: submitted {len(all_task_ids)} tasks across "
                f"{len(chunks)} chunks, {failed_chunks} chunks failed"
            )
        else:
            logger.info(f"Submitted task {task.id} with {len(all_task_ids)} task(s) across {len(chunks)} chunk(s)")
        
        return True
         
    except Exception as e:
        logger.error(f"Failed to submit task {task.id} to DataForSEO: {e}")
        task.status = "failed"
        task.errorMessage = str(e)
        db.add(task)
        db.commit()
        return False


def get_refresh_status(db: Session) -> dict:
    """
    Get queue status/progress for weekly and monthly jobs.
    Uses database aggregation for efficiency.
    """
    from sqlalchemy import case
    
    weekly_stats = db.execute(
        select(
            func.count(RefreshJob.id).label("totalJobs"),
            func.sum(case((RefreshJob.status == "queued", 1), else_=0)).label("queuedJobs"),
            func.sum(case((RefreshJob.status == "processing", 1), else_=0)).label("processingJobs"),
            func.sum(case((RefreshJob.status == "submitted", 1), else_=0)).label("submittedJobs"),
            func.sum(case((RefreshJob.status == "success", 1), else_=0)).label("completedJobs"),
            func.sum(case((RefreshJob.status == "failed", 1), else_=0)).label("failedJobs"),
            func.sum(case((RefreshJob.status == "retry", 1), else_=0)).label("retryingJobs"),
            func.sum(RefreshJob.keywordCount).label("totalKeywords"),
        ).where(RefreshJob.jobType == "weekly_serp")
    ).first()
    
    monthly_stats = db.execute(
        select(
            func.count(RefreshJob.id).label("totalJobs"),
            func.sum(case((RefreshJob.status == "queued", 1), else_=0)).label("queuedJobs"),
            func.sum(case((RefreshJob.status == "processing", 1), else_=0)).label("processingJobs"),
            func.sum(case((RefreshJob.status == "submitted", 1), else_=0)).label("submittedJobs"),
            func.sum(case((RefreshJob.status == "success", 1), else_=0)).label("completedJobs"),
            func.sum(case((RefreshJob.status == "failed", 1), else_=0)).label("failedJobs"),
            func.sum(case((RefreshJob.status == "retry", 1), else_=0)).label("retryingJobs"),
            func.sum(RefreshJob.keywordCount).label("totalKeywords"),
        ).where(RefreshJob.jobType == "monthly_metrics")
    ).first()
    
    def summarize(row):
        if not row or row.totalJobs is None:
            return {
                "totalJobs": 0,
                "queuedJobs": 0,
                "processingJobs": 0,
                "submittedJobs": 0,
                "completedJobs": 0,
                "failedJobs": 0,
                "retryingJobs": 0,
                "totalKeywords": 0,
            }
        return {
            "totalJobs": row.totalJobs or 0,
            "queuedJobs": row.queuedJobs or 0,
            "processingJobs": row.processingJobs or 0,
            "submittedJobs": row.submittedJobs or 0,
            "completedJobs": row.completedJobs or 0,
            "failedJobs": row.failedJobs or 0,
            "retryingJobs": row.retryingJobs or 0,
            "totalKeywords": row.totalKeywords or 0,
        }
    
    return {
        "weekly": summarize(weekly_stats),
        "monthly": summarize(monthly_stats),
    }