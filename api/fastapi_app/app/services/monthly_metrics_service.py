"""
Monthly Keyword Metrics Refresh Service

This service handles the monthly refresh of keyword-table metrics:
- volume
- kd
- cpc
- competition
- backlinks
- referring_domains
- intent

These metrics are refreshed monthly only. Weekly rank tracking jobs
must NOT update these fields.
"""

import json
import logging
from datetime import datetime, timedelta

import requests
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Keyword, Project, User, DataForSEOCost, KeywordMetricsHistory, RefreshJob, CreditLedger
from app.services.credit_service import (
    deduct_credits, reserve_credits, consume_reserved, refund_reserved,
    consume_automatic_reserved, refund_automatic_reserved,
)
from app.services.async_bulk_service import submit_refresh_job_to_dataforseo
from app.services.keyword_identity import effective_location_code, normalize_device, normalize_keyword
from app.services.dataforseo_client import _build_kw_metrics_cache_key, _get_cached_kw_metrics, _set_cached_kw_metrics, _log_dataforseo_cost

logger = logging.getLogger(__name__)
settings = get_settings()

MONTHLY_METRICS_FIELDS = {
    "volume",
    "kd",
    "cpc",
    "competition",
    "backlinks",
    "referring_domains",
    "intent",
}


def _monthly_keyword_target(keyword: Keyword, project: Project | None = None) -> tuple[str, int, str]:
    project = project or getattr(keyword, "project", None)
    location_code = effective_location_code(
        location_code=keyword.locationCode,
        location=keyword.location,
        project_location_code=getattr(project, "locationCode", None),
        project_location=getattr(project, "location", None),
    )
    return (
        normalize_keyword(keyword.keyword),
        int(location_code),
        normalize_device(keyword.device or getattr(project, "device", None)),
    )


def _monthly_result_key(keyword: str, location_code: int) -> str:
    return f"{normalize_keyword(keyword)}|{int(location_code)}"


def _paginate_eligible_keywords_for_monthly(db: Session, batch_size: int = 5000) -> list[list[dict]]:
    """
    Keyset-paginated collection of eligible keywords for monthly refresh.
    """
    now = datetime.utcnow()
    entries = {}
    last_id = None
    
    while True:
        query = (
            select(Keyword, Project)
            .join(Project, Project.id == Keyword.projectId)
            .join(User, User.id == Project.userId)
            .where(
                Keyword.isActive == True,
                User.subscriptionStatus == "active",
                User.selectedPlan.in_(["starter", "pro", "agency", "enterprise"]),
                User.refreshFrequency.in_(["monthly", None, ""]),
                (Keyword.lastMonthlyMetricsRefreshAt == None) | (Keyword.lastMonthlyMetricsRefreshAt < now - timedelta(days=14)),
            )
            .order_by(Keyword.id.asc())
        )
        
        if last_id is not None:
            query = query.where(Keyword.id > last_id)
        
        query = query.limit(batch_size)
        batch = db.execute(query).all()
        
        if not batch:
            break
        
        for kw, project in batch:
            keyword_text, location_code, device = _monthly_keyword_target(kw, project)
            key = (keyword_text, location_code)
            entry = entries.setdefault(
                key,
                {
                    "keyword": keyword_text,
                    "location": kw.location or project.location or "India",
                    "location_code": location_code,
                    "eligible_rows": [],
                },
            )
            entry["eligible_rows"].append({
                "keyword_id": kw.id,
                "project_id": kw.projectId,
                "user_id": kw.userId,
                "keyword": keyword_text,
                "location": kw.location or project.location or "India",
                "location_code": location_code,
                "device": device,
            })
        
        last_id = batch[-1][0].id
        
        if len(batch) < batch_size:
            break
    
    ordered_entries = list(entries.values())
    return [
        ordered_entries[index:index + batch_size]
        for index in range(0, len(ordered_entries), batch_size)
    ]


