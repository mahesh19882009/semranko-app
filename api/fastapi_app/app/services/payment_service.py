import razorpay
import uuid
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.models import User, PaymentOrder, Subscription
from app.core.config import get_settings
from app.services.plan_service import PLAN_DEFINITIONS, PLAN_ORDER
from app.services.notification_service import create_notification
from app.services import email_service
from datetime import datetime, timedelta
from sqlalchemy import select
from fastapi import HTTPException

logger = logging.getLogger(__name__)

settings = get_settings()

# Initialize Razorpay client - will be None if keys not configured (zero-cost dev mode)
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
) if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET else None


def get_plan_by_id(db: Session, plan_id: int, billing_cycle: str = "monthly") -> Optional[Dict[str, Any]]:
    """
    Get plan details by ID from PLAN_DEFINITIONS
    
    Args:
        db: Database session (not used but kept for consistency)
        plan_id: ID of the plan (0=starter, 1=pro, 2=agency)
        billing_cycle: 'monthly' or 'yearly'
    
    Returns:
        Plan details or None if invalid plan_id
    """
    from app.services.plan_service import PLAN_DEFINITIONS
    
    plan_keys = ["starter", "pro", "agency"]
    if plan_id < 0 or plan_id >= len(plan_keys):
        return None
    
    plan_key = plan_keys[plan_id]
    plan = PLAN_DEFINITIONS.get(plan_key)
    
    if not plan:
        return None
    
    # Calculate duration and price based on billing cycle
    if billing_cycle == "yearly":
        duration_days = 365
        price = plan["yearlyPrice"]
    else:
        duration_days = 30
        price = plan["monthlyPrice"]
    
    # Return plan with additional metadata
    return {
        "id": plan_id,
        "key": plan["key"],
        "name": plan["name"],
        "monthly_price": plan["monthlyPrice"],
        "yearly_price": plan["yearlyPrice"],
        "price": price,
        "billing_cycle": billing_cycle,
        "description": plan["description"],
        "limits": plan["limits"],
        "duration_days": duration_days
    }


def create_order(amount: int, currency: str = "INR", force_mock: bool = False) -> dict:
    # Check if credentials are actually present and not just empty strings
    has_credentials = (
        settings.RAZORPAY_KEY_ID and 
        settings.RAZORPAY_KEY_SECRET and 
        settings.RAZORPAY_KEY_ID != "your_razorpay_key_id" and 
        settings.RAZORPAY_KEY_SECRET != "your_razorpay_secret"
    )

    # If force_mock is True or credentials are missing, use mock mode
    if force_mock or not has_credentials:
        logger.warning("Using MOCK payment mode.")
        return {
            "id": f"order_mock_{uuid.uuid4()}", 
            "amount": amount, 
            "currency": currency,
            "key": settings.RAZORPAY_KEY_ID if settings.RAZORPAY_KEY_ID else "rzp_test_mock_key",
            "mock": True
        }

    # Real Razorpay order creation
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        order_data = {
            "amount": amount,
            "currency": currency,
            "receipt": f"rcpt_{uuid.uuid4().hex[:24]}"
        }
        order_data["notes"] = {"environment": "test" if "test" in settings.RAZORPAY_KEY_ID else "live"}
        
        order = client.order.create(data=order_data)
        logger.info(f"Razorpay order created: {order['id']}")
        return {
            "id": order["id"], 
            "amount": order["amount"], 
            "currency": order["currency"],
            "key": settings.RAZORPAY_KEY_ID
        }
    except razorpay.errors.BadRequestError as e:
        logger.error(f"Razorpay BadRequest: {str(e)} - Check your Key/Secret or Amount format.")
        raise HTTPException(status_code=400, detail=f"Invalid Razorpay config: {str(e)}")
    except Exception as e:
        logger.error(f"Razorpay unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Payment service unavailable")


def verify_payment_signature(
    order_id: str,
    payment_id: str,
    signature: str
) -> bool:
    """
    Verify Razorpay payment signature
    
    Args:
        order_id: Razorpay order ID
        payment_id: Razorpay payment ID
        signature: Razorpay payment signature
    
    Returns:
        True if signature is valid, False otherwise
    """
    # Zero-cost dev mode: accept mock payments only when no real client exists
    if not razorpay_client:
        return order_id.startswith("order_mock_")
    
    # Real Razorpay keys configured: reject mock orders
    if order_id.startswith("order_mock_"):
        return False
    
    try:
        params = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        
        # This will raise SignatureVerificationError if signature is invalid
        razorpay_client.utility.verify_payment_signature(params)
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
    except Exception as e:
        raise Exception(f"Payment verification failed: {str(e)}")


def handle_webhook(payload: Dict[str, Any], signature: str) -> Optional[Dict[str, Any]]:
    """
    Handle Razorpay webhook events
    
    Args:
        payload: Webhook payload
        signature: Webhook signature
    
    Returns:
        Event data if valid, None otherwise
    """
    if not razorpay_client:
        raise Exception("Razorpay client not initialized.")
    
    try:
        # Verify webhook signature
        razorpay_client.utility.verify_webhook_signature(
            str(payload),
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET
        )
        
        event = payload.get('event', {})
        payment = payload.get('payload', {}).get('payment', {}).get('entity', {})
        
        # Handle payment captured event
        if event == 'payment.captured' and payment.get('status') == 'captured':
            return {
                'type': 'payment.captured',
                'payment_id': payment.get('id'),
                'order_id': payment.get('order_id'),
                'amount': payment.get('amount'),
                'currency': payment.get('currency'),
                'user_email': payment.get('notes', {}).get('email'),
                'plan_id': payment.get('notes', {}).get('plan_id')
            }
        
        return None
    except Exception as e:
        raise Exception(f"Webhook verification failed: {str(e)}")


