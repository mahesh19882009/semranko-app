import logging
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import get_settings
from app.services.payment_service import razorpay_client
from app.db.models import User, PaymentOrder, Subscription, CreditLedger
from app.db.session import SessionLocal
from app.services.plan_service import PLAN_DEFINITIONS, PLAN_ID_TO_KEY
from app.services import email_service

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
            return {"status": "ok"}

        payment_id = entity.get("id")
        if not payment_id:
            return {"status": "ok"}

        existing_ledger = db.scalar(
            select(CreditLedger).where(CreditLedger.relatedOrderId == order_id)
        )
        if existing_ledger:
            return {"status": "duplicate_ignored"}

        user = db.scalar(select(User).where(User.id == payment_order.userId))
        if not user:
            logger.error(f"User not found for payment order: {order_id}")
            return {"status": "ok"}

        if getattr(payment_order, "purchaseType", None) == "CREDIT_TOP_UP":
            multiplier = getattr(payment_order, "planId", 0)
            credits_to_add = int(multiplier) * 1000
            user.creditBalance = round(
                float(getattr(user, "creditBalance", 0.0) or 0.0) + credits_to_add, 2
            )
            db.add(user)

            ledger = CreditLedger(
                userId=user.id,
                ownerId=user.id,
                amount=float(credits_to_add),
                actionType="CREDIT_TOP_UP",
                description=f"Credit top-up: {credits_to_add} credits added via Razorpay payment",
                relatedOrderId=order_id,
                status="success",
            )
            db.add(ledger)

            payment_order.status = "paid"
            payment_order.razorpayPaymentId = payment_id
            db.add(payment_order)
            db.commit()

            email_service.send_payment_success_email(
                to_email=user.email,
                name=user.name,
                plan_name="Credit Top-Up",
                amount=float(payment_order.amount) / 100,
                order_id=order_id,
            )
        else:
            plan_id = payment_order.planId
            logger.info(f"[webhook] Calling activate_subscription user={user.id} plan_id={plan_id} order_id={order_id}")
            try:
                from app.services.payment_service import activate_subscription
                activate_subscription(
                    db=db,
                    user_id=user.id,
                    plan_id=plan_id,
                    payment_id=payment_id,
                    order_id=order_id,
                    billing_cycle="monthly"
                )
            except Exception as exc:
                logger.error(f"Webhook activate_subscription failed: {exc}")
            
            payment_order.status = "paid"
            payment_order.razorpayPaymentId = payment_id
            db.add(payment_order)
            db.commit()

            plan_key = PLAN_ID_TO_KEY.get(plan_id, "starter")
            plan_name = PLAN_DEFINITIONS.get(plan_key, {}).get("name", "Unknown")
            email_service.send_payment_success_email(
                to_email=user.email,
                name=user.name,
                plan_name=plan_name,
                amount=float(payment_order.amount) / 100,
                order_id=order_id,
            )

        return {"status": "ok"}
    except Exception as exc:
        db.rollback()
        logger.exception(f"Razorpay webhook processing failed: {exc}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")
    finally:
        db.close()


@router.post("/dataforseo")
async def dataforseo_webhook(request: Request):
    """Receive DataForSEO pingback callbacks when SERP tasks complete."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    task_id = data.get("task_id") or data.get("id") or request.query_params.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="Missing task_id")

    logger.info(f"DataForSEO webhook received: task_id={task_id}")

    result_type = data.get("result_type", "regular")

    serp_data = DataForSEOClient._retrieve_task_result(task_id, result_type)
    if serp_data:
        keyword_text = serp_data.get("keyword", "")
        location = serp_data.get("location", "India")
        device = serp_data.get("device", "desktop")
        parsed = DataForSEOClient._parse_serp_result(serp_data)
        if parsed:
            for kw_text, parsed_data in parsed.items():
                set_cached("serp", ("serp", kw_text, location, device), parsed_data, ttl_seconds=3600)
            logger.info(f"DataForSEO webhook cached results: task_id={task_id} keywords={len(parsed)}")
        return {"success": True, "message": f"Task {task_id} results cached"}
    else:
        logger.warning(f"DataForSEO webhook: no results for task_id={task_id}")
        return {"success": True, "message": f"Task {task_id} no results yet"}
