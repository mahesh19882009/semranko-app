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

PLAN_ID_TO_KEY = {0: "starter", 1: "pro", 2: "agency"}
GST_RATE = Decimal(str(GST_RATE))
PLAN_KEY_PRICES = {
    "starter": {"monthly": 639, "yearly": 6932},
    "pro":     {"monthly": 1589, "yearly": 17235},
    "agency":  {"monthly": 3969, "yearly": 43058},
}

def _build_invoice(order: "PaymentOrder", user_name: str, user_email: str) -> dict:
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
    }


@router.post("/create-order")
async def create_payment_order(
    plan_id: int = Query(..., description="Plan ID to upgrade to"),
    amount: int = Query(..., description="Amount in smallest currency unit (e.g., paise)"),
    billing_cycle: str = Query("monthly", description="Billing cycle: monthly or yearly"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Razorpay payment order for subscription upgrade.
    Expects query parameters: ?plan_id=2&amount=999900
    """
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    try:
        from app.db.models import PaymentOrder as PO
        from datetime import datetime, timedelta

        # Calculate prorated amount for upgrades
        existing_subscription = db.query(Subscription).filter(
            Subscription.userId == current_user.id,
            Subscription.isActive == True
        ).first()
        
        prorated_discount_paise = 0
        if existing_subscription and existing_subscription.endDate:
            # Calculate remaining days in current subscription
            remaining_days = (existing_subscription.endDate - datetime.utcnow()).days
            if remaining_days > 0:
                # Get current plan price
                current_plan_id = existing_subscription.planId
                current_plan_key = PLAN_ID_TO_KEY.get(current_plan_id, "starter")
                current_plan_price = PLAN_KEY_PRICES.get(current_plan_key, {}).get("monthly", 639)
                
                # Calculate daily rate and remaining value
                daily_rate = current_plan_price / 30  # Assuming 30-day month
                remaining_value = daily_rate * remaining_days
                
                # Convert to paise and apply as discount
                prorated_discount_paise = int(round(remaining_value * 100))
        
        # Apply prorated discount to amount
        amount_after_proration = max(0, amount - prorated_discount_paise)
        
        # Check credit balance
        available_credit = float(getattr(current_user, "creditBalance", 0.0) or 0.0)
        available_credit_paise = int(round(available_credit * 100))
        applied_credit_paise = min(amount_after_proration, available_credit_paise)
        net_amount_paise = amount_after_proration - applied_credit_paise

        # 100% Credit Coverage Case — paid entirely by account credit
        if net_amount_paise == 0:
            pay_id = f"pay_credit_{uuid.uuid4().hex[:8]}"
            order_id = f"order_credit_{uuid.uuid4().hex[:16]}"

            credit_order = PO(
                userId=current_user.id,
                razorpayOrderId=order_id,
                razorpayPaymentId=pay_id,
                planId=plan_id,
                amount=0,
                credit_applied_paise=amount,
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
            credit_deducted = round(applied_credit_paise / 100.0, 2)
            current_user.creditBalance = round(max(0.0, available_credit - credit_deducted), 2)
            db.add(current_user)
            db.commit()

            return {
                "order_id": order_id,
                "amount": amount,
                "prorated_discount": round(prorated_discount_paise / 100.0, 2),
                "amount_after_proration": round(amount_after_proration / 100.0, 2),
                "net_amount": 0,
                "currency": "INR",
                "key_id": "rzp_credit",
                "plan_id": plan_id,
                "user_id": current_user.id,
                "is_mock": True,
                "is_fully_credited": True,
                "credit_applied": credit_deducted,
                "remaining_credit": current_user.creditBalance
            }

        settings = get_settings()
        force_mock = getattr(settings, "RAZORPAY_FORCE_MOCK", False)
        
        order = create_order(amount=net_amount_paise, currency="INR", force_mock=force_mock)

        plan_key = PLAN_ID_TO_KEY.get(plan_id, "starter")
        plan_name = PLAN_DEFINITIONS.get(plan_key, {}).get("name", "Unknown")

        credit_order = PO(
            userId=current_user.id,
            razorpayOrderId=order["id"],
            planId=plan_id,
            amount=net_amount_paise,
            credit_applied_paise=applied_credit_paise,
            currency=order["currency"],
            status="created",
        )
        db.add(credit_order)
        db.flush()

        create_pending_ledger_entry(
            db=db,
            user_id=current_user.id,
            owner_id=current_user.id,
            amount=float(net_amount_paise) / 100.0,
            action_type="purchase",
            description=f"Subscription purchase: {plan_name} (Order {order['id']})",
            related_order_id=order["id"],
            plan_name=plan_name,
        )

        db.commit()

        return {
            "order_id": order["id"],
            "amount": amount,
            "prorated_discount": round(prorated_discount_paise / 100.0, 2),
            "amount_after_proration": round(amount_after_proration / 100.0, 2),
            "net_amount": net_amount_paise,
            "currency": order["currency"],
            "key_id": order["key"],
            "plan_id": plan_id,
            "user_id": current_user.id,
            "is_mock": order.get("mock", False),
            "is_fully_credited": False,
            "credit_applied": round(applied_credit_paise / 100.0, 2)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Failed to create payment order: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create payment order: {str(e)}")

@router.post("/verify-payment")
async def verify_payment(
    request_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify Razorpay payment signature and activate subscription.
    Expected body: { razorpay_order_id, razorpay_payment_id, razorpay_signature, plan_id, credit_applied, billing_cycle }
    """
    razorpay_order_id = request_data.get("razorpay_order_id")
    razorpay_payment_id = request_data.get("razorpay_payment_id")
    razorpay_signature = request_data.get("razorpay_signature")
    plan_id = request_data.get("plan_id")
    credit_applied = float(request_data.get("credit_applied", 0.0) or 0.0)
    billing_cycle = request_data.get("billing_cycle", "monthly")
    
    if razorpay_order_id is None or razorpay_payment_id is None or razorpay_signature is None or plan_id is None:
        raise HTTPException(status_code=400, detail="Missing required payment fields")
    
    try:
        is_valid = verify_payment_signature(
            order_id=razorpay_order_id,
            payment_id=razorpay_payment_id,
            signature=razorpay_signature
        )
        
        if not is_valid:
            # Mark payment order as failed
            from app.db.models import PaymentOrder as PO
            payment_order = db.scalar(select(PO).where(PO.razorpayOrderId == razorpay_order_id))
            plan_name = PLAN_DEFINITIONS.get(PLAN_ID_TO_KEY.get(plan_id, "starter"), {}).get("name", "Unknown")
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
        
        subscription = activate_subscription(
            db=db,
            user_id=current_user.id,
            plan_id=plan_id,
            payment_id=razorpay_payment_id,
            order_id=razorpay_order_id,
            billing_cycle=billing_cycle
        )

        if credit_applied > 0:
            current_user.creditBalance = round(max(0.0, (getattr(current_user, "creditBalance", 0.0) or 0.0) - credit_applied), 2)
            db.add(current_user)
            db.commit()
        
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
        # Mark payment order as failed on any other error
        from app.db.models import PaymentOrder as PO
        payment_order = db.scalar(select(PO).where(PO.razorpayOrderId == razorpay_order_id))
        plan_name = PLAN_DEFINITIONS.get(PLAN_ID_TO_KEY.get(plan_id, "starter"), {}).get("name", "Unknown")
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
    subscription = db.query(Subscription).filter(
        Subscription.userId == current_user.id,
        Subscription.isActive == False,
        Subscription.status == "cancelled"
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No cancelled subscription found")
    
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
    from app.db.models import PaymentOrder as PO

    orders = (
        db.query(PO)
        .filter(PO.userId == current_user.id)
        .order_by(PO.createdAt.desc())
        .all()
    )

    invoices = [
        _build_invoice(o, current_user.name, current_user.email)
        for o in orders
    ]

    return {
        "success": True,
        "data": {
            "invoices": invoices,
            "credit_balance": float(getattr(current_user, "creditBalance", 0.0) or 0.0),
            "user_name": current_user.name,
            "user_email": current_user.email,
        }
    }


@router.post("/webhook")
async def razorpay_webhook(
    request_data: Dict[str, Any],
    signature: str = Header(None),
    db: Session = Depends(get_db)
):
    from app.services.payment_service import handle_webhook
    from app.db.models import User, PaymentOrder as PO, CreditLedger

    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")

    try:
        event = handle_webhook(request_data, signature)
    except Exception as exc:
        logger.exception("Webhook verification failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if not event:
        return {"received": True}

    event_type = event.get("type")
    payment_id = event.get("payment_id")
    order_id = event.get("order_id")
    user_email = event.get("user_email")
    plan_id = event.get("plan_id")

    payment_order = db.scalar(select(PO).where(PO.razorpayOrderId == order_id))
    if not payment_order:
        return {"received": True}

    user = db.scalar(select(User).where(User.id == payment_order.userId))
    if not user:
        return {"received": True}

    plan_name = PLAN_DEFINITIONS.get(PLAN_ID_TO_KEY.get(plan_id, "starter"), {}).get("name", "Unknown") if plan_id is not None else "Unknown"

    if event_type == "payment.captured":
        payment_order.status = "paid"
        payment_order.razorpayPaymentId = payment_id
        db.add(payment_order)
        db.commit()

        finalize_pending_ledger_entry(
            db=db,
            order_id=order_id,
            amount_paid_inr=float(payment_order.amount) / 100.0,
            plan_name=plan_name,
        )

        try:
            subscription = activate_subscription(
                db=db,
                user_id=user.id,
                plan_id=plan_id if plan_id is not None else payment_order.planId,
                payment_id=payment_id,
                order_id=order_id,
                billing_cycle="monthly"
            )
            user = db.scalar(select(User).where(User.id == user.id))
            if user:
                user.selectedPlan = PLAN_ID_TO_KEY.get(plan_id if plan_id is not None else payment_order.planId, "starter")
                db.add(user)
                db.commit()
                db.refresh(user)
        except Exception as exc:
            logger.exception("Webhook subscription activation failed: %s", exc)

        email_service.send_payment_success_email(
            to_email=user.email,
            name=user.name,
            plan_name=plan_name,
            amount=float(payment_order.amount) / 100,
            order_id=order_id
        )

    elif event_type == "payment.failed":
        payment_order.status = "failed"
        payment_order.razorpayPaymentId = payment_id
        db.add(payment_order)
        db.commit()

        ledger = db.scalar(
            select(CreditLedger).where(
                CreditLedger.relatedOrderId == order_id,
                CreditLedger.status == "pending",
            )
        )
        if ledger:
            ledger.status = "failed"
            db.add(ledger)
            db.commit()
            db.refresh(ledger)

        email_service.send_payment_failure_email(
            to_email=user.email,
            name=user.name,
            plan_name=plan_name,
            order_id=order_id,
            error_message="Payment failed via Razorpay webhook"
        )

    return {"received": True}


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

    payment_order = db.scalar(select(PO).where(PO.razorpayOrderId == order_id, PO.userId == current_user.id))
    if not payment_order:
        raise HTTPException(status_code=404, detail="Payment order not found")

    if payment_order.status == "paid":
        return ok("Order already paid", None)

    payment_order.status = "failed"
    db.add(payment_order)
    db.commit()

    return ok("Payment marked as failed", None)
