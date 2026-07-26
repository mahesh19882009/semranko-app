import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.security import get_current_user
from app.db.session import get_db
from app.db.models import User, Subscription
from app.services.payment_service import create_order, verify_payment_signature, activate_subscription
from app.core.config import FREE_PLAN_LIMITS, get_settings

router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/create-order")
async def create_payment_order(
    plan_id: int = Query(..., description="Plan ID to upgrade to"),
    amount: int = Query(..., description="Amount in smallest currency unit (e.g., paise)"),
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
        # Check credit balance
        available_credit = float(getattr(current_user, "creditBalance", 0.0) or 0.0)
        available_credit_paise = int(round(available_credit * 100))
        applied_credit_paise = min(amount, available_credit_paise)
        net_amount_paise = amount - applied_credit_paise

        # 100% Credit Coverage Case
        if net_amount_paise == 0:
            order_id = f"order_credit_{uuid.uuid4().hex[:16]}"
            subscription = activate_subscription(
                db=db,
                user_id=current_user.id,
                plan_id=plan_id,
                payment_id=f"pay_credit_{uuid.uuid4().hex[:8]}",
                order_id=order_id
            )
            credit_deducted = round(applied_credit_paise / 100.0, 2)
            current_user.creditBalance = round(max(0.0, available_credit - credit_deducted), 2)
            db.add(current_user)
            db.commit()

            return {
                "order_id": order_id,
                "amount": amount,
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
        
        return {
            "order_id": order["id"],
            "amount": amount,
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
    Expected body: { razorpay_order_id, razorpay_payment_id, razorpay_signature, plan_id, credit_applied }
    """
    razorpay_order_id = request_data.get("razorpay_order_id")
    razorpay_payment_id = request_data.get("razorpay_payment_id")
    razorpay_signature = request_data.get("razorpay_signature")
    plan_id = request_data.get("plan_id")
    credit_applied = float(request_data.get("credit_applied", 0.0) or 0.0)
    
    if razorpay_order_id is None or razorpay_payment_id is None or razorpay_signature is None or plan_id is None:
        raise HTTPException(status_code=400, detail="Missing required payment fields")
    
    try:
        is_valid = verify_payment_signature(
            order_id=razorpay_order_id,
            payment_id=razorpay_payment_id,
            signature=razorpay_signature
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid payment signature")
        
        subscription = activate_subscription(
            db=db,
            user_id=current_user.id,
            plan_id=plan_id,
            payment_id=razorpay_payment_id,
            order_id=razorpay_order_id
        )

        if credit_applied > 0:
            current_user.creditBalance = round(max(0.0, (getattr(current_user, "creditBalance", 0.0) or 0.0) - credit_applied), 2)
            db.add(current_user)
            db.commit()
        
        return {
            "message": "Payment verified successfully",
            "subscription": {
                "id": subscription.id,
                "status": subscription.status,
                "plan_id": subscription.planId
            }
        }
    except HTTPException:
        raise
    except Exception as e:
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
        return {
            "plan_name": "Free",
            "plan_id": None,
            "status": "free",
            "limits": FREE_PLAN_LIMITS
        }
    
    # Return basic plan info.
    return {
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
    }

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
    
    return {"message": "Subscription cancelled successfully"}

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
    
    return {"message": "Subscription reactivated successfully"}