def _fetch_monthly_metrics(db: Session, keywords: list[dict]) -> dict:
    """
    Fetch monthly metrics from DataForSEO Labs keyword_overview endpoint.
    Uses existing 7-day cache.
    Returns dict mapping (keyword, location) -> metrics dict.
    """
    if not keywords:
        return {}

    results = {}
    target_entries: dict[tuple[str, int], str] = {}
    for kw_entry in keywords:
        kw = normalize_keyword(kw_entry.get("keyword"))
        location = kw_entry.get("location", "India")
        # Legacy callers did not persist a code; retain their established
        # 2840 fallback while modern scheduled entries provide location_code.
        location_code = int(kw_entry.get("location_code") or 2840)
        target_entries[(kw, location_code)] = location

    missing_targets = []
    for (kw, location_code), location in target_entries.items():
        cache_key = _build_kw_metrics_cache_key(kw, location_code, "en")
        cached = _get_cached_kw_metrics(cache_key)
        if cached:
            results[(kw, location)] = cached
        else:
            missing_targets.append((kw, location_code, location))

    if not missing_targets:
        logger.info("All monthly metrics found in cache, skipping DataForSEO call")
        return results

    url = f"{getattr(settings, 'DATAFORSEO_BASE_URL', None) or 'https://api.dataforseo.com/v3'}/dataforseo_labs/google/keyword_overview/live"
    
    targets_by_location: dict[int, list[tuple[str, int, str]]] = {}
    for target in missing_targets:
        targets_by_location.setdefault(target[1], []).append(target)
    chunks = [
        chunk
        for location_targets in targets_by_location.values()
        for chunk in (
            location_targets[i:i + 700]
            for i in range(0, len(location_targets), 700)
        )
    ]
    
    try:
        for chunk in chunks:
            location_code = chunk[0][1]
            payload = [
                {
                    "keywords": [target[0] for target in chunk],
                    "location_code": location_code,
                    "language_code": "en",
                    "item_types": ["organic", "paid", "ai_overview_reference"],
                }
            ]
            
            logger.info("Monthly metrics Labs payload: %s keywords", len(chunk))
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
                kw = normalize_keyword(kw)
                task_location_code = int(
                    (task.get("data") or {}).get("location_code") or location_code
                )
                location = target_entries.get((kw, task_location_code), "India")

                metric_entry = {
                    "volume": keyword_info.get("search_volume"),
                    "kd": keyword_properties.get("keyword_difficulty"),
                    "cpc": keyword_info.get("cpc"),
                    "competition": keyword_info.get("competition"),
                    "backlinks": avg_backlinks_info.get("backlinks"),
                    "referring_domains": avg_backlinks_info.get("referring_domains"),
                    "intent": search_intent_info.get("main_intent"),
                }
                results[(kw, location)] = metric_entry

                cache_key = _build_kw_metrics_cache_key(kw, task_location_code, "en")
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
                    # Labs keyword metrics neither request nor mutate AIO data.
                    expand_ai_overview=False,
                    cache_hit=False,
                    success=True,
                )
    except Exception as exc:
        logger.error("Monthly metrics DataForSEO request failed: %s", exc)
        _log_dataforseo_cost(
            db=db,
            user_id=None,
            task_type="monthly_metrics_error",
            endpoint="/dataforseo_labs/google/keyword_overview/live",
            method="POST",
            keyword_count=len(missing_targets),
            priority=1,
            depth=100,
            expand_ai_overview=False,
            cache_hit=False,
            success=False,
            error=str(exc),
        )
        return results

    return results


def _apply_monthly_metrics(db: Session, keyword_map: dict, metrics_data: dict) -> tuple[int, int]:
    """
    Apply monthly metrics to Keyword rows.
    Returns (updated_count, credit_failures_count).
    """
    now = datetime.utcnow()
    updated_count = 0
    credit_failures = 0

    for (kw_text, location), kw_objects in keyword_map.items():
        metrics = metrics_data.get((kw_text, location))
        if not metrics:
            continue

        for kw_obj in kw_objects:
            try:
                kw_obj.volume = metrics.get("volume")
                kw_obj.kd = metrics.get("kd")
                kw_obj.cpc = metrics.get("cpc")
                kw_obj.competition = metrics.get("competition")
                kw_obj.backlinks = metrics.get("backlinks")
                kw_obj.referring_domains = metrics.get("referring_domains")
                kw_obj.intent = metrics.get("intent")
                kw_obj.lastMonthlyMetricsRefreshAt = now
                kw_obj.updatedAt = now
                db.add(kw_obj)
                updated_count += 1
            except Exception as exc:
                logger.error(f"Failed to apply monthly metrics for keyword {kw_text}: {exc}")
                credit_failures += 1

    return updated_count, credit_failures


def _record_metrics_history(db: Session, keyword_map: dict, metrics_data: dict) -> int:
    """
    Record previous metrics to KeywordMetricsHistory before applying new values.
    Returns count of history records created.
    """
    now = datetime.utcnow()
    history_count = 0

    for (kw_text, location), kw_objects in keyword_map.items():
        metrics = metrics_data.get((kw_text, location))
        if not metrics:
            continue

        for kw_obj in kw_objects:
            try:
                history = KeywordMetricsHistory(
                    keywordId=kw_obj.id,
                    projectId=kw_obj.projectId,
                    userId=kw_obj.userId,
                    volume=kw_obj.volume,
                    kd=kw_obj.kd,
                    cpc=kw_obj.cpc,
                    competition=kw_obj.competition,
                    backlinks=kw_obj.backlinks,
                    referring_domains=kw_obj.referring_domains,
                    intent=kw_obj.intent,
                    refreshedAt=now,
                )
                db.add(history)
                history_count += 1
            except Exception as exc:
                logger.error(f"Failed to record metrics history for keyword {kw_text}: {exc}")

    return history_count


