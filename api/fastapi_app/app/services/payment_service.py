import razorpay
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.user import User
from app.db.models.subscription import Subscription
from app.core.config import get_settings
from datetime import datetime, timedelta

settings = get_settings()

# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
) if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET else None


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
    if not razorpay_client:
        raise Exception("Razorpay client not initialized. Please check your API keys.")
    
    # Create Razorpay order
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
        
        # Store order in database (optional - you can create an Order model)
        # For now, we'll just return the order details
        
        return {
            "order_id": order['id'],
            "amount": order['amount'],
            "currency": order['currency'],
            "status": order['status'],
            "plan_id": plan_id,
            "user_id": user.id
        }
    except Exception as e:
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
    if not razorpay_client:
        raise Exception("Razorpay client not initialized.")
    
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
    from app.services.plan_service import get_plan_by_id
    
    plan = get_plan_by_id(db, plan_id)
    if not plan:
        raise Exception("Plan not found")
    
    # Check if user has existing subscription
    existing_subscription = db.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.is_active == True
    ).first()
    
    if existing_subscription:
        # Extend existing subscription
        if existing_subscription.end_date and existing_subscription.end_date > datetime.utcnow():
            new_end_date = existing_subscription.end_date + timedelta(days=plan.duration_days)
        else:
            new_end_date = datetime.utcnow() + timedelta(days=plan.duration_days)
        
        existing_subscription.plan_id = plan_id
        existing_subscription.end_date = new_end_date
        existing_subscription.status = 'active'
        db.commit()
        db.refresh(existing_subscription)
        return existing_subscription
    else:
        # Create new subscription
        subscription = Subscription(
            user_id=user.id,
            plan_id=plan_id,
            status='active',
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=plan.duration_days),
            razorpay_payment_id=payment_id,
            razorpay_order_id=order_id
        )
        
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription


def get_subscription_status(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get current subscription status for a user
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        Subscription details or None
    """
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.is_active == True
    ).first()
    
    if not subscription:
        return None
    
    return {
        'plan_id': subscription.plan_id,
        'status': subscription.status,
        'start_date': subscription.start_date,
        'end_date': subscription.end_date,
        'days_remaining': (subscription.end_date - datetime.utcnow()).days if subscription.end_date else 0,
        'is_trial': subscription.is_trial if hasattr(subscription, 'is_trial') else False
    }
