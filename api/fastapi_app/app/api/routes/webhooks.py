import logging
import json
import gzip
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import select

from app.core.config import get_settings
from app.services.payment_service import razorpay_client
from app.db.models import User, PaymentOrder, Subscription, CreditLedger, TopUpPackage
from app.db.session import SessionLocal
from app.services.plan_service import PLAN_DEFINITIONS, PLAN_ID_TO_KEY
from app.services import email_service
from app.services.credit_service import deduct_credits
from app.services.serp_result_ingestion import (
    _aio_cites_target_domain,
    _domain_matches,
    _find_refresh_job_by_task_id,
    ingest_dataforseo_task_result,
)
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
settings = get_settings()

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
        result = ingest_dataforseo_task_result(db, task_id, tasks)
        result.pop("queue_enqueued", None)
        return result
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
