"""
Async tracking service for user-triggered keyword operations.

Reuses the existing RefreshJob + ProcessingJob + webhook + worker
infrastructure so Add Keyword, Bulk Add, and Manual Refresh can run
through DataForSEO task_post without introducing a second async system.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select, func
from sqlalchemy.orm import Session

from app.db.models import (
    Keyword,
    Project,
    RefreshJob,
    ProcessingJob,
    RankResult,
    TrackedKeyword,
    CreditLedger,
)
from app.services.credit_service import (
    reserve_credits,
    consume_reserved,
    refund_reserved,
)
from app.services.dataforseo_client import (
    DataForSEOClient,
    get_serp_priority,
    SERP_TASK_POST_BATCH_SIZE,
    _build_serp_cache_key,
    _get_cached_serp,
    _set_cached_serp,
    _log_dataforseo_cost,
    CODE_TO_LOCATION,
)
from app.services.keyword_update_events import publish_keyword_update
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PROCESSING_TIMEOUT_HOURS = 24
CALLBACK_RECOVERY_GRACE_MINUTES = 30
CALLBACK_RECOVERY_RETRY_MINUTES = 15


def _normalize_domain(domain: str) -> str:
    if not domain:
        return ""

    domain = domain.strip().lower()
    domain = domain.replace("https://", "").replace("http://", "")
    domain = domain.split("/")[0]
    domain = domain.split(":")[0]

    if domain.startswith("www."):
        domain = domain[4:]

    return domain

def _build_postback_url() -> str:
    base_url = settings.PINGBACK_URL or settings.FRONTEND_URL
    postback_url = (
        f"{base_url.rstrip('/')}/api/webhooks/dataforseo"
        f"?task_id=$id"
    )

    if settings.DATAFORSEO_WEBHOOK_SECRET:
        postback_url = (
            f"{postback_url}&secret={settings.DATAFORSEO_WEBHOOK_SECRET}"
        )

    return postback_url


def _existing_pending_refresh_job(db: Session, project_id: str, keyword_text: str, job_type: str) -> Optional[RefreshJob]:
    return db.scalar(
        select(RefreshJob)
        .where(RefreshJob.jobType == job_type)
        .where(RefreshJob.status.in_(["queued", "processing", "submitted"]))
        .where(RefreshJob.keywordsJson.contains(keyword_text))
        .order_by(RefreshJob.createdAt.desc())
        .limit(1)
    )

def _enrich_keyword_metrics(
    db: Session,
    user_id: str,
    project_id: str,
    keyword_texts: list[str],
    location_code: int,
) -> dict:
    """
    Fetch and persist Keyword Overview metrics for tracked keywords.

    This is intentionally separate from SERP tracking:
    - SERP task_post provides position, ranking URL and AIO badge.
    - Keyword Overview provides volume, KD, CPC, competition,
      backlinks, referring domains and intent.

    The DataForSEO client handles the 7-day metrics cache and batches
    uncached keywords into one Keyword Overview request.
    """
    if not keyword_texts:
        return {
            "requested": 0,
            "updated": 0,
            "missing": 0,
        }

    location_name = CODE_TO_LOCATION.get(location_code, "India")

    try:
        metrics_map = DataForSEOClient._fetch_keyword_data_batch(
            keyword_texts,
            location_name,
            db=db,
            user_id=user_id,
        )
    except Exception as exc:
        logger.exception(
            "Keyword metrics enrichment failed for project=%s: %s",
            project_id,
            exc,
        )
        return {
            "requested": len(keyword_texts),
            "updated": 0,
            "missing": len(keyword_texts),
        }

    if not metrics_map:
        logger.warning(
            "Keyword metrics enrichment returned no metrics for project=%s keywords=%s",
            project_id,
            keyword_texts,
        )
        return {
            "requested": len(keyword_texts),
            "updated": 0,
            "missing": len(keyword_texts),
        }

    keyword_rows = db.scalars(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword.in_(keyword_texts),
            Keyword.isActive == True,
        )
    ).all()

    rows_by_keyword = {
        row.keyword.strip().lower(): row
        for row in keyword_rows
        if row.keyword
    }

    metrics_by_keyword = {
        key.strip().lower(): value
        for key, value in metrics_map.items()
        if isinstance(key, str)
    }

    now = datetime.utcnow()
    updated = 0

    for keyword_text in keyword_texts:
        normalized = keyword_text.strip().lower()

        keyword_row = rows_by_keyword.get(normalized)
        metrics = metrics_by_keyword.get(normalized)

        if not keyword_row or not metrics:
            continue

        volume = metrics.get("volume")
        difficulty = metrics.get("difficulty")
        cpc = metrics.get("cpc")
        competition = metrics.get("competition")
        backlinks = metrics.get("backlinks")
        referring_domains = metrics.get("referring_domains")
        intent = metrics.get("intent")

        if volume is not None:
            keyword_row.volume = volume

        if difficulty is not None:
            keyword_row.kd = difficulty

        if cpc is not None:
            keyword_row.cpc = cpc

        if competition is not None:
            keyword_row.competition = competition

        if backlinks is not None:
            keyword_row.backlinks = backlinks

        if referring_domains is not None:
            keyword_row.referring_domains = referring_domains

        if intent:
            keyword_row.intent = intent

        keyword_row.lastMonthlyMetricsRefreshAt = now
        keyword_row.updatedAt = now

        db.add(keyword_row)
        updated += 1

    # Flush only. submit_user_tracking_job controls the transaction.
    db.flush()

    logger.info(
        "Keyword metrics enrichment complete project=%s requested=%s updated=%s",
        project_id,
        len(keyword_texts),
        updated,
    )

    return {
        "requested": len(keyword_texts),
        "updated": updated,
        "missing": len(keyword_texts) - updated,
    }

def submit_user_tracking_job(
    db: Session,
    user_id: str,
    project_id: str,
    keywords: list[dict],
    domain: str,
    action: str,
    location_code: int = 2840,
    language_code: str = "en",
    device: str = "desktop",
    depth: int = 100,
    cost_per_keyword: int = 20,
) -> dict:
    if not keywords:
        return {"refresh_job_id": None, "task_ids": [], "submitted": [], "failed_chunks": 0, "accepted": False, "accepted_keywords": [], "completed_keywords": [], "failed_keywords": []}

    priority = get_serp_priority(action)
    postback_url = _build_postback_url()

    keyword_texts = [kw.get("keyword", "").strip() for kw in keywords if kw.get("keyword")]
    keyword_texts = [kw for kw in keyword_texts if kw]
    if not keyword_texts:
        return {"refresh_job_id": None, "task_ids": [], "submitted": [], "failed_chunks": 0, "accepted": False, "accepted_keywords": [], "completed_keywords": [], "failed_keywords": []}

    pending_jobs = db.scalars(
        select(RefreshJob)
        .where(RefreshJob.jobType == action)
        .where(RefreshJob.status.in_(["queued", "processing", "submitted"]))
        .order_by(RefreshJob.createdAt.desc())
        .limit(20)
    ).all()

    requested_keywords = sorted(
        kw.strip().lower()
        for kw in keyword_texts
        if kw.strip()
    )

    for pending_job in pending_jobs:
        try:
            result_summary = json.loads(pending_job.resultSummary or "{}")
        except Exception:
            result_summary = {}

        if result_summary.get("project_id") != project_id:
            continue

        if result_summary.get("user_id") != user_id:
            continue

        try:
            pending_payload = json.loads(
                pending_job.keywordsJson or "[]"
            )
        except Exception:
            pending_payload = []

        pending_keywords = sorted(
            str(item.get("keyword", "")).strip().lower()
            for item in pending_payload
            if isinstance(item, dict) and item.get("keyword")
        )

        # Only reuse the job when this is the exact same in-flight request.
        if pending_keywords != requested_keywords:
            continue

        logger.info(
            "Reusing identical pending %s RefreshJob %s for project %s",
            action,
            pending_job.id,
            project_id,
        )

        completed_keyword_set = set(
            db.scalars(
                select(ProcessingJob.keywordText).where(
                    ProcessingJob.refreshJobId == pending_job.id,
                    ProcessingJob.status == "success",
                )
            ).all()
        )
        completed_keywords = [
            keyword
            for keyword in keyword_texts
            if keyword in completed_keyword_set
        ]

        return {
            "refresh_job_id": pending_job.id,
            "task_ids": json.loads(
                pending_job.dataforseoRequestIds or "[]"
            ),
            "submitted": keyword_texts,
            "failed_chunks": 0,
            "accepted": True,
            "accepted_keywords": keyword_texts,
            "completed_keywords": completed_keywords,
            "failed_keywords": [],
        }

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
    cached_results = {}
    for kw_text in keyword_texts:
        aio_flag = kw_text in aio_keyword_texts
        cache_key = _build_serp_cache_key(kw_text, location_code, language_code, device, "unknown", depth, aio_flag)
        cached = _get_cached_serp(cache_key)
        if cached:
            cached_results[kw_text] = cached
        else:
            uncached_keywords.append(kw_text)

    reference = f"{action}:{user_id}:{project_id}:{datetime.utcnow().timestamp()}"
    try:
        reserve_credits(
            db,
            user_id,
            float(len(keyword_texts) * cost_per_keyword),
            "reservation",
            f"{action.replace('_', ' ').title()} tracking reservation",
            reference=reference,
            project_id=project_id,
        )
    except Exception as exc:
        logger.error(f"{action} tracking credit reservation failed: {exc}")
        raise

    # Enrich user-added keywords with Keyword Overview metrics.
    #
    # Do not run this for manual/weekly SERP refreshes because these
    # metrics have their own cache/refresh lifecycle and should not
    # generate unnecessary Labs requests on every rank refresh.
    metrics_summary = {
        "requested": 0,
        "updated": 0,
        "missing": 0,
    }

    if action in ("add_keyword", "bulk_add"):
        metrics_summary = _enrich_keyword_metrics(
            db=db,
            user_id=user_id,
            project_id=project_id,
            keyword_texts=keyword_texts,
            location_code=location_code,
        )

    refresh_job = RefreshJob(
        jobType=action,
        status="queued",
        batchIndex=0,
        totalBatches=1,
        keywordCount=len(keyword_texts),
        keywordsJson=json.dumps(keywords),
        dataforseoRequestIds="[]",
        resultSummary=json.dumps({
            "credit_reference": reference,
            "cost_per_keyword": cost_per_keyword,
            "total_keywords": len(keyword_texts),
            "cached_count": len(cached_results),
            "domain": domain,
            "location_code": location_code,
            "language_code": language_code,
            "device": device,
            "depth": depth,
            "priority": priority,
            "project_id": project_id,
            "user_id": user_id,
            "metrics_requested": metrics_summary["requested"],
            "metrics_updated": metrics_summary["updated"],
            "metrics_missing": metrics_summary["missing"],
        }),
    )
    db.add(refresh_job)
    db.flush()
    db.refresh(refresh_job)

    completed_cached_keywords = []
    if cached_results:
        completed_cached_keywords = _apply_cached_results(
            db,
            project_id,
            user_id,
            domain,
            cached_results,
            refresh_job.id
        )
        consume_reserved(
            db=db,
            user_id=user_id,
            reference=reference,
            amount=float(len(cached_results) * cost_per_keyword),
            action_type="charge",
            description=f"{action.replace('_', ' ').title()}: cached results",
            project_id=project_id,
            commit=False,
        )

    if not uncached_keywords:
        refresh_job.status = "success"
        refresh_job.completedAt = datetime.utcnow()
        db.add(refresh_job)
        db.commit()
        _publish_cached_completion_events(
            user_id,
            project_id,
            completed_cached_keywords,
        )
        return {
            "refresh_job_id": refresh_job.id,
            "task_ids": [],
            "submitted": [],
            "failed_chunks": 0,
            "cached_count": len(cached_results),
            "accepted": True,
            "accepted_keywords": list(cached_results),
            "completed_keywords": completed_cached_keywords,
            "failed_keywords": [],
        }

    from app.services.dataforseo_client import check_dfs_cost_ceiling
    estimated_cost = len(uncached_keywords) * 0.0155
    try:
        check_dfs_cost_ceiling(db, user_id, estimated_cost)
    except Exception as exc:
        refund_reserved(db, user_id, reference, float(len(keyword_texts) * cost_per_keyword), description=f"Refund: DFS cost ceiling exceeded for {action}")
        db.commit()
        raise

    task_payloads = []
    for kw_text in uncached_keywords:
        task_payloads.append({
            "keyword": kw_text,
            "location_code": location_code,
            "language_code": language_code,
            "device": device,
            "depth": depth,
        })

    submission = DataForSEOClient.submit_serp_task_post(
        keywords=task_payloads,
        location_code=location_code,
        language_code=language_code,
        device=device,
        depth=depth,
        priority=priority,
        postback_url=postback_url,
        expand_ai_overview=(
            True
            if action in ("add_keyword", "bulk_add")
            else bool(aio_keyword_texts)
        ),
        db=db,
        user_id=user_id,
        task_type=action,
        stop_crawl_on_match_domain=domain,
    )

    all_task_ids = submission.get("task_ids", [])
    submitted_keywords = submission.get("submitted", [])
    failed_chunks = submission.get("failed_chunks", 0)

    if not all_task_ids:
        refund_reserved(
            db,
            user_id,
            reference,
            float(len(keyword_texts) * cost_per_keyword),
            description=f"Refund: {action} task_post submission failed",
        )

        try:
            result_summary = json.loads(refresh_job.resultSummary or "{}")
        except Exception:
            result_summary = {}

        result_summary["error"] = "No task IDs returned from DataForSEO"

        refresh_job.resultSummary = json.dumps(result_summary)
        refresh_job.status = "failed"
        refresh_job.completedAt = datetime.utcnow()
        db.add(refresh_job)
        db.commit()
        _publish_cached_completion_events(
            user_id,
            project_id,
            completed_cached_keywords,
        )
        return {
            "refresh_job_id": refresh_job.id,
            "task_ids": [],
            "submitted": [],
            "failed_chunks": failed_chunks,
            "cached_count": len(cached_results),
            "accepted": bool(cached_results),
            "accepted_keywords": list(cached_results),
            "completed_keywords": completed_cached_keywords,
            "failed_keywords": list(uncached_keywords),
        }

    submitted_normalized = {
        str(keyword).strip().lower()
        for keyword in submitted_keywords
        if str(keyword).strip()
    }
    accepted_uncached_keywords = [
        keyword
        for keyword in uncached_keywords
        if keyword.strip().lower() in submitted_normalized
    ]
    failed_keywords = [
        keyword
        for keyword in uncached_keywords
        if keyword.strip().lower() not in submitted_normalized
    ]

    if failed_keywords:
        refund_reserved(
            db,
            user_id,
            reference,
            float(len(failed_keywords) * cost_per_keyword),
            description=f"Refund: {action} keywords not submitted",
            project_id=project_id,
        )

    existing_ids = json.loads(refresh_job.dataforseoRequestIds or "[]")
    existing_ids.extend(all_task_ids)
    refresh_job.dataforseoRequestIds = json.dumps(existing_ids)
    refresh_job.status = "submitted"
    refresh_job.processingTimeoutAt = datetime.utcnow() + timedelta(hours=PROCESSING_TIMEOUT_HOURS)
    db.add(refresh_job)

    for kw_text in accepted_uncached_keywords:
        deduplication_key = f"pending:{refresh_job.id}:{kw_text}:{location_code}"
        processing_job = ProcessingJob(
            refreshJobId=refresh_job.id,
            keywordText=kw_text,
            location=CODE_TO_LOCATION.get(location_code, "India"),
            status="pending",
            deduplicationKey=deduplication_key,
            payload=json.dumps({
                "action": action,
                "credit_reference": reference,
                "cost_per_keyword": cost_per_keyword,
                "task_ids": [],
                "location_code": location_code,
                "language_code": language_code,
                "device": device,
                "depth": depth,
                "domain": domain,
                "user_id": user_id,
                "project_id": project_id,
                "awaiting_callback": True,
            }),
        )
        db.add(processing_job)

    db.flush()

    keyword_rows = db.scalars(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword.in_(accepted_uncached_keywords),
            Keyword.isActive == True,
        )
    ).all()
    for keyword_row in keyword_rows:
        if keyword_row:
            if action in ("weekly_serp", "weekly", "automatic"):
                keyword_row.weeklyRefreshStatus = "processing"

            keyword_row.processingTimeoutAt = datetime.utcnow() + timedelta(
                hours=PROCESSING_TIMEOUT_HOURS
            )
            db.add(keyword_row)

    db.commit()
    _publish_cached_completion_events(
        user_id,
        project_id,
        completed_cached_keywords,
    )

    logger.info(
        "Submitted %s RefreshJob %s with %d task(s) for %d keyword(s)",
        action, refresh_job.id, len(all_task_ids), len(keyword_texts)
    )

    return {
        "refresh_job_id": refresh_job.id,
        "task_ids": all_task_ids,
        "submitted": submitted_keywords,
        "failed_chunks": failed_chunks,
        "cached_count": len(cached_results),
        "accepted": bool(cached_results or accepted_uncached_keywords),
        "accepted_keywords": list(cached_results) + accepted_uncached_keywords,
        "completed_keywords": completed_cached_keywords,
        "failed_keywords": failed_keywords,
    }

def _publish_cached_completion_events(
    user_id: str,
    project_id: str,
    completed_keywords: list[str],
) -> None:
    for keyword in completed_keywords:
        publish_keyword_update(
            user_id=user_id,
            project_id=project_id,
            keyword=keyword,
            status="success",
        )


def _apply_cached_results( db: Session, project_id: str, user_id: str, domain: str, cached_results: dict, refresh_job_id: str ) -> list[str]:
    now = datetime.utcnow()
    deduplication_keys = {
        kw_text: f"cached:{refresh_job_id}:{kw_text}"
        for kw_text in cached_results
    }
    existing_deduplication_keys = set(
        db.scalars(
            select(ProcessingJob.deduplicationKey).where(
                ProcessingJob.deduplicationKey.in_(
                    list(deduplication_keys.values())
                )
            )
        ).all()
    )
    keyword_rows = db.scalars(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword.in_(list(cached_results)),
            Keyword.isActive == True,
        )
    ).all()
    rows_by_keyword = {row.keyword: row for row in keyword_rows}
    completed_keywords = []

    for kw_text, cached in cached_results.items():
        deduplication_key = deduplication_keys[kw_text]
        if deduplication_key in existing_deduplication_keys:
            completed_keywords.append(kw_text)
            continue

        keyword_row = rows_by_keyword.get(kw_text)
        if not keyword_row:
            continue

        organic_items = cached.get("organic_items", []) or []
        position = None
        url = None
        target_domain = _normalize_domain(domain)

        for item in organic_items:
            if item.get("type") != "organic":
                continue

            item_domain = _normalize_domain(
                item.get("domain")
                or item.get("url")
                or ""
            )

            if (
                item_domain == target_domain
                or item_domain.endswith("." + target_domain)
            ):
                position = (
                    item.get("rank_group")
                    or item.get("rank_absolute")
                )
                url = item.get("url")
                break

        ai_overview = None
        ai_description = None

        for item in cached.get("items", []) or []:
            if item.get("type") not in ("ai_overview", "ai_answer"):
                continue

            references = (
                item.get("ai_overview_reference")
                or item.get("references")
                or []
            )

            for ref in references:
                if not isinstance(ref, dict):
                    continue

                ref_domain = _normalize_domain(
                    ref.get("domain")
                    or ref.get("source_domain")
                    or ref.get("url")
                    or ""
                )

                if (
                    ref_domain == target_domain
                    or ref_domain.endswith("." + target_domain)
                ):
                    ai_overview = item
                    ai_description = (
                        item.get("description")
                        or item.get("content")
                    )
                    break

            if ai_overview:
                break

        keyword_row.position = position
        keyword_row.visibility = _dfs_visibility(position)
        keyword_row.check_url = url
        if ai_overview and not keyword_row.ai_badge:
            keyword_row.ai_badge = "AIO"
        if ai_description and not keyword_row.ai_description:
            keyword_row.ai_description = ai_description
        keyword_row.updatedAt = now
        keyword_row.lastWeeklyRefreshAt = now
        keyword_row.weeklyRefreshStatus = "success"
        keyword_row.processingTimeoutAt = None
        db.add(keyword_row)

        rank_result = RankResult(
            projectId=project_id,
            keywordText=kw_text,
            position=position,
            url=url,
            device="desktop",
            location=keyword_row.location or "India",
            checkedAt=now,
            keywordId=keyword_row.id,
        )
        db.add(rank_result)

        processing_job = ProcessingJob(
            refreshJobId=refresh_job_id,
            keywordText=kw_text,
            location=keyword_row.location or "India",
            status="success",
            deduplicationKey=deduplication_key,
            payload=json.dumps({
                "position": position,
                "url": url,
                "has_aio_badge": keyword_row.ai_badge,
                "ai_description": keyword_row.ai_description,
                "cached": True,
            }),
        )
        db.add(processing_job)
        completed_keywords.append(kw_text)

    db.flush()
    return completed_keywords


def _dfs_visibility(position):
    if position is None or position > 100:
        return 0.0
    if 1 <= position <= 10:
        return round(1.0 - (position - 1) * 0.1, 2)
    if 11 <= position <= 20:
        return 0.05
    return 0.0


def recover_missed_callback_results(
    db: Session,
    *,
    now: datetime | None = None,
) -> dict:
    """Retrieve already-paid SERP tasks whose callbacks missed the grace window."""
    from app.services.serp_result_ingestion import ingest_dataforseo_task_result

    now = now or datetime.utcnow()
    grace_cutoff = now - timedelta(minutes=CALLBACK_RECOVERY_GRACE_MINUTES)
    candidates = db.scalars(
        select(RefreshJob).where(
            RefreshJob.jobType.in_(["add_keyword", "bulk_add", "manual_refresh"]),
            RefreshJob.status == "submitted",
            RefreshJob.createdAt <= grace_cutoff,
            RefreshJob.processingTimeoutAt.is_not(None),
            RefreshJob.processingTimeoutAt > now,
        )
    ).all()

    stats = {
        "jobs": len(candidates),
        "retrieved": 0,
        "recovered": 0,
        "not_ready": 0,
        "errors": 0,
        "queue_enqueues": 0,
    }

    for refresh_job in candidates:
        try:
            summary = json.loads(refresh_job.resultSummary or "{}")
        except Exception:
            summary = {}

        processed_task_ids = set(summary.get("processed_task_ids") or [])
        try:
            task_ids = json.loads(refresh_job.dataforseoRequestIds or "[]")
        except Exception:
            task_ids = []
        if not isinstance(task_ids, list):
            task_ids = []

        waiting_children = []
        for child in db.scalars(
            select(ProcessingJob).where(
                ProcessingJob.refreshJobId == refresh_job.id,
                ProcessingJob.status.in_(["pending", "processing", "retry"]),
            )
        ).all():
            try:
                child_payload = json.loads(child.payload or "{}")
            except Exception:
                child_payload = {}
            if child_payload.get("awaiting_callback") is True:
                waiting_children.append(child)

        if not waiting_children:
            continue

        recovery_state = summary.get("callback_recovery")
        if not isinstance(recovery_state, dict):
            recovery_state = {}

        for task_id in task_ids:
            if not isinstance(task_id, str) or not task_id or task_id in processed_task_ids:
                continue

            task_state = recovery_state.get(task_id)
            if not isinstance(task_state, dict):
                task_state = {}
            last_attempt_at = task_state.get("last_attempt_at")
            if last_attempt_at:
                try:
                    last_attempt = datetime.fromisoformat(last_attempt_at)
                except (TypeError, ValueError):
                    last_attempt = None
                if (
                    last_attempt is not None
                    and now - last_attempt
                    < timedelta(minutes=CALLBACK_RECOVERY_RETRY_MINUTES)
                ):
                    continue

            task_state["attempts"] = int(task_state.get("attempts") or 0) + 1
            task_state["last_attempt_at"] = now.isoformat()
            task_state["last_outcome"] = "retrieving"
            recovery_state[task_id] = task_state
            summary["callback_recovery"] = recovery_state
            refresh_job.resultSummary = json.dumps(summary)
            db.add(refresh_job)
            db.commit()

            stats["retrieved"] += 1
            response = DataForSEOClient._retrieve_task_result(
                task_id,
                result_type="regular",
            )

            outcome = "error"
            matching_tasks = []
            if isinstance(response, dict) and response.get("status_code", 20000) == 20000:
                response_tasks = response.get("tasks") or []
                if isinstance(response_tasks, list):
                    matching_tasks = [
                        task
                        for task in response_tasks
                        if isinstance(task, dict) and task.get("id") == task_id
                    ]
                if matching_tasks:
                    task_result = matching_tasks[0]
                    task_data = task_result.get("data") or {}
                    result_list = task_result.get("result")
                    result_keyword = (
                        task_data.get("keyword")
                        if isinstance(task_data, dict)
                        else None
                    )
                    if (
                        task_result.get("status_code", 20000) == 20000
                        and isinstance(result_list, list)
                        and result_list
                        and isinstance(result_list[0], dict)
                        and result_keyword
                        and any(
                            child.keywordText == result_keyword
                            for child in waiting_children
                        )
                    ):
                        outcome = "ready"
                    else:
                        outcome = "not_ready"

            if outcome == "ready":
                ingestion = ingest_dataforseo_task_result(
                    db,
                    task_id,
                    matching_tasks,
                )
                if ingestion["updated"] > 0:
                    stats["recovered"] += 1
                if ingestion.get("queue_enqueued"):
                    stats["queue_enqueues"] += 1
            elif outcome == "not_ready":
                stats["not_ready"] += 1
            else:
                stats["errors"] += 1

            db.refresh(refresh_job)
            try:
                summary = json.loads(refresh_job.resultSummary or "{}")
            except Exception:
                summary = {}
            recovery_state = summary.get("callback_recovery")
            if not isinstance(recovery_state, dict):
                recovery_state = {}
            task_state = recovery_state.get(task_id)
            if not isinstance(task_state, dict):
                task_state = {}
            task_state["last_outcome"] = outcome
            recovery_state[task_id] = task_state
            summary["callback_recovery"] = recovery_state
            refresh_job.resultSummary = json.dumps(summary)
            db.add(refresh_job)
            db.commit()

            if outcome == "ready":
                processed_task_ids.add(task_id)

    return stats


def recover_stale_user_tracking_jobs(db: Session) -> dict:
    """Fail timed-out user submissions that never received a provider callback."""
    now = datetime.utcnow()
    stale_jobs = db.scalars(
        select(RefreshJob).where(
            RefreshJob.jobType.in_(["add_keyword", "bulk_add", "manual_refresh"]),
            RefreshJob.status == "submitted",
            RefreshJob.processingTimeoutAt.is_not(None),
            RefreshJob.processingTimeoutAt <= now,
        )
    ).all()

    timed_out_count = 0
    refunded_total = 0.0

    for refresh_job in stale_jobs:
        try:
            summary = json.loads(refresh_job.resultSummary or "{}")
        except Exception:
            summary = {}

        children = db.scalars(
            select(ProcessingJob).where(
                ProcessingJob.refreshJobId == refresh_job.id
            )
        ).all()
        waiting_children = []
        for child in children:
            if child.status not in ("pending", "processing", "retry"):
                continue
            try:
                payload = json.loads(child.payload or "{}")
            except Exception:
                payload = {}
            if payload.get("awaiting_callback") is True:
                waiting_children.append(child)

        if not waiting_children:
            # Results are already durable; give the worker another recovery window.
            refresh_job.processingTimeoutAt = now + timedelta(hours=1)
            db.add(refresh_job)
            continue

        waiting_keywords = [child.keywordText for child in waiting_children]
        for child in waiting_children:
            child.status = "failed"
            child.processingTimeoutAt = None
            child.updatedAt = now
            db.add(child)

        project_id = summary.get("project_id")
        if project_id:
            keyword_rows = db.scalars(
                select(Keyword).where(
                    Keyword.projectId == project_id,
                    Keyword.keyword.in_(waiting_keywords),
                )
            ).all()
            for keyword_row in keyword_rows:
                keyword_row.processingTimeoutAt = None
                if keyword_row.weeklyRefreshStatus == "processing":
                    keyword_row.weeklyRefreshStatus = "failed"
                keyword_row.updatedAt = now
                db.add(keyword_row)

        refund_amount = float(
            len(waiting_children) * (summary.get("cost_per_keyword") or 0)
        )
        if (
            refund_amount > 0
            and summary.get("user_id")
            and summary.get("credit_reference")
        ):
            refund_reserved(
                db=db,
                user_id=summary["user_id"],
                reference=summary["credit_reference"],
                amount=refund_amount,
                description=f"Refund: timed out callbacks for {refresh_job.jobType}",
                project_id=project_id,
            )
            refunded_total += refund_amount

        timed_out_count += len(waiting_children)
        active_children = [
            child
            for child in children
            if child.status in ("pending", "processing", "retry")
        ]
        summary["callback_timeout_count"] = (
            int(summary.get("callback_timeout_count", 0))
            + len(waiting_children)
        )
        refresh_job.resultSummary = json.dumps(summary)

        if active_children:
            refresh_job.processingTimeoutAt = now + timedelta(hours=1)
        else:
            refresh_job.status = "failed"
            refresh_job.processingTimeoutAt = None
            refresh_job.completedAt = now
        db.add(refresh_job)

    db.commit()
    return {
        "jobs": len(stale_jobs),
        "callbacks_timed_out": timed_out_count,
        "refunded": refunded_total,
    }


def get_user_processing_jobs(db: Session, user_id: str, project_id: str) -> list[dict]:
    job_rows = db.execute(
        select(ProcessingJob, Keyword)
        .join(RefreshJob, ProcessingJob.refreshJobId == RefreshJob.id)
        .join(
            Keyword,
            and_(
                Keyword.projectId == project_id,
                Keyword.userId == user_id,
                Keyword.isActive == True,
                Keyword.keyword == ProcessingJob.keywordText,
                func.coalesce(Keyword.location, "India") == ProcessingJob.location,
            ),
        )
        .where(RefreshJob.jobType.in_(["add_keyword", "bulk_add", "manual_refresh"]))
        .where(ProcessingJob.status.in_(["pending", "processing", "retry"]))
        .order_by(ProcessingJob.createdAt.asc())
    ).all()

    results = []
    for job, keyword_row in job_rows:
        try:
            payload = json.loads(job.payload or "{}")
        except Exception:
            payload = {}

        if payload.get("project_id") != project_id or payload.get("user_id") != user_id:
            continue

        results.append({
            "id": job.id,
            "refresh_job_id": job.refreshJobId,
            "keyword": job.keywordText,
            "location": job.location,
            "status": job.status,
            "action": payload.get("action"),
            "created_at": job.createdAt.isoformat() if job.createdAt else None,
            "updated_at": job.updatedAt.isoformat() if job.updatedAt else None,
            "keyword_id": keyword_row.id if keyword_row else None,
            "position": keyword_row.position if keyword_row else None,
            "check_url": keyword_row.check_url if keyword_row else None,
            "ai_badge": keyword_row.ai_badge if keyword_row else None,
            "volume": keyword_row.volume if keyword_row else None,
            "kd": keyword_row.kd if keyword_row else None,
            "cpc": keyword_row.cpc if keyword_row else None,
            "competition": keyword_row.competition if keyword_row else None,
            "backlinks": keyword_row.backlinks if keyword_row else None,
            "referring_domains": keyword_row.referring_domains if keyword_row else None,
            "intent": keyword_row.intent if keyword_row else None,
        })

    return results
