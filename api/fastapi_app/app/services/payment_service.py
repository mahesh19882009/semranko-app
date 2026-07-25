import razorpay
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.models import User, PaymentOrder, Subscription
from app.core.config import get_settings
from datetime import datetime, timedelta
from sqlalchemy import select

settings = get_settings()

# Initialize Razorpay client - will be None if keys not configured (zero-cost dev mode)
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
) if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET else None


def get_plan_by_id(db: Session, plan_id: int) -> Optional[Dict[str, Any]]:
    """
    Get plan details by ID from PLAN_DEFINITIONS
    
    Args:
        db: Database session (not used but kept for consistency)
        plan_id: ID of the plan (0=starter, 1=pro, 2=agency)
    
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
    
    # Return plan with additional metadata
    return {
        "id": plan_id,
        "key": plan["key"],
        "name": plan["name"],
        "monthly_price": plan["monthlyPrice"],
        "yearly_price": plan["yearlyPrice"],
        "description": plan["description"],
        "limits": plan["limits"],
        "duration_days": 30  # Default subscription duration
    }


def create_order(
    db: Session, 
    user: User, 
    plan_id: int, 
    amount: int, 
    currency: str = "INR"
) -> Dict[str, Any]:
    """
    Create a Razorpay order for subscription payment
    
    Args:
        db: Database session
        user: Current user
        plan_id: ID of the plan being purchased
        amount: Amount in paise (e.g., 50000 for ₹500)
        currency: Currency code (default: INR)
    
    Returns:
        Order details including order_id, amount, and status
    """
    # Zero-cost dev mode: if Razorpay not configured, create mock order
    if not razorpay_client:
        # Create mock order for development
        mock_order_id = f"mock_order_{user.id}_{int(datetime.now().timestamp())}"
        
        # Store mock order in database
        order = PaymentOrder(
            userId=user.id,
            razorpayOrderId=mock_order_id,
            planId=plan_id,
            amount=amount,
            currency=currency,
            status="created"
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        return {
            "order_id": mock_order_id,
            "amount": amount,
            "currency": currency,
            "status": "created",
            "plan_id": plan_id,
            "user_id": user.id,
            "key_id": "mock_key_id"  # Mock key for frontend
        }
    
    # Production mode: Create real Razorpay order
    order_data = {
        'amount': amount,  # Amount in paise
        'currency': currency,
        'receipt': f"order_rcptid_{user.id}_{datetime.now().timestamp()}",
        'notes': {
            'user_id': str(user.id),
            'plan_id': str(plan_id),
            'email': user.email
        }
    }
    
    try:
        order = razorpay_client.order.create(data=order_data)
        
        # Store order in database
        db_order = PaymentOrder(
            userId=user.id,
            razorpayOrderId=order['id'],
            planId=plan_id,
            amount=order['amount'],
            currency=order['currency'],
            status=order['status']
        )
        db.add(db_order)
        db.commit()
        
        return {
            "order_id": order['id'],
            "amount": order['amount'],
            "currency": order['currency'],
            "status": order['status'],
            "plan_id": plan_id,
            "user_id": user.id,
            "key_id": settings.RAZORPAY_KEY_ID
        }
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to create Razorpay order: {str(e)}")


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
    # Zero-cost dev mode: accept mock payments
    if not razorpay_client:
        # For mock orders, just verify the order_id starts with "mock_order_"
        return order_id.startswith("mock_order_")
    
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
    user: User,
    plan_id: int,
    payment_id: str,
    order_id: str
) -> Subscription:
    """
    Activate subscription after successful payment
    
    Args:
        db: Database session
        user: User object
        plan_id: ID of the purchased plan
        payment_id: Razorpay payment ID
        order_id: Razorpay order ID
    
    Returns:
        Activated subscription object
    """
    plan = get_plan_by_id(db, plan_id)
    if not plan:
        raise Exception("Plan not found")
    
    # Update the payment order status
    order = db.scalar(select(PaymentOrder).where(PaymentOrder.razorpayOrderId == order_id))
    if order:
        order.status = "paid"
        order.razorpayPaymentId = payment_id
        db.add(order)
    
    # Check if user has existing subscription
    existing_subscription = db.scalar(
        select(Subscription).where(
            Subscription.userId == user.id,
            Subscription.isActive == True
        )
    )
    
    if existing_subscription:
        # Extend existing subscription
        if existing_subscription.endDate and existing_subscription.endDate > datetime.utcnow():
            new_end_date = existing_subscription.endDate + timedelta(days=plan["duration_days"])
        else:
            new_end_date = datetime.utcnow() + timedelta(days=plan["duration_days"])
        
        existing_subscription.planId = plan_id
        existing_subscription.endDate = new_end_date
        existing_subscription.status = 'active'
        existing_subscription.isActive = True
        existing_subscription.razorpayPaymentId = payment_id
        existing_subscription.razorpayOrderId = order_id
        db.add(existing_subscription)
        db.commit()
        db.refresh(existing_subscription)
        return existing_subscription
    else:
        # Create new subscription
        subscription = Subscription(
            userId=user.id,
            planId=plan_id,
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
        user.selectedPlan = plan["key"]
        db.add(user)
        db.commit()
        
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
