import logging
import json
import re
import gzip
from datetime import datetime, timedelta
from app.queues.rank_check_queue import get_rank_check_queue
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import get_settings
from app.services.dataforseo_client import LOCATION_MAP, _log_dataforseo_cost, _build_serp_cache_key, _set_cached_serp
from app.services.payment_service import razorpay_client
from app.db.models import User, PaymentOrder, Subscription, CreditLedger, Keyword, RankResult, Project, AsyncTaskQueue, SerpFeature, TrackedKeyword, PendingWebhookCredit, RefreshJob, ProcessingJob, TopUpPackage
from app.db.session import SessionLocal
from app.services.plan_service import PLAN_DEFINITIONS, PLAN_ID_TO_KEY
from app.services import email_service
from app.services.credit_service import deduct_credits
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
settings = get_settings()

LOCATION_CODE_MAP = {v: k for k, v in LOCATION_MAP.items()}


def _dfs_visibility(position):
    if position is None or position > 100:
        return 0.0
    if 1 <= position <= 10:
        return round(1.0 - (position - 1) * 0.1, 2)
    if 11 <= position <= 20:
        return 0.05
    return 0.0


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/razorpay")
async def razorpay_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing Razorpay signature")

    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.warning("Razorpay webhook secret not configured")
        raise HTTPException(status_code=400, detail="Webhook secret not configured")

    if not razorpay_client:
        logger.warning("Razorpay client not initialized")
        raise HTTPException(status_code=400, detail="Razorpay not configured")

    try:
        razorpay_client.utility.verify_webhook_signature(
            raw_body.decode("utf-8"),
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET,
        )
    except Exception as exc:
        logger.error(f"Razorpay webhook signature verification failed: {exc}")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event")
    logger.info(f"Razorpay webhook received: event={event}")

    if event not in ("order.paid", "payment.captured"):
        return {"status": "ok"}

    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity")
    order_entity = payload.get("payload", {}).get("order", {}).get("entity")
    entity = order_entity or payment_entity
    if not entity:
        return {"status": "ok"}

    order_id = entity.get("order_id") or entity.get("id")
    if not order_id:
        return {"status": "ok"}

    db = SessionLocal()
    try:
        payment_order = db.scalar(
            select(PaymentOrder).where(PaymentOrder.razorpayOrderId == order_id)
        )
        if not payment_order:
            logger.warning(f"PaymentOrder not found for order_id={order_id}")
            return {"status": "ok"}

        if payment_order.status == "paid":
            existing_subscription = db.scalar(
                select(Subscription).where(
                    Subscription.userId == payment_order.userId,
                    Subscription.isActive == True
                )
            )
            if not existing_subscription or existing_subscription.razorpayOrderId != order_id:
                logger.info(f"[webhook] Payment already paid but subscription may not be activated, reprocessing")
            else:
                return {"status": "ok"}

        payment_id = entity.get("id")
        if not payment_id:
            return {"status": "ok"}

        is_credit_top_up = getattr(payment_order, "purchaseType", None) == "CREDIT_TOP_UP"
        existing_ledger = db.scalar(
            select(CreditLedger).where(CreditLedger.relatedOrderId == order_id)
        )
        if existing_ledger and not is_credit_top_up:
            return {"status": "duplicate_ignored"}
        if (
            existing_ledger
            and is_credit_top_up
            and existing_ledger.creditPool == "purchased"
            and existing_ledger.status == "completed"
        ):
            return {"status": "duplicate_ignored"}

        user = db.scalar(select(User).where(User.id == payment_order.userId))
        if not user:
            logger.error(f"User not found for payment order: {order_id}")
            return {"status": "ok"}

        if is_credit_top_up:
            package = db.scalar(select(TopUpPackage).where(TopUpPackage.id == payment_order.topUpPackageId)) if payment_order.topUpPackageId else None
            credits_to_add = package.credits if package else int(payment_order.planId) * settings.CREDIT_TOP_UP_CONFIG.get("credits_per_100_inr", 600)
            payment_order.status = "paid"
            payment_order.razorpayPaymentId = payment_id
            db.add(payment_order)
            db.commit()
            from app.services.credit_service import add_purchased_credits
            add_purchased_credits(db, user.id, credits_to_add, "Credit top-up via Razorpay payment", order_id)

            logger.info(f"[webhook] Credit top-up processed: user={user.id} credits_added={credits_to_add}")

            email_service.send_payment_success_email(
                to_email=user.email,
                name=user.name,
                plan_name="Credit Top-Up",
                amount=float(payment_order.amount) / 100,
                order_id=order_id,
            )
        else:
            plan_id = payment_order.planId
            logger.info(f"[webhook] Processing subscription payment user={user.id} plan_id={plan_id} order_id={order_id}")

            try:
                from app.services.payment_service import activate_subscription
                subscription = activate_subscription(
                    db=db,
                    user_id=user.id,
                    plan_id=plan_id,
                    payment_id=payment_id,
                    order_id=order_id,
                    billing_cycle="monthly"
                )
                logger.info(f"[webhook] activate_subscription succeeded subscription_id={subscription.id} plan_id={subscription.planId} status={subscription.status}")
            except Exception as exc:
                logger.error("[webhook] activate_subscription failed: %s", exc)
                payment_order.status = "paid"
                payment_order.razorpayPaymentId = payment_id
                db.add(payment_order)
                db.commit()
                raise

            payment_order.status = "paid"
            payment_order.razorpayPaymentId = payment_id
            db.add(payment_order)
            db.commit()

            plan_key = PLAN_ID_TO_KEY.get(plan_id, "starter")
            plan_name = PLAN_DEFINITIONS.get(plan_key, {}).get("name", "Unknown")
            logger.info(f"[webhook] Subscription upgrade complete: user={user.id} plan={plan_name}")

            email_service.send_payment_success_email(
                to_email=user.email,
                name=user.name,
                plan_name=plan_name,
                amount=float(payment_order.amount) / 100,
                order_id=order_id,
            )

        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Razorpay webhook processing failed: %s", exc)
        raise HTTPException(status_code=500, detail="Webhook processing failed")
    finally:
        db.close()

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