def run_monthly_metrics_refresh(db: Session) -> dict:
    """
    Main entry point for monthly keyword metrics refresh.
    Runs once per month to refresh volume, kd, cpc, competition, backlinks,
    referring_domains, and intent for all active users' keywords.
    Uses keyset pagination and RefreshJob records.
    """
    logger.info("Starting monthly keyword metrics refresh")

    try:
        keyword_batches = _paginate_eligible_keywords_for_monthly(db)
        
        if not keyword_batches:
            logger.info("No keywords due for monthly metrics refresh")
            return {
                "status": "completed",
                "keywords_processed": 0,
                "updated_count": 0,
            }
        
        total_keywords = sum(len(b) for b in keyword_batches)
        jobs = []
        for index, keywords in enumerate(keyword_batches):
            job = RefreshJob(
                jobType="monthly_metrics",
                status="queued",
                batchIndex=index,
                totalBatches=len(keyword_batches),
                keywordCount=len(keywords),
                keywordsJson=json.dumps(keywords),
            )
            db.add(job)
            jobs.append(job)
        
        db.commit()
        for job in jobs:
            db.refresh(job)
        
        logger.info(
            f"Monthly metrics refresh queued: {len(jobs)} RefreshJobs "
            f"for {total_keywords} keywords"
        )
        
        return {
            "status": "queued",
            "keywords_processed": total_keywords,
            "updated_count": 0,
            "job_ids": [j.id for j in jobs],
        }
        
    except Exception as exc:
        logger.exception(f"Monthly metrics refresh failed: %s", exc)
        db.rollback()
        return {
            "status": "failed",
            "error": str(exc),
        }


def run_monthly_refresh_worker(db: Session) -> dict:
    """
    Worker that processes queued monthly RefreshJobs.
    Uses atomic claim to prevent duplicate processing.
    """
    processed = 0
    failed = 0
    while True:
        job = db.scalar(
            select(RefreshJob)
            .where(RefreshJob.jobType == "monthly_metrics")
            .where(RefreshJob.status.in_(["queued", "retry"]))
            .order_by(RefreshJob.createdAt.asc())
            .limit(1)
        )
        if not job:
            return {"status": "completed", "processed": processed, "failed": failed}

        claimed = db.execute(
            update(RefreshJob)
            .where(RefreshJob.id == job.id)
            .where(RefreshJob.status.in_(["queued", "retry"]))
            .values(status="processing", updatedAt=datetime.utcnow())
        ).rowcount
        if claimed == 0:
            db.rollback()
            continue
        db.commit()

        try:
            keywords = json.loads(job.keywordsJson or "[]")
            keyword_texts = [kw.get("keyword") for kw in keywords if kw.get("keyword")]
            if keyword_texts:
                from app.services.async_bulk_service import mark_keywords_processing_atomic
                location = keywords[0].get("location", "India") if keywords else "India"
                keyword_ids = [
                    row.get("keyword_id")
                    for entry in keywords
                    for row in entry.get("eligible_rows", [])
                    if row.get("keyword_id")
                ]
                mark_keywords_processing_atomic(
                    db, keyword_texts, location, keyword_ids=keyword_ids or None
                )
            success = submit_refresh_job_to_dataforseo(db, job)
            if success:
                _apply_monthly_refresh_results(db, job)
                processed += 1
            else:
                failed += 1
        except Exception as exc:
            failed += 1
            logger.error(f"Failed to process monthly RefreshJob {job.id}: {exc}")


