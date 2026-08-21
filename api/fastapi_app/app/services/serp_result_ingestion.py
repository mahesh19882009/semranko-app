"""Internal persistence path shared by SERP callbacks and task-get recovery."""

import json
import logging

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AsyncTaskQueue, ProcessingJob, RefreshJob
from app.queues.rank_check_queue import get_rank_check_queue
from app.services.dataforseo_client import LOCATION_MAP

logger = logging.getLogger(__name__)

LOCATION_CODE_MAP = {value: key for key, value in LOCATION_MAP.items()}


def _find_refresh_job_by_task_id(db: Session, task_id: str):
    """Return only a RefreshJob whose serialized task-id list contains an exact match."""
    candidates = db.scalars(
        select(RefreshJob).where(
            RefreshJob.dataforseoRequestIds.contains(task_id)
        )
    ).all()

    for candidate in candidates:
        try:
            task_ids = json.loads(candidate.dataforseoRequestIds or "[]")
        except Exception:
            continue
        if isinstance(task_ids, list) and task_id in task_ids:
            return candidate

    return None


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


def _domain_matches(
    target_domain: str,
    item_domain: str = "",
    item_url: str = "",
) -> bool:
    target = _normalize_domain(target_domain)
    if not target:
        return False
    candidate = _normalize_domain(item_domain)
    if not candidate and item_url:
        candidate = _normalize_domain(item_url)
    if not candidate:
        return False
    return candidate == target or candidate.endswith("." + target)


def _aio_cites_target_domain(target_domain: str, item: dict) -> bool:
    references = (
        item.get("ai_overview_reference")
        or item.get("references")
        or []
    )
    if not isinstance(references, list):
        return False
    for ref in references:
        if not isinstance(ref, dict):
            continue
        if _domain_matches(
            target_domain,
            ref.get("domain") or ref.get("source_domain") or "",
            ref.get("url") or "",
        ):
            return True
    return False


def _make_processing_job_worker_ready(
    processing_job: ProcessingJob,
    *,
    task_id: str,
    task_data: dict,
    current_keyword: str,
    location_code,
    location_name: str,
) -> None:
    """Apply one provider result to one project-specific child job."""
    try:
        existing_payload = json.loads(processing_job.payload or "{}")
    except Exception:
        existing_payload = {}

    target_domain = existing_payload.get("domain") or ""
    detected_position = None
    detected_url = None
    local_pack_position = None
    local_pack_url = None
    has_aio_badge = None
    ai_description = None
    first_block = None

    results_list = task_data.get("result") or []
    if isinstance(results_list, list) and results_list:
        first_block = results_list[0]
        serp_items = first_block.get("items") or []
        if isinstance(serp_items, list):
            for item in serp_items:
                if not isinstance(item, dict) or item.get("type") != "organic":
                    continue
                if _domain_matches(
                    target_domain,
                    item.get("domain") or "",
                    item.get("url") or "",
                ):
                    detected_position = (
                        item.get("rank_group") or item.get("rank_absolute")
                    )
                    detected_url = item.get("url")
                    break

            for item in serp_items:
                if not isinstance(item, dict):
                    continue
                if item.get("type") not in (
                    "local_pack",
                    "map",
                    "local_services",
                ):
                    continue
                if _domain_matches(
                    target_domain,
                    item.get("domain") or "",
                    item.get("url") or "",
                ):
                    local_pack_position = (
                        item.get("rank_group") or item.get("rank_absolute")
                    )
                    local_pack_url = item.get("url")
                    break

            for item in serp_items:
                if not isinstance(item, dict) or item.get("type") != "ai_overview":
                    continue
                if _aio_cites_target_domain(target_domain, item):
                    has_aio_badge = "AIO"
                    ai_description = item.get("description") or item.get("content")
                    break

    position_int = None
    if (
        detected_position is not None
        and str(detected_position).replace(".", "", 1).isdigit()
    ):
        position_int = int(float(detected_position))

    existing_payload.update({
        "position": position_int,
        "url": detected_url,
        "local_pack_position": (
            int(float(local_pack_position))
            if local_pack_position is not None
            else None
        ),
        "local_pack_url": local_pack_url,
        "has_aio_badge": has_aio_badge,
        "ai_description": ai_description,
        "task_id": task_id,
        "location_code": location_code,
        "first_block": first_block,
        "awaiting_callback": False,
    })
    processing_job.payload = json.dumps(existing_payload)
    processing_job.status = "pending"
    processing_job.deduplicationKey = (
        f"{task_id}:{current_keyword}:{location_name}:{processing_job.id}"
    )


