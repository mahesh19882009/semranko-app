from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import json

from app.db.session import get_db
from app.api.deps import get_current_user
from app.db.models import User
from app.services.payment_service import (
    create_order,
    verify_payment_signature,
    handle_webhook,
    activate_subscription,
    get_subscription_status
)
from app.core.config import get_settings

router = APIRouter(prefix="/payments", tags=["Payments"])
settings = get_settings()


@router.post("/create-order")
async def create_payment_order(
    plan_id: int,
    amount: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a Razorpay payment order
    
    Args:
        plan_id: ID of the plan to purchase (0=starter, 1=pro, 2=agency)
        amount: Amount in paise (e.g., 50000 for ₹500)
    
    Returns:
        Order details including order_id, amount, and key
    """
    try:
        order_data = create_order(
            db=db,
            user=current_user,
            plan_id=plan_id,
            amount=amount
        )
        
        return {
            "success": True,
            "data": {
                "order_id": order_data["order_id"],
                "amount": order_data["amount"],
                "currency": order_data["currency"],
                "plan_id": order_data["plan_id"],
                "key_id": order_data.get("key_id", settings.RAZORPAY_KEY_ID or "mock_key_id")
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/verify-payment")
async def verify_payment(
    order_id: str,
    payment_id: str,
    signature: str,
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verify Razorpay payment signature and activate subscription
    
    Args:
        order_id: Razorpay order ID
        payment_id: Razorpay payment ID
        signature: Razorpay payment signature
        plan_id: ID of the purchased plan
    
    Returns:
        Subscription details
    """
    try:
        # Verify payment signature
        is_valid = verify_payment_signature(order_id, payment_id, signature)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment verification failed"
            )
        
        # Activate subscription
        subscription = activate_subscription(
            db=db,
            user=current_user,
            plan_id=plan_id,
            payment_id=payment_id,
            order_id=order_id
        )
        
        return {
            "success": True,
            "message": "Payment verified and subscription activated",
            "data": {
                "subscription_id": subscription.id,
                "plan_id": subscription.planId,
                "status": subscription.status,
                "end_date": subscription.endDate.isoformat() if subscription.endDate else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Razorpay webhook events
    
    This endpoint receives payment events from Razorpay
    """
    try:
        # Get the signature from headers
        signature = request.headers.get('X-Razorpay-Signature')
        
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing webhook signature"
            )
        
        # Parse the payload
        body = await request.body()
        payload = json.loads(body.decode('utf-8'))
        
        # Handle the webhook
        event_data = handle_webhook(payload, signature)
        
        if event_data and event_data['type'] == 'payment.captured':
            # Find user by email
            from app.services.auth_service import get_user_by_email
            user = get_user_by_email(db, event_data['user_email'])
            
            if user:
                # Activate subscription
                activate_subscription(
                    db=db,
                    user=user,
                    plan_id=int(event_data['plan_id']),
                    payment_id=event_data['payment_id'],
                    order_id=event_data['order_id']
                )
        
        return {"status": "success"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/subscription-status")
async def get_user_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current subscription status for the authenticated user
    
    Returns:
        Subscription details or None if no active subscription
    """
    try:
        subscription = get_subscription_status(db, current_user.id)
        
        return {
            "success": True,
            "data": subscription
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