def _apply_monthly_refresh_results(db: Session, job: RefreshJob) -> None:
    """
    Apply monthly metrics results from a RefreshJob to Keyword records.
    Also handles credit deduction for all keywords in the job.
    """
    if job.status != "success" or not job.resultSummary:
        return
    
    try:
        summary = json.loads(job.resultSummary)
        results = summary.get("results", {})
        results_by_target = summary.get("results_by_target", {})
        
        keywords = json.loads(job.keywordsJson or "[]")
        
        now = datetime.utcnow()
        updated_count = 0
        applied_keyword_ids = set(summary.get("applied_keyword_ids", []))
        identity_entries = [
            entry for entry in keywords if "eligible_rows" in entry
        ]
        if identity_entries:
            row_specs = [
                (
                    row.get("keyword_id"),
                    normalize_keyword(entry.get("keyword")),
                    entry.get("location", "India"),
                    int(row.get("location_code") or entry.get("location_code") or 2840),
                )
                for entry in identity_entries
                for row in entry.get("eligible_rows", [])
                if row.get("keyword_id")
            ]
        else:
            row_specs = []
            for kw_entry in keywords:
                kw_text = kw_entry.get("keyword", "").lower().strip()
                location = kw_entry.get("location", "India")
                db_keywords = db.scalars(
                    select(Keyword).where(
                        Keyword.keyword == kw_text,
                        Keyword.isActive == True,
                        (
                            (Keyword.location == location) |
                            (Keyword.location == None)
                        ),
                    )
                ).all()
                for row in db_keywords:
                    project = db.get(Project, row.projectId)
                    row_specs.append(
                        (
                            row.id,
                            kw_text,
                            location,
                            effective_location_code(
                                location_code=row.locationCode,
                                location=row.location,
                                project_location_code=getattr(project, "locationCode", None),
                                project_location=getattr(project, "location", None),
                            ),
                        )
                    )

        exact_ids = [keyword_id for keyword_id, _, _, _ in row_specs]
        exact_keyword_rows = {
            row.id: row
            for row in db.scalars(
                select(Keyword).where(
                    Keyword.id.in_(exact_ids),
                    Keyword.isActive == True,
                )
            ).all()
        } if exact_ids else {}

        seen_ids = set()
        for keyword_id, kw_text, location, location_code in row_specs:
            if keyword_id in seen_ids or keyword_id in applied_keyword_ids:
                continue
            seen_ids.add(keyword_id)
            db_keyword = exact_keyword_rows.get(keyword_id)
            metrics = results_by_target.get(
                f"{normalize_keyword(kw_text)}|{int(location_code)}"
            ) or results.get(kw_text)
            if not db_keyword or not db_keyword.isActive or not metrics:
                continue

            user_id = db_keyword.userId
            try:
                consume_automatic_reserved(
                    db=db,
                    user_id=user_id,
                    reference=f"auto:monthly:{job.id}:{user_id}",
                    amount=settings.plan_config.credit_costs.get("monthly_refresh_per_keyword", 10),
                    description=f"Monthly keyword metrics refresh: {kw_text}",
                    project_id=db_keyword.projectId,
                    keyword_id=db_keyword.id,
                    task_id=job.id,
                    commit=False,
                )
                history = KeywordMetricsHistory(
                    keywordId=db_keyword.id,
                    projectId=db_keyword.projectId,
                    userId=db_keyword.userId,
                    volume=db_keyword.volume,
                    kd=db_keyword.kd,
                    cpc=db_keyword.cpc,
                    competition=db_keyword.competition,
                    backlinks=db_keyword.backlinks,
                    referring_domains=db_keyword.referring_domains,
                    intent=db_keyword.intent,
                    refreshedAt=now,
                )
                db.add(history)

                db_keyword.volume = metrics.get("volume")
                db_keyword.kd = metrics.get("kd")
                db_keyword.cpc = metrics.get("cpc")
                db_keyword.competition = metrics.get("competition")
                db_keyword.backlinks = metrics.get("backlinks")
                db_keyword.referring_domains = metrics.get("referring_domains")
                db_keyword.intent = metrics.get("intent")
                db_keyword.lastMonthlyMetricsRefreshAt = now
                db_keyword.updatedAt = now
                db.add(db_keyword)
                applied_keyword_ids.add(keyword_id)
                updated_count += 1
            except Exception as exc:
                logger.error(f"Failed to apply monthly metrics for keyword {kw_text}: {exc}")

        summary["applied_keyword_ids"] = sorted(applied_keyword_ids)
        job.resultSummary = json.dumps(summary)
        db.add(job)
        db.commit()

        pending_user_ids = db.scalars(
            select(CreditLedger.userId).where(
                CreditLedger.creditPool == "automatic",
                CreditLedger.status == "pending",
                CreditLedger.description.like(f"%[ref:auto:monthly:{job.id}:%"),
            ).distinct()
        ).all()
        for user_id in pending_user_ids:
            refund_automatic_reserved(
                db, user_id, f"auto:monthly:{job.id}:{user_id}", 10**12,
                "Unused monthly automatic tracking reservation refunded",
            )
        logger.info(f"Applied monthly metrics for RefreshJob {job.id}: updated {updated_count} keywords from automatic reservations")
        
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to apply monthly refresh results for job {job.id}: {exc}")



def recover_stale_monthly_jobs(db: Session) -> dict:
    """
    Recovery logic for stale monthly RefreshJobs.
    Uses atomic state transition to prevent duplicate recovery.
    """
    now = datetime.utcnow()
    result = db.execute(
        update(RefreshJob)
        .where(
            RefreshJob.jobType == "monthly_metrics",
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
        logger.info(f"Recovered {len(recovered_ids)} stale monthly RefreshJobs for retry: {recovered_ids}")
    
    return {"recovered": len(recovered_ids)}