def ingest_dataforseo_task_result(
    db: Session,
    task_id: str,
    tasks: list[dict],
    *,
    enqueue: bool = True,
) -> dict:
    """Persist a completed provider task using the canonical callback semantics."""
    refresh_job = _find_refresh_job_by_task_id(db, task_id)
    if not refresh_job:
        async_task = db.scalar(
            select(AsyncTaskQueue).where(AsyncTaskQueue.id == task_id)
        )
        if not async_task:
            logger.warning("DataForSEO result rejected: task_id=%s not found", task_id)
            raise HTTPException(status_code=404, detail="Task not found")

    updated_count = 0
    skipped_count = 0

    for task_data in tasks:
        if not task_data:
            continue

        task_info = task_data.get("data") or {}
        current_keyword = task_info.get("keyword")
        if not current_keyword:
            continue

        location_code = task_info.get("location_code", 2840)
        location_name = (
            LOCATION_CODE_MAP.get(location_code, "India")
            if isinstance(location_code, int)
            else (location_code or "India")
        )

        matching_tracking_jobs = db.scalars(
            select(ProcessingJob).where(
                ProcessingJob.refreshJobId == (
                    refresh_job.id if refresh_job else ""
                ),
                ProcessingJob.keywordText == current_keyword,
                ProcessingJob.status.in_(["pending", "processing", "retry"]),
            )
        ).all()

        callback_waiting_jobs = []
        for tracking_job in matching_tracking_jobs:
            try:
                tracking_payload = json.loads(tracking_job.payload or "{}")
            except Exception:
                tracking_payload = {}
            expected_task_ids = tracking_payload.get("task_ids")
            if (
                isinstance(expected_task_ids, list)
                and expected_task_ids
                and task_id not in expected_task_ids
            ):
                continue
            callback_waiting_jobs.append(tracking_job)

        if not callback_waiting_jobs:
            logger.warning(
                "No pending ProcessingJob found: task=%s keyword=%s",
                task_id,
                current_keyword,
            )
            skipped_count += 1
            continue

        for tracking_job in callback_waiting_jobs:
            _make_processing_job_worker_ready(
                tracking_job,
                task_id=task_id,
                task_data=task_data,
                current_keyword=current_keyword,
                location_code=location_code,
                location_name=location_name,
            )
            db.add(tracking_job)
            updated_count += 1

    db.commit()

    queue_enqueued = False
    if updated_count > 0 and enqueue:
        queue = get_rank_check_queue()
        queue.enqueue(
            "app.workers.tasks.process_refresh_jobs",
            job_timeout="600",
        )
        queue_enqueued = True

    if refresh_job:
        try:
            result_data = json.loads(refresh_job.resultSummary or "{}")
        except Exception:
            result_data = {}
        processed_task_ids = result_data.get("processed_task_ids", [])
        if task_id not in processed_task_ids:
            processed_task_ids.append(task_id)
        result_data["processed_task_ids"] = processed_task_ids
        refresh_job.resultSummary = json.dumps(result_data)
        db.add(refresh_job)
        db.commit()

    logger.info(
        "DataForSEO result stored: task_id=%s updated=%d skipped=%d",
        task_id,
        updated_count,
        skipped_count,
    )
    return {
        "success": True,
        "message": f"Task {task_id} result stored",
        "updated": updated_count,
        "skipped": skipped_count,
        "queue_enqueued": queue_enqueued,
    }
