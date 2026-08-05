import logging
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException
from app.db.models import User, CreditLedger, TrackedKeyword
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _to_float(value) -> float:
    return float(Decimal(str(value or 0)))


def get_credit_balance(db: Session, user_id: str) -> float:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return round(_to_float(getattr(user, "creditBalance", 0.0)), 2)


def check_credits(db: Session, user_id: str, required: float) -> bool:
    balance = get_credit_balance(db, user_id)
    if balance < required:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Required: {required}, Available: {balance}",
        )
    return True


def deduct_credits(db: Session, user_id: str, amount: float, action_type: str, description: str, related_order_id: str | None = None) -> float:
    if amount <= 0:
        return get_credit_balance(db, user_id)

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    current = _to_float(getattr(user, "creditBalance", 0.0))
    if current < amount:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Required: {amount}, Available: {current}",
        )

    user.creditBalance = round(current - amount, 2)
    db.add(user)

    ledger = CreditLedger(
        userId=user_id,
        ownerId=user_id,  # Set ownerId to userId for individual users
        amount=-amount,
        actionType=action_type,
        description=description,
        relatedOrderId=related_order_id,
    )
    db.add(ledger)
    db.flush()
    db.commit()
    return user.creditBalance


def refund_credits(db: Session, user_id: str, amount: float, description: str, related_order_id: str | None = None) -> float:
    if amount <= 0:
        return get_credit_balance(db, user_id)

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    current = _to_float(getattr(user, "creditBalance", 0.0))
    user.creditBalance = round(current + amount, 2)
    db.add(user)

    ledger = CreditLedger(
        userId=user_id,
        ownerId=user_id,  # Set ownerId to userId for individual users
        amount=amount,
        actionType="refund",
        description=description,
        relatedOrderId=related_order_id,
    )
    db.add(ledger)
    db.flush()
    db.commit()
    return user.creditBalance


def add_purchased_credits(db: Session, user_id: str, amount: float, description: str, related_order_id: str) -> float:
    if amount <= 0:
        return get_credit_balance(db, user_id)

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    current = _to_float(getattr(user, "creditBalance", 0.0))
    user.creditBalance = round(current + amount, 2)
    db.add(user)

    ledger = CreditLedger(
        userId=user_id,
        ownerId=user_id,
        amount=amount,
        actionType="purchase",
        description=description,
        relatedOrderId=related_order_id,
        status="completed",
    )
    db.add(ledger)
    db.flush()
    db.commit()
    return user.creditBalance


def create_pending_ledger_entry(
    db: Session,
    user_id: str,
    owner_id: str,
    amount: float,
    action_type: str,
    description: str,
    related_order_id: str,
    plan_name: str | None = None,
) -> CreditLedger:
    ledger = CreditLedger(
        userId=user_id,
        ownerId=owner_id,
        amount=amount,
        actionType=action_type,
        description=description,
        relatedOrderId=related_order_id,
        status="pending",
        planName=plan_name,
    )
    db.add(ledger)
    db.flush()
    return ledger


def finalize_pending_ledger_entry(
    db: Session,
    order_id: str,
    amount_paid_inr: float | None = None,
    plan_name: str | None = None,
) -> CreditLedger | None:
    ledger = db.scalar(
        select(CreditLedger).where(
            CreditLedger.relatedOrderId == order_id,
            CreditLedger.status == "pending",
        )
    )
    if not ledger:
        return None

    ledger.status = "success"
    if amount_paid_inr is not None:
        ledger.amountPaidInr = amount_paid_inr
    if plan_name is not None:
        ledger.planName = plan_name
    db.add(ledger)
    db.flush()
    db.commit()
    db.refresh(ledger)
    return ledger


def lock_tracked_keyword(db: Session, user_id: str, keyword: str, location: str | None = None, device: str | None = None) -> dict:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.scalar(
        select(TrackedKeyword).where(
            TrackedKeyword.userId == user_id,
            TrackedKeyword.keyword == keyword,
            TrackedKeyword.isActive == True,
        )
    )
    if existing:
        db.delete(existing)

    try:
        deduct_credits(db, user_id, 20, "charge", f"Tracked keyword: {keyword}")

        tracked = TrackedKeyword(
            userId=user_id,
            keyword=keyword,
            location=location,
            device=device,
            lockedAt=datetime.utcnow(),
            lockedUntil=datetime.utcnow() + timedelta(days=30),
            isActive=True,
        )
        db.add(tracked)
        db.flush()

        return {
            "id": tracked.id,
            "keyword": tracked.keyword,
            "lockedAt": tracked.lockedAt.isoformat(),
            "lockedUntil": tracked.lockedUntil.isoformat(),
            "credits_charged": 20,
        }
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to lock tracked keyword {keyword}: {exc}")
        refund_credits(db, user_id, 20, f"Refund: failed to lock tracked keyword {keyword}")
        raise


def unlock_tracked_keyword(db: Session, user_id: str, keyword: str) -> dict:
    tracked = db.scalar(
        select(TrackedKeyword).where(
            TrackedKeyword.userId == user_id,
            TrackedKeyword.keyword == keyword,
            TrackedKeyword.isActive == True,
        )
    )
    if not tracked:
        raise HTTPException(status_code=404, detail="Tracked keyword not found")

    tracked.isActive = False
    db.add(tracked)
    db.flush()

    return {
        "id": tracked.id,
        "keyword": tracked.keyword,
        "unlockedAt": datetime.utcnow().isoformat(),
        "refunded": 0,
    }


def get_active_tracked_keywords(db: Session, user_id: str) -> list[dict]:
    rows = db.scalars(
        select(TrackedKeyword).where(
            TrackedKeyword.userId == user_id,
            TrackedKeyword.isActive == True,
        )
    ).all()

    return [
        {
            "id": r.id,
            "keyword": r.keyword,
            "location": r.location,
            "device": r.device,
            "lockedAt": r.lockedAt.isoformat() if r.lockedAt else None,
            "lockedUntil": r.lockedUntil.isoformat() if r.lockedUntil else None,
            "track_aio": r.trackAio,
        }
        for r in rows
    ]
