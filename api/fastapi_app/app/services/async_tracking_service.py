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

from sqlalchemy import select, func, or_
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
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PROCESSING_TIMEOUT_HOURS = 24


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
        return {"refresh_job_id": None, "task_ids": [], "submitted": [], "failed_chunks": 0}

    priority = get_serp_priority(action)
    postback_url = _build_postback_url()

    keyword_texts = [kw.get("keyword", "").strip() for kw in keywords if kw.get("keyword")]
    keyword_texts = [kw for kw in keyword_texts if kw]
    if not keyword_texts:
        return {"refresh_job_id": None, "task_ids": [], "submitted": [], "failed_chunks": 0}

    existing_pending = db.scalar(
        select(RefreshJob)
        .where(RefreshJob.jobType == action)
        .where(RefreshJob.status.in_(["queued", "processing", "submitted"]))
        .order_by(RefreshJob.createdAt.desc())
        .limit(1)
    )
    if existing_pending:
        try:
            result_summary = json.loads(existing_pending.resultSummary or "{}")
        except Exception:
            result_summary = {}
        existing_project_id = result_summary.get("project_id")
        if existing_project_id == project_id:
            logger.info("Reusing existing pending %s RefreshJob %s for project %s", action, existing_pending.id, project_id)
            return {
                "refresh_job_id": existing_pending.id,
                "task_ids": json.loads(existing_pending.dataforseoRequestIds or "[]"),
                "submitted": keyword_texts,
                "failed_chunks": 0,
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

    if cached_results:
        _apply_cached_results(
            db,
            project_id,
            user_id,
            domain,
            cached_results,
            refresh_job.id
        )

    if not uncached_keywords:
        refresh_job.status = "success"
        refresh_job.completedAt = datetime.utcnow()
        db.add(refresh_job)
        db.commit()
        return {
            "refresh_job_id": refresh_job.id,
            "task_ids": [],
            "submitted": [],
            "failed_chunks": 0,
            "cached_count": len(cached_results),
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
        return {
            "refresh_job_id": refresh_job.id,
            "task_ids": [],
            "submitted": [],
            "failed_chunks": failed_chunks,
        }

    existing_ids = json.loads(refresh_job.dataforseoRequestIds or "[]")
    existing_ids.extend(all_task_ids)
    refresh_job.dataforseoRequestIds = json.dumps(existing_ids)
    refresh_job.status = "submitted"
    refresh_job.processingTimeoutAt = datetime.utcnow() + timedelta(hours=PROCESSING_TIMEOUT_HOURS)
    db.add(refresh_job)

    for kw_text in uncached_keywords:
        deduplication_key = f"pending:{refresh_job.id}:{kw_text}:{location_code}"
        existing = db.scalar(
            select(ProcessingJob).where(ProcessingJob.deduplicationKey == deduplication_key)
        )
        if existing:
            continue
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
            }),
        )
        db.add(processing_job)

    db.commit()

    for kw_text in uncached_keywords:
        keyword_row = db.scalar(
            select(Keyword).where(
                Keyword.projectId == project_id,
                Keyword.keyword == kw_text,
                Keyword.isActive == True,
            )
        )
        if keyword_row:
            if action in ("weekly_serp", "weekly", "automatic"):
                keyword_row.weeklyRefreshStatus = "processing"

            keyword_row.processingTimeoutAt = datetime.utcnow() + timedelta(
                hours=PROCESSING_TIMEOUT_HOURS
            )
            db.add(keyword_row)

    db.commit()

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
    }

def _apply_cached_results( db: Session, project_id: str, user_id: str, domain: str, cached_results: dict, refresh_job_id: str ) -> None:
    now = datetime.utcnow()
    for kw_text, cached in cached_results.items():
        keyword_row = db.scalar(
            select(Keyword).where(
                Keyword.projectId == project_id,
                Keyword.keyword == kw_text,
                Keyword.isActive == True,
            )
        )
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

        deduplication_key = f"cached:{refresh_job_id}:{kw_text}"
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

    db.commit()


def _dfs_visibility(position):
    if position is None or position > 100:
        return 0.0
    if 1 <= position <= 10:
        return round(1.0 - (position - 1) * 0.1, 2)
    if 11 <= position <= 20:
        return 0.05
    return 0.0


def get_user_processing_jobs(db: Session, user_id: str, project_id: str) -> list[dict]:
    rows = db.execute(
        select(Keyword.keyword, Keyword.location).where(
            Keyword.projectId == project_id,
            Keyword.isActive == True,
        )
    ).all()

    keyword_keys = {(kw_text, kw_location or "India") for kw_text, kw_location in rows}
    if not keyword_keys:
        return []

    conditions = []
    for kw_text, location in keyword_keys:
        conditions.append(
            (ProcessingJob.keywordText == kw_text) & (ProcessingJob.location == location)
        )

    jobs = db.scalars(
        select(ProcessingJob)
        .join(RefreshJob, ProcessingJob.refreshJobId == RefreshJob.id)
        .where(RefreshJob.jobType.in_(["add_keyword", "bulk_add", "manual_refresh"]))
        .where(ProcessingJob.status.in_(["pending", "processing", "retry"]))
        .where(or_(*conditions))
        .order_by(ProcessingJob.createdAt.asc())
    ).all()

    results = []
    for job in jobs:
        try:
            payload = json.loads(job.payload or "{}")
        except Exception:
            payload = {}

        keyword_row = db.scalar(
            select(Keyword).where(
                Keyword.projectId == project_id,
                Keyword.keyword == job.keywordText,
            )
        )

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