def _domain_matches(target_domain: str, item_domain: str = "", item_url: str = "") -> bool:
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


@router.post("/dataforseo")
async def dataforseo_webhook(request: Request):
    """Receive completed DataForSEO SERP postbacks."""
    settings = get_settings()

    if settings.DATAFORSEO_WEBHOOK_SECRET:
        webhook_secret = request.query_params.get("secret")
        if webhook_secret != settings.DATAFORSEO_WEBHOOK_SECRET:
            logger.warning("DataForSEO webhook rejected: invalid or missing secret")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        raw_body = await request.body()

        if request.headers.get("content-encoding", "").lower() == "gzip":
            raw_body = gzip.decompress(raw_body)

        data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception as exc:
        logger.exception("Failed to decode DataForSEO postback: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid DataForSEO payload")

    task_id = (
        data.get("task_id")
        or data.get("id")
        or request.query_params.get("task_id")
    )

    if not task_id:
        raise HTTPException(status_code=400, detail="Missing task_id")

    logger.info("DataForSEO webhook received: task_id=%s", task_id)

    tasks = data.get("tasks", []) or []
    if not tasks:
        logger.warning(
            "DataForSEO webhook: no tasks in payload for task_id=%s",
            task_id,
        )
        return {
            "success": True,
            "message": f"Task {task_id} no tasks in payload",
        }

    db = SessionLocal()

    try:
        refresh_job = db.scalar(
            select(RefreshJob).where(
                RefreshJob.dataforseoRequestIds.contains(task_id)
            )
        )

        if not refresh_job:
            async_task = db.scalar(
                select(AsyncTaskQueue).where(
                    AsyncTaskQueue.id == task_id
                )
            )

            if not async_task:
                logger.warning(
                    "DataForSEO webhook rejected: task_id=%s not found",
                    task_id,
                )
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

            # The tracking service already created this job before DFS submission.
            existing_tracking_job = db.scalar(
                select(ProcessingJob).where(
                    ProcessingJob.refreshJobId == (
                        refresh_job.id if refresh_job else ""
                    ),
                    ProcessingJob.keywordText == current_keyword,
                    ProcessingJob.status.in_(
                        ["pending", "processing", "retry"]
                    ),
                )
            )

            # Duplicate postback after the job was already completed.
            if not existing_tracking_job:
                already_processed = db.scalar(
                    select(ProcessingJob).where(
                        ProcessingJob.deduplicationKey
                        == f"{task_id}:{current_keyword}:{location_name}"
                    )
                )

                if already_processed:
                    skipped_count += 1
                    continue

                logger.warning(
                    "No pending ProcessingJob found: task=%s keyword=%s",
                    task_id,
                    current_keyword,
                )
                skipped_count += 1
                continue

            try:
                existing_payload = json.loads(
                    existing_tracking_job.payload or "{}"
                )
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
                    # Organic rank must belong to the project's target domain.
                    for item in serp_items:
                        if not isinstance(item, dict):
                            continue

                        if item.get("type") != "organic":
                            continue

                        if _domain_matches(
                            target_domain,
                            item.get("domain") or "",
                            item.get("url") or "",
                        ):
                            detected_position = (
                                item.get("rank_group")
                                or item.get("rank_absolute")
                            )
                            detected_url = item.get("url")
                            break

                    # Local Pack rank must belong to the project's target domain.
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
                                item.get("rank_group")
                                or item.get("rank_absolute")
                            )
                            local_pack_url = item.get("url")
                            break

                    # AIO must also cite the target domain.
                    for item in serp_items:
                        if not isinstance(item, dict):
                            continue

                        if item.get("type") != "ai_overview":
                            continue

                        if _aio_cites_target_domain(
                            target_domain,
                            item,
                        ):
                            has_aio_badge = "AIO"
                            ai_description = (
                                item.get("description")
                                or item.get("content")
                            )
                            break

                        if _aio_cites_target_domain(
                            target_domain,
                            item,
                        ):
                            has_aio_badge = "AIO"
                            ai_description = (
                                item.get("description")
                                or item.get("content")
                            )
                            break

            position_int = None

            if (
                detected_position is not None
                and str(detected_position)
                .replace(".", "", 1)
                .isdigit()
            ):
                position_int = int(float(detected_position))

            # Keep all submission metadata already stored in the job.
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
                
            })

            existing_tracking_job.payload = json.dumps(existing_payload)
            existing_tracking_job.deduplicationKey = (
                f"{task_id}:{current_keyword}:{location_name}"
            )

            db.add(existing_tracking_job)
            updated_count += 1

        db.commit()

        if updated_count > 0:
            queue = get_rank_check_queue()
            queue.enqueue(
                "app.workers.tasks.process_refresh_jobs",
                job_timeout="600",
            )

        if refresh_job:
            result_data = json.loads(
                refresh_job.resultSummary or "{}"
            )

            processed_task_ids = result_data.get(
                "processed_task_ids",
                [],
            )

            if task_id not in processed_task_ids:
                processed_task_ids.append(task_id)

            result_data["processed_task_ids"] = processed_task_ids
            refresh_job.resultSummary = json.dumps(result_data)

            db.add(refresh_job)
            db.commit()

        logger.info(
            "DataForSEO webhook stored: task_id=%s updated=%d skipped=%d",
            task_id,
            updated_count,
            skipped_count,
        )

        return {
            "success": True,
            "message": f"Task {task_id} result stored",
            "updated": updated_count,
            "skipped": skipped_count,
        }

    except HTTPException:
        raise

    except Exception as exc:
        db.rollback()
        logger.exception(
            "DataForSEO webhook processing failed: %s",
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail="Webhook processing failed",
        )

    finally:
        db.close()

@router.get("/refresh-status")
async def get_refresh_status(current_user: dict = Depends(get_current_user)):
    """Get refresh job status for weekly and monthly tracking."""
    db = SessionLocal()
    try:
        from app.services.async_bulk_service import get_refresh_status
        return get_refresh_status(db)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get refresh status: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to get refresh status")
    finally:
        db.close()