def activate_subscription(
    db: Session,
    user_id: str,
    plan_id: int,
    payment_id: str,
    order_id: str,
    billing_cycle: str = "monthly"
) -> Subscription:
    """
    Activate subscription after successful payment
    
    Args:
        db: Database session
        user_id: User ID
        plan_id: ID of the purchased plan
        payment_id: Razorpay payment ID (or mock payment ID for dev mode)
        order_id: Razorpay order ID (or mock order ID for dev mode)
        billing_cycle: 'monthly' or 'yearly'
    
    Returns:
        Activated subscription object
    """
    plan = get_plan_by_id(db, plan_id, billing_cycle)
    if not plan:
        raise Exception("Plan not found")
    
    # Get user object
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise Exception("User not found")
    
    # Upsert PaymentOrder: mark existing as paid, or create it if somehow missing
    order = db.scalar(select(PaymentOrder).where(PaymentOrder.razorpayOrderId == order_id))
    if order:
        order.status = "paid"
        order.razorpayPaymentId = payment_id
        db.add(order)
    else:
        # Fallback: create the PaymentOrder record if it wasn't saved during create-order
        fallback_order = PaymentOrder(
            userId=user_id,
            razorpayOrderId=order_id,
            razorpayPaymentId=payment_id,
            planId=plan_id,
            amount=0,
            credit_applied_paise=0,
            currency="INR",
            status="paid",
        )
        db.add(fallback_order)
    
    # Check if user has existing subscription
    existing_subscription = db.scalar(
        select(Subscription).where(
            Subscription.userId == user_id,
            Subscription.isActive == True
        )
    )
    
    effective_plan_id = plan_id
    effective_plan_key = plan["key"]
    
    if existing_subscription:
        existing_subscription.planId = effective_plan_id
        existing_subscription.status = 'active'
        existing_subscription.isActive = True
        existing_subscription.razorpayPaymentId = payment_id
        existing_subscription.razorpayOrderId = order_id
        
        if existing_subscription.endDate and existing_subscription.endDate > datetime.utcnow():
            new_end_date = existing_subscription.endDate
        else:
            new_end_date = datetime.utcnow() + timedelta(days=plan["duration_days"])
        
        existing_subscription.endDate = new_end_date
        db.add(existing_subscription)
        
        user.subscriptionStatus = "active"
        user.selectedPlan = effective_plan_key
        db.add(user)
        
        db.commit()
        db.refresh(existing_subscription)
        
        create_notification(
            db,
            user_id=user_id,
            title="Subscription renewed",
            message=f"Your {plan['name']} subscription has been renewed.",
            type="plan_change",
            severity="info",
        )
        db.commit()

        payment_order = db.scalar(select(PaymentOrder).where(PaymentOrder.razorpayOrderId == order_id))
        amount = float(payment_order.amount) / 100 if payment_order else 0.0
        email_service.send_payment_success_email(
            to_email=user.email,
            name=user.name,
            plan_name=plan['name'],
            amount=amount,
            order_id=order_id
        )
        
        return existing_subscription
    else:
        # Create new subscription
        subscription = Subscription(
            userId=user_id,
            planId=effective_plan_id,
            status='active',
            isActive=True,
            startDate=datetime.utcnow(),
            endDate=datetime.utcnow() + timedelta(days=plan["duration_days"]),
            razorpayPaymentId=payment_id,
            razorpayOrderId=order_id
        )
        
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        # Also update user's subscription status and selected plan
        user.subscriptionStatus = "active"
        user.selectedPlan = effective_plan_key
        db.add(user)
        db.commit()
        
        create_notification(
            db,
            user_id=user_id,
            title="Welcome to RankCare",
            message=f"Your {plan['name']} subscription is now active.",
            type="plan_change",
            severity="info",
        )
        db.commit()

        payment_order = db.scalar(select(PaymentOrder).where(PaymentOrder.razorpayOrderId == order_id))
        amount = float(payment_order.amount) / 100 if payment_order else 0.0
        email_service.send_payment_success_email(
            to_email=user.email,
            name=user.name,
            plan_name=plan['name'],
            amount=amount,
            order_id=order_id
        )
        
        return subscription


def get_subscription_status(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get current subscription status for a user
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        Subscription details or None
    """
    subscription = db.scalar(
        select(Subscription).where(
            Subscription.userId == user_id,
            Subscription.isActive == True
        )
    )
    
    if not subscription:
        return None
    
    plan = get_plan_by_id(db, subscription.planId)
    
    return {
        'plan_id': subscription.planId,
        'plan_key': plan['key'] if plan else 'unknown',
        'plan_name': plan['name'] if plan else 'Unknown',
        'status': subscription.status,
        'start_date': subscription.startDate,
        'end_date': subscription.endDate,
        'days_remaining': (subscription.endDate - datetime.utcnow()).days if subscription.endDate else 0,
        'is_trial': False
    }