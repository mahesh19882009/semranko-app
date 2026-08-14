import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

from app.core.security import get_current_user
from app.db.session import get_db
from app.db.models import User, Subscription, TopUpPackage
from app.services.payment_service import create_order, verify_payment_signature, activate_subscription
from app.services import email_service
from app.services.plan_service import PLAN_DEFINITIONS, build_usage_snapshot, get_plan_key
from app.services.credit_service import create_pending_ledger_entry, finalize_pending_ledger_entry, add_purchased_credits
from app.core.config import GST_RATE, get_settings
from app.services.commercial_config_service import ensure_commercial_config, plan_definitions

from decimal import Decimal, ROUND_HALF_UP

from app.schemas.common import ok

router = APIRouter(prefix="/payments", tags=["payments"])

PLAN_ID_TO_KEY = {0: "starter", 1: "pro", 2: "agency", 3: "enterprise"}
PLAN_KEY_TO_ID = {v: k for k, v in PLAN_ID_TO_KEY.items()}
GST_RATE = Decimal(str(GST_RATE))
def _build_invoice(
    order: "PaymentOrder",
    user_name: str,
    user_email: str,
    user_gstin: Optional[str] = None,
    user_gst_name: Optional[str] = None,
    user_gst_address: Optional[str] = None,
    user_gst_state: Optional[str] = None,
    user_gst_state_code: Optional[str] = None,
) -> dict:
    """Convert a PaymentOrder row into a structured invoice dict with GST breakdown.
    Failed transactions don't get invoice numbers."""
    plan_key = PLAN_ID_TO_KEY.get(order.planId, "starter")
    plan = PLAN_DEFINITIONS.get(plan_key, {})

    # Net amount actually paid by user (after credit deduction) in INR
    net_inr = Decimal(str(order.amount or 0)) / Decimal("100")
    
    # Credit applied in INR
    credit_inr = Decimal(str(getattr(order, "credit_applied_paise", 0) or 0)) / Decimal("100")
    
    # Gross plan price (net paid + credit applied)
    gross_inr = net_inr + credit_inr

    # Only calculate GST for successful transactions
    if order.status in ["paid", "captured"]:
        base_inr   = (net_inr / (Decimal("1") + GST_RATE)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        gst_inr    = (net_inr - base_inr).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        base_inr = Decimal("0")
        gst_inr = Decimal("0")

    # Only assign invoice_id for successful transactions
    invoice_id = order.id if order.status in ["paid", "captured"] else None

    return {
        "invoice_id":   invoice_id,
        "order_id":     order.razorpayOrderId,
        "payment_id":   order.razorpayPaymentId,
        "plan_key":     plan_key,
        "plan_name":    plan_key.capitalize(),
        "status":       order.status,
        "currency":     order.currency,
        "base_amount":  float(base_inr),
        "gst_amount":   float(gst_inr),
        "gst_rate":     18,
        "credit_applied": float(credit_inr),
        "total_amount": float(net_inr),
        "gross_amount": float(gross_inr),
        "date":         order.createdAt.isoformat() if order.createdAt else None,
        "user_name":    user_name,
        "user_email":   user_email,
        "user_gstin":   user_gstin,
        "user_gst_name": user_gst_name,
        "user_gst_address": user_gst_address,
        "user_gst_state": user_gst_state,
        "user_gst_state_code": user_gst_state_code,
    }


@router.post("/create-order")
async def create_payment_order(
    plan_id: int = Query(..., description="Plan ID to upgrade to"),
    amount: int = Query(0, description="Amount in smallest currency unit (e.g., paise) - server will override with plan price"),
    billing_cycle: str = Query("monthly", description="Billing cycle: monthly or yearly"),
    currency: str = Query("INR", description="Display/checkout currency requested by the customer"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Razorpay payment order for subscription upgrade.
    Server calculates the authoritative amount from plan definitions. The
    browser-provided amount is intentionally ignored.
    """
    try:
        from app.db.models import PaymentOrder as PO

        billing_cycle = str(billing_cycle).strip().lower()
        currency = str(currency).strip().upper()
        if billing_cycle not in {"monthly", "yearly"}:
            raise HTTPException(status_code=400, detail="Invalid billing cycle")
        if currency not in {"INR", "USD"}:
            raise HTTPException(status_code=400, detail="Unsupported currency")

        settings = get_settings()
        ensure_commercial_config(db)
        if currency == "USD" and not settings.RAZORPAY_USD_CHECKOUT_ENABLED:
            raise HTTPException(
                status_code=409,
                detail={"error": "USD_CHECKOUT_UNAVAILABLE", "message": "USD checkout is not available yet. Please choose INR or contact sales."},
            )

        logger.info(f"[create-order] user={current_user.id} plan_id={plan_id} billing_cycle={billing_cycle} currency={currency}")

        plan_key = PLAN_ID_TO_KEY.get(plan_id)
        if not plan_key or plan_key == "enterprise":
            raise HTTPException(status_code=400, detail="Invalid self-service plan")
        plan_def = plan_definitions(db).get(plan_key, {})
        price_field = "monthlyPrice" if currency == "INR" else "monthlyPriceUsd"
        if billing_cycle == "yearly":
            price_field = "yearlyPrice" if currency == "INR" else "yearlyPriceUsd"
        base_price = float(plan_def.get(price_field, 0))
        individual_discount_pct = float(plan_def.get("individual_discount_pct", 0))
        discounted_price = base_price - (base_price * (individual_discount_pct / 100))
        # GST handling is unchanged for INR. International tax is intentionally
        # not inferred until an approved tax policy and USD checkout are enabled.
        total_price = discounted_price + (discounted_price * float(GST_RATE)) if currency == "INR" else discounted_price
        amount_in_smallest_unit = int(round(total_price * 100))

        logger.info(f"[create-order] plan_key={plan_key} base_price={base_price} currency={currency} final_amount={amount_in_smallest_unit}")

        if amount_in_smallest_unit <= 0:
            raise HTTPException(status_code=400, detail="Calculated amount must be greater than 0")

        if amount_in_smallest_unit == 0:
            pay_id = f"pay_credit_{uuid.uuid4().hex[:8]}"
            order_id = f"order_credit_{uuid.uuid4().hex[:16]}"

            credit_order = PO(
                userId=current_user.id,
                razorpayOrderId=order_id,
                razorpayPaymentId=pay_id,
                planId=plan_id,
                amount=0,
                credit_applied_paise=0,
                currency="INR",
                billingCycle=billing_cycle,
                status="paid",
            )
            db.add(credit_order)
            db.flush()

            subscription = activate_subscription(
                db=db,
                user_id=current_user.id,
                plan_id=plan_id,
                payment_id=pay_id,
                order_id=order_id,
                billing_cycle=billing_cycle
            )
            db.commit()

            return {
                "order_id": order_id,
                "amount": 0,
                "prorated_discount": 0,
                "amount_after_proration": 0,
                "net_amount": 0,
                "currency": "INR",
                "key_id": "rzp_credit",
                "plan_id": plan_id,
                "user_id": current_user.id,
                "is_mock": True,
                "is_fully_credited": True,
                "credit_applied": 0
            }

        force_mock = getattr(settings, "RAZORPAY_FORCE_MOCK", False)
        
        order = create_order(amount=amount_in_smallest_unit, currency=currency, force_mock=force_mock)

        plan_name = plan_def.get("name", "Unknown")

        credit_order = PO(
            userId=current_user.id,
            razorpayOrderId=order["id"],
            planId=plan_id,
            amount=amount_in_smallest_unit,
            credit_applied_paise=0,
            currency=order["currency"],
            billingCycle=billing_cycle,
            status="created",
            purchaseType="SUBSCRIPTION_UPGRADE",
        )
        db.add(credit_order)
        db.flush()
        db.commit()

        logger.info(f"[create-order] Created payment order: order_id={order['id']} plan_id={plan_id} amount={amount_in_smallest_unit}")

        return {
            "order_id": order["id"],
            "amount": amount_in_smallest_unit,
            "prorated_discount": 0,
            "amount_after_proration": amount_in_smallest_unit,
            "net_amount": amount_in_smallest_unit / 100.0,
            "currency": order["currency"],
            "key_id": order["key"],
            "plan_id": plan_id,
            "user_id": current_user.id,
            "is_mock": order.get("mock", False),
            "is_fully_credited": False,
            "credit_applied": 0
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create payment order: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create payment order")

@router.post("/create-top-up-order")
async def create_top_up_order(
    package_id: Optional[str] = Query(None, description="Active commercial top-up package identifier"),
    multiplier: Optional[int] = Query(None, ge=1, description="Deprecated legacy selector; clients must submit package_id"),
    currency: str = Query("INR", description="INR or USD when provider support is enabled"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Razorpay payment order from an active, server-authoritative package.
    """
    try:
        from app.db.models import PaymentOrder as PO
        from app.core.config import get_settings

        settings = get_settings()
        ensure_commercial_config(db)
        currency = str(currency).strip().upper()
        if currency not in {"INR", "USD"}:
            raise HTTPException(status_code=400, detail="Unsupported currency")
        if currency == "USD" and not settings.RAZORPAY_USD_CHECKOUT_ENABLED:
            raise HTTPException(status_code=409, detail={"error": "USD_CHECKOUT_UNAVAILABLE", "message": "USD checkout is not available yet."})
        if not package_id and multiplier:
            # Transitional compatibility for the existing protected billing page;
            # it still resolves a real active package before calculating money.
            package = db.scalar(select(TopUpPackage).where(TopUpPackage.credits == multiplier * 600, TopUpPackage.isActive.is_(True)))
        else:
            package = db.scalar(select(TopUpPackage).where(TopUpPackage.id == package_id, TopUpPackage.isActive.is_(True)))
        if not package:
            raise HTTPException(status_code=404, detail="Active top-up package not found")
        total_credits = package.credits
        base_price = package.priceInr if currency == "INR" else package.priceUsd

        individual_discount_pct = float(getattr(current_user, "individual_discount_pct", 0.0) or 0.0)
        discounted_price = base_price - (base_price * (individual_discount_pct / 100.0))
        
        # Add GST (18%) to the final amount
        total_with_tax = discounted_price * 1.18 if currency == "INR" else discounted_price
        amount_in_paise = int(round(total_with_tax * 100))

        if amount_in_paise <= 0:
            raise HTTPException(status_code=400, detail="Calculated amount must be greater than 0")

        settings = get_settings()
        force_mock = getattr(settings, "RAZORPAY_FORCE_MOCK", False)
        order = create_order(amount=amount_in_paise, currency=currency, force_mock=force_mock)

        credit_order = PO(
            userId=current_user.id,
            razorpayOrderId=order["id"],
            planId=0,
            amount=amount_in_paise,
            credit_applied_paise=total_credits,  # Store credits in paise equivalent for tracking
            currency=order["currency"],
            status="created",
            purchaseType="CREDIT_TOP_UP",
            topUpPackageId=package.id,
        )
        db.add(credit_order)
        db.flush()

        create_pending_ledger_entry(
            db=db,
            user_id=current_user.id,
            owner_id=current_user.id,
            amount=float(total_credits),
            action_type="CREDIT_TOP_UP",
            description=f"Credit top-up: {total_credits} credits ({package.name})",
            related_order_id=order["id"],
            plan_name="Credit Top-Up",
        )

        db.commit()

        logger.info(f"[create-top-up-order] Created order: order_id={order['id']}, package_id={package.id}, amount_in_paise={amount_in_paise}")

        return {
            "order_id": order["id"],
            "amount": amount_in_paise,
            "currency": order["currency"],
            "key_id": order["key"],
            "package_id": package.id,
            "total_credits": total_credits,
            "base_price": base_price,
            "is_mock": order.get("mock", False),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create top-up order: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create top-up order")

@router.post("/verify-payment")
async def verify_payment(
    request_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    razorpay_order_id = request_data.get("razorpay_order_id")
    razorpay_payment_id = request_data.get("razorpay_payment_id")
    razorpay_signature = request_data.get("razorpay_signature")
    plan_id = request_data.get("plan_id")
    credit_applied = float(request_data.get("credit_applied", 0.0) or 0.0)
    billing_cycle = request_data.get("billing_cycle", "monthly")
    
    if razorpay_order_id is None or razorpay_payment_id is None or razorpay_signature is None:
        raise HTTPException(status_code=400, detail="Missing required payment fields")
    
    try:
        is_valid = verify_payment_signature(
            order_id=razorpay_order_id,
            payment_id=razorpay_payment_id,
            signature=razorpay_signature
        )
        
        logger.info(f"[verify-payment] signature_valid={is_valid} user={current_user.id} plan_id={plan_id} order_id={razorpay_order_id}")
        
        if not is_valid:
            from app.db.models import PaymentOrder as PO
            payment_order = db.scalar(select(PO).where(PO.razorpayOrderId == razorpay_order_id))
            plan_name = PLAN_DEFINITIONS.get(PLAN_ID_TO_KEY.get(plan_id, "starter"), {}).get("name", "Unknown") if plan_id is not None else "Unknown"
            if payment_order:
                payment_order.status = "failed"
                payment_order.razorpayPaymentId = razorpay_payment_id
                db.add(payment_order)
                db.commit()
            email_service.send_payment_failure_email(
                to_email=current_user.email,
                name=current_user.name,
                plan_name=plan_name,
                order_id=razorpay_order_id,
                error_message="Invalid payment signature"
            )
            raise HTTPException(status_code=400, detail="Invalid payment signature")
        
        from app.db.models import PaymentOrder as PO
        payment_order = db.scalar(select(PO).where(PO.razorpayOrderId == razorpay_order_id))
        if not payment_order:
            raise HTTPException(status_code=404, detail="Payment order not found")

        if payment_order.userId != current_user.id:
            raise HTTPException(status_code=403, detail="Not your payment order")

        if payment_order.planId != plan_id:
            raise HTTPException(status_code=400, detail="Payment plan does not match the order")
        billing_cycle = payment_order.billingCycle

        if getattr(payment_order, "purchaseType", None) == "CREDIT_TOP_UP":
            payment_order.status = "paid"
            payment_order.razorpayPaymentId = razorpay_payment_id
            db.add(payment_order)
            db.commit()

            # Credit top-ups are handled by /billing/verify-credit-payment endpoint
            # This webhook only marks the payment as paid
            logger.info(f"[verify-payment] CREDIT_TOP_UP payment marked as paid, credits will be added by verify-credit-payment endpoint")
            
            return ok("Credit top-up payment verified", {
                "credits_added": 0,  # Credits added by separate endpoint
                "message": "Credits will be added by verification endpoint"
            })

        if plan_id is None:
            logger.error(f"[verify-payment] Missing plan_id for subscription payment. razorpay_order_id={razorpay_order_id}")
            raise HTTPException(status_code=400, detail="Missing plan_id for subscription payment")

        logger.info(f"[verify-payment] Calling activate_subscription user={current_user.id} plan_id={plan_id} order_id={razorpay_order_id}")
        subscription = activate_subscription(
            db=db,
            user_id=current_user.id,
            plan_id=plan_id,
            payment_id=razorpay_payment_id,
            order_id=razorpay_order_id,
            billing_cycle=billing_cycle
        )
        
        logger.info(f"[verify-payment] activate_subscription done subscription_id={subscription.id} plan_id={subscription.planId}")
        
        return ok("Payment verified successfully", {
            "subscription": {
                "id": subscription.id,
                "status": subscription.status,
                "plan_id": subscription.planId
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        from app.db.models import PaymentOrder as PO
        payment_order = db.scalar(select(PO).where(PO.razorpayOrderId == razorpay_order_id))
        plan_name = PLAN_DEFINITIONS.get(PLAN_ID_TO_KEY.get(plan_id, "starter"), {}).get("name", "Unknown") if plan_id is not None else "Unknown"
        if payment_order:
            payment_order.status = "failed"
            payment_order.razorpayPaymentId = razorpay_payment_id
            db.add(payment_order)
            db.commit()
        email_service.send_payment_failure_email(
            to_email=current_user.email,
            name=current_user.name,
            plan_name=plan_name,
            order_id=razorpay_order_id,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")

@router.get("/current-plan")
async def get_current_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's subscription plan details.
    """
    subscription = db.query(Subscription).filter(
        Subscription.userId == current_user.id,
        Subscription.isActive == True
    ).first()
    
    snapshot = build_usage_snapshot(db, current_user)
    plan_key = get_plan_key(current_user)
    plan_name = get_settings().plan_config.plans.get(plan_key)
    payload = {
        "plan_name": plan_name.name if plan_name else plan_key,
        "plan_id": subscription.id if subscription else None,
        "status": subscription.status if subscription else "free",
        "current_period_start": subscription.startDate if subscription else None,
        "current_period_end": subscription.endDate if subscription else None,
        # Customer-facing limits always describe the active immutable cycle,
        # not the currently advertised commercial offering.
        "limits": snapshot["limits"],
    }
    return ok("Current plan" if subscription else "Free plan", payload)

@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel current subscription (downgrade to free at period end).
    """
    subscription = db.query(Subscription).filter(
        Subscription.userId == current_user.id,
        Subscription.isActive == True
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    subscription.isActive = False
    subscription.status = "cancelled"
    db.commit()
    
    return ok("Subscription cancelled successfully", None)

@router.post("/reactivate-subscription")
async def reactivate_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reactivate a cancelled subscription (before period ends).
    """
    active_subscription = db.query(Subscription).filter(
        Subscription.userId == current_user.id,
        Subscription.isActive == True
    ).first()
    
    if active_subscription:
        raise HTTPException(status_code=400, detail="You already have an active subscription")
    
    subscription = db.query(Subscription).filter(
        Subscription.userId == current_user.id,
        Subscription.isActive == False,
        Subscription.status == "cancelled"
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No cancelled subscription found")
    
    if subscription.endDate and subscription.endDate < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Subscription period has expired. Please purchase a new plan.")
    
    subscription.isActive = True
    subscription.status = "active"
    db.commit()
    
    return ok("Subscription reactivated successfully", None)


@router.get("/invoices")
async def get_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Return all payment invoices for the current user with GST breakdown.
    Failed transactions are included but without invoice numbers.
    Also returns the current account credit balance.
    """
    from app.db.models import PaymentOrder as PO, User

    user = db.scalar(select(User).where(User.id == current_user["id"]))

    orders = (
        db.query(PO)
        .filter(PO.userId == current_user["id"])
        .order_by(PO.createdAt.desc())
        .all()
    )

    invoices = [
        _build_invoice(
            o,
            user.name if user else current_user.get("name", "Customer"),
            user.email if user else current_user.get("email", ""),
            user.userGstin if user else None,
            user.userGstName if user else None,
            user.userGstAddress if user else None,
            user.userGstState if user else None,
            user.userGstStateCode if user else None,
        )
        for o in orders
    ]

    return {
        "success": True,
        "data": {
            "invoices": invoices,
            "credit_balance": float(getattr(current_user, "creditBalance", 0.0) or 0.0),
            "user_name": user.name if user else current_user.get("name", "Customer"),
            "user_email": user.email if user else current_user.get("email", ""),
            "user_gstin": user.userGstin if user else None,
            "user_gst_name": user.userGstName if user else None,
            "user_gst_address": user.userGstAddress if user else None,
            "user_gst_state": user.userGstState if user else None,
            "user_gst_state_code": user.userGstStateCode if user else None,
        }
    }


@router.post("/mark-failed")
async def mark_payment_failed(
    request_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.db.models import PaymentOrder as PO

    order_id = request_data.get("razorpay_order_id")
    if not order_id:
        raise HTTPException(status_code=400, detail="Missing order ID")

    payment_order = db.scalar(select(PO).where(PO.razorpayOrderId == order_id))
    if not payment_order:
        payment_order = db.scalar(select(PO).where(PO.razorpayOrderId == order_id, PO.userId == current_user.id))
    
    if not payment_order:
        raise HTTPException(status_code=404, detail="Payment order not found")
    
    if payment_order.userId != current_user.id:
        raise HTTPException(status_code=403, detail="Not your payment order")

    if payment_order.status == "paid":
        return ok("Order already paid", None)

    payment_order.status = "failed"
    db.add(payment_order)
    db.commit()

    return ok("Payment marked as failed", None)
