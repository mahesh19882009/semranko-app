import logging
import json
import re
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import get_settings
from app.services.dataforseo_client import LOCATION_MAP
from app.services.payment_service import razorpay_client
from app.db.models import User, PaymentOrder, Subscription, CreditLedger, Keyword
from app.db.session import SessionLocal
from app.services.plan_service import PLAN_DEFINITIONS, PLAN_ID_TO_KEY
from app.services import email_service

logger = logging.getLogger(__name__)
settings = get_settings()

LOCATION_CODE_MAP = {v: k for k, v in LOCATION_MAP.items()}

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
            # Check if subscription was activated - if not, try to activate it
            from app.db.models import Subscription
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
            from app.core.config import get_settings
            settings = get_settings()
            multiplier = getattr(payment_order, "planId", 0)
            credits_per_unit = settings.CREDIT_TOP_UP_CONFIG.get("credits_per_100_inr", 600)
            credits_to_add = int(multiplier) * credits_per_unit
            user.creditBalance = round(
                float(getattr(user, "creditBalance", 0.0) or 0.0) + credits_to_add, 2
            )
            db.add(user)

            ledger = CreditLedger(
                userId=user.id,
                ownerId=user.id,
                amount=float(credits_to_add),
                actionType="CREDIT_TOP_UP",
                description="Credit top-up via Razorpay payment",
                relatedOrderId=order_id,
                status="success",
            )
            db.add(ledger)

            payment_order.status = "paid"
            payment_order.razorpayPaymentId = payment_id
            db.add(payment_order)
            db.commit()

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
            
            # Call activate_subscription to handle plan upgrade and credit allocation
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
                logger.error(f"[webhook] activate_subscription failed: {exc}")
                import traceback
                traceback.print_exc()
                # Still mark payment as paid even if activation fails
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

    tasks = data.get("tasks", []) or []
    if not tasks:
        logger.warning(f"DataForSEO webhook: no tasks in payload for task_id={task_id}")
        return {"success": True, "message": f"Task {task_id} no tasks in payload"}

    db = SessionLocal()
    try:
        updated_count = 0
        for task_data in tasks:
            if not task_data:
                continue

            current_keyword = task_data.get("data", {}).get("keyword")
            if not current_keyword:
                continue

            location = task_data.get("data", {}).get("location_code", 2840)
            location_name = LOCATION_CODE_MAP.get(location, "India")
            if isinstance(location, str) and location:
                location_name = location

            detected_position = None
            has_aio_badge = None
            keyword_difficulty = None
            cost_per_click = None
            competition_level = None
            search_intent = None
            backlinks_count = None
            referring_domains = None
            search_volume = None

            results_list = task_data.get("result", []) or []
            if isinstance(results_list, list) and len(results_list) > 0:
                first_block = results_list[0]

                keyword_properties = first_block.get("keyword_properties", {})
                if isinstance(keyword_properties, dict):
                    keyword_difficulty = keyword_properties.get("keyword_difficulty")
                    search_intent = keyword_properties.get("search_intent")

                keyword_info = first_block.get("keyword_info", {})
                if isinstance(keyword_info, dict):
                    search_volume = keyword_info.get("search_volume")
                    cost_per_click = keyword_info.get("cpc")
                    competition_level = keyword_info.get("competition")

                serp_items = first_block.get("items", []) or []
                if isinstance(serp_items, list):
                    for item in serp_items:
                        if not item:
                            continue

                        if item.get("type") == "organic" and item.get("url"):
                            detected_position = item.get("rank_group") or item.get("rank_absolute")

                        if item.get("type") == "ai_overview":
                            references = item.get("ai_overview_reference", []) or []
                            if isinstance(references, list):
                                for ref in references:
                                    if ref and ref.get("url"):
                                        has_aio_badge = "AIO"

            volume_int = None
            kd_int = None
            cpc_float = None
            competition_float = None
            backlinks_float = None
            referring_domains_float = None
            position_int = None

            if search_volume is not None and str(search_volume).replace(".", "", 1).isdigit():
                volume_int = int(float(search_volume))
            if keyword_difficulty is not None and str(keyword_difficulty).replace(".", "", 1).isdigit():
                kd_int = int(float(keyword_difficulty))
            if cost_per_click is not None and str(cost_per_click).replace(".", "", 1).isdigit():
                cpc_float = float(cost_per_click)
            if competition_level is not None and str(competition_level).replace(".", "", 1).isdigit():
                competition_float = float(competition_level)
            if backlinks_count is not None and str(backlinks_count).replace(".", "", 1).isdigit():
                backlinks_float = float(backlinks_count)
            if referring_domains is not None and str(referring_domains).replace(".", "", 1).isdigit():
                referring_domains_float = float(referring_domains)
            if detected_position is not None and str(detected_position).replace(".", "", 1).isdigit():
                position_int = int(float(detected_position))

            keyword_row = db.scalar(
                select(Keyword).where(Keyword.keyword == current_keyword)
            )
            if keyword_row:
                keyword_row.volume = volume_int
                keyword_row.kd = kd_int
                keyword_row.cpc = cpc_float
                keyword_row.competition = competition_float
                keyword_row.backlinks = backlinks_float
                keyword_row.referring_domains = referring_domains_float
                keyword_row.intent = search_intent
                keyword_row.position = position_int
                keyword_row.ai_badge = has_aio_badge
                ai_description = row.get("ai_description")
                if isinstance(ai_description, str):
                    ai_description = re.sub(r'\.{3}\s*Read more$', '', ai_description.strip()) or None
                keyword_row.ai_description = ai_description
                keyword_row.updatedAt = datetime.utcnow()

            updated_count += 1

        db.commit()
        logger.info(
            "DataForSEO webhook processed: task_id=%s updated_keywords=%d",
            task_id,
            updated_count,
        )
        return {"success": True, "message": f"Task {task_id} processed", "updated_keywords": updated_count}
    except Exception as exc:
        db.rollback()
        logger.exception(f"DataForSEO webhook processing failed: {exc}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")
    finally:
        db.close()
