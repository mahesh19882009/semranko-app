import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Dict, Any

logger = logging.getLogger(__name__)

from app.core.security import get_current_user
from app.db.session import get_db
from app.db.models import User, Subscription
from app.services.payment_service import create_order, verify_payment_signature, activate_subscription
from app.services import email_service
from app.services.plan_service import PLAN_DEFINITIONS
from app.services.credit_service import create_pending_ledger_entry, finalize_pending_ledger_entry, add_purchased_credits
from app.core.config import FREE_PLAN_LIMITS, GST_RATE, get_settings

from decimal import Decimal, ROUND_HALF_UP

from app.schemas.common import ok

router = APIRouter(prefix="/payments", tags=["payments"])

PLAN_ID_TO_KEY = {0: "starter", 1: "pro", 2: "agency", 3: "enterprise"}
PLAN_KEY_TO_ID = {v: k for k, v in PLAN_ID_TO_KEY.items()}
GST_RATE = Decimal(str(GST_RATE))
PLAN_KEY_PRICES = {
    "starter": {"monthly": 999, "yearly": 10789},
    "pro":     {"monthly": 3999, "yearly": 43189},
    "agency":  {"monthly": 9999, "yearly": 107989},
}

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Razorpay payment order for subscription upgrade.
    Server calculates discounted INR amount from plan definitions.
    """
    try:
        from app.db.models import PaymentOrder as PO

        logger.info(f"[create-order] user={current_user.id} plan_id={plan_id} billing_cycle={billing_cycle}")
        
        plan_key = PLAN_ID_TO_KEY.get(plan_id, "starter")
        plan_def = PLAN_DEFINITIONS.get(plan_key, {})
        base_price_inr = float(plan_def.get("monthlyPrice", 0))
        individual_discount_pct = float(plan_def.get("individual_discount_pct", 0))

        if billing_cycle == "yearly":
            base_price_inr = float(plan_def.get("yearlyPrice", base_price_inr))

        discounted_inr = base_price_inr - (base_price_inr * (individual_discount_pct / 100))
        amount_in_inr = discounted_inr + (discounted_inr * float(GST_RATE))
        amount_in_paise = int(round(amount_in_inr * 100))

        logger.info(f"[create-order] plan_key={plan_key} base_price={base_price_inr} discount={individual_discount_pct}% final_amount={amount_in_paise}")

        if amount_in_paise <= 0:
            raise HTTPException(status_code=400, detail="Calculated amount must be greater than 0")

        if amount_in_paise == 0:
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

        settings = get_settings()
        force_mock = getattr(settings, "RAZORPAY_FORCE_MOCK", False)
        
        order = create_order(amount=amount_in_paise, currency="INR", force_mock=force_mock)

        plan_name = plan_def.get("name", "Unknown")

        credit_order = PO(
            userId=current_user.id,
            razorpayOrderId=order["id"],
            planId=plan_id,
            amount=amount_in_paise,
            credit_applied_paise=0,
            currency=order["currency"],
            status="created",
            purchaseType="SUBSCRIPTION_UPGRADE",
        )
        db.add(credit_order)
        db.flush()
        db.commit()

        logger.info(f"[create-order] Created payment order: order_id={order['id']} plan_id={plan_id} amount={amount_in_paise}")

        return {
            "order_id": order["id"],
            "amount": amount_in_paise,
            "prorated_discount": 0,
            "amount_after_proration": amount_in_paise,
            "net_amount": amount_in_paise / 100.0,
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
    multiplier: int = Query(..., ge=1, description="Multiplier of 600 credits to purchase (1=600, 2=1200, etc.)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Razorpay payment order for credit top-up.
    1 multiplier = 600 credits at flat ₹100 per 600 credits.
    No bulk discount.
    """
    try:
        from app.db.models import PaymentOrder as PO
        from app.core.config import get_settings

        settings = get_settings()
        credits_per_unit = settings.CREDIT_TOP_UP_CONFIG.get("credits_per_100_inr", 600)
        base_price_inr = settings.CREDIT_TOP_UP_CONFIG.get("base_price_inr", 100)

        total_credits = multiplier * credits_per_unit
        total_inr = multiplier * base_price_inr  # Base price excluding GST

        individual_discount_pct = float(getattr(current_user, "individual_discount_pct", 0.0) or 0.0)
        discounted_inr = total_inr - (total_inr * (individual_discount_pct / 100.0))
        
        # Add GST (18%) to the final amount
        gst_inr = discounted_inr * 0.18
        total_with_gst = discounted_inr + gst_inr
        amount_in_paise = int(round(total_with_gst * 100))

        if amount_in_paise <= 0:
            raise HTTPException(status_code=400, detail="Calculated amount must be greater than 0")

        settings = get_settings()
        force_mock = getattr(settings, "RAZORPAY_FORCE_MOCK", False)
        order = create_order(amount=amount_in_paise, currency="INR", force_mock=force_mock)

        credit_order = PO(
            userId=current_user.id,
            razorpayOrderId=order["id"],
            planId=multiplier,
            amount=amount_in_paise,
            credit_applied_paise=total_credits,  # Store credits in paise equivalent for tracking
            currency=order["currency"],
            status="created",
            purchaseType="CREDIT_TOP_UP",
        )
        db.add(credit_order)
        db.flush()

        create_pending_ledger_entry(
            db=db,
            user_id=current_user.id,
            owner_id=current_user.id,
            amount=float(total_credits),
            action_type="CREDIT_TOP_UP",
            description=f"Credit top-up: {total_credits} credits ({multiplier}x{credits_per_unit})",
            related_order_id=order["id"],
            plan_name="Credit Top-Up",
        )

        db.commit()

        logger.info(f"[create-top-up-order] Created order: order_id={order['id']}, multiplier={multiplier}, total_credits={total_credits}, amount_in_paise={amount_in_paise}")

        return {
            "order_id": order["id"],
            "amount": amount_in_paise,
            "currency": order["currency"],
            "key_id": order["key"],
            "multiplier": multiplier,
            "credits_per_unit": credits_per_unit,
            "total_credits": total_credits,
            "price_per_unit_inr": base_price_inr,
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
    
    if not subscription:
        return ok("Free plan", {
            "plan_name": "Free",
            "plan_id": None,
            "status": "free",
            "limits": FREE_PLAN_LIMITS
        })
    
    # Return basic plan info.
    return ok("Current plan", {
        "plan_name": "Pro", 
        "plan_id": subscription.id, 
        "status": subscription.status,
        "current_period_start": subscription.startDate,
        "current_period_end": subscription.endDate,
        "limits": {
            "projects": 10, 
            "keywords": 500,
            "competitors": 10,
            "reports": 20
        }
    })

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
