import logging
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException
from app.db.models import User, CreditLedger, TrackedKeyword, DataForSEOCost
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _to_float(value) -> float:
    return float(Decimal(str(value or 0)))


def _normalize_spendable_pools(user: User) -> tuple[float, float]:
    """Keep legacy creditBalance compatible with the separated spendable pools."""
    current = _to_float(getattr(user, "creditBalance", 0.0))
    plan = _to_float(getattr(user, "planCreditBalance", 0.0))
    purchased = _to_float(getattr(user, "purchasedCreditBalance", 0.0))
    if round(plan + purchased, 2) != round(current, 2):
        # Rows created by older code/tests have no pool attribution. Preserve the
        # value as plan spendable credits; migrated production rows are explicitly
        # grandfathered as purchased credits by Alembic.
        plan = current
        purchased = 0.0
        user.planCreditBalance = plan
        user.purchasedCreditBalance = purchased
    return plan, purchased


def _debit_spendable(user: User, amount: float) -> tuple[float, float, float, float]:
    plan, purchased = _normalize_spendable_pools(user)
    current = round(plan + purchased, 2)
    if current < amount:
        raise HTTPException(status_code=402, detail=f"Insufficient credits. Required: {amount}, Available: {current}")
    plan_used = min(plan, amount)
    purchased_used = amount - plan_used
    user.planCreditBalance = round(plan - plan_used, 2)
    user.purchasedCreditBalance = round(purchased - purchased_used, 2)
    user.creditBalance = round(user.planCreditBalance + user.purchasedCreditBalance, 2)
    return current, user.creditBalance, plan_used, purchased_used


def get_credit_balances(db: Session, user_id: str) -> dict:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    plan, purchased = _normalize_spendable_pools(user)
    return {
        "spendable": round(plan + purchased, 2),
        "planSpendable": round(plan, 2),
        "purchased": round(purchased, 2),
        "automaticRemaining": round(_to_float(getattr(user, "automaticCreditBalance", 0.0)), 2),
    }


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


def deduct_credits(db: Session, user_id: str, amount: float, action_type: str, description: str, related_order_id: str | None = None, project_id: str | None = None, keyword_id: str | None = None, task_id: str | None = None, request_id: str | None = None) -> float:
    if amount <= 0:
        return get_credit_balance(db, user_id)

    user = db.scalar(
        select(User).where(User.id == user_id).with_for_update()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if task_id:
        existing = db.scalar(
            select(CreditLedger).where(
                CreditLedger.taskId == task_id,
                CreditLedger.actionType == action_type,
                CreditLedger.userId == user_id,
                CreditLedger.status == "completed",
            )
        )
        if existing:
            return round(_to_float(getattr(user, "creditBalance", 0.0)), 2)

    balance_before, balance_after, plan_used, purchased_used = _debit_spendable(user, float(amount))
    db.add(user)

    ledger = CreditLedger(
        userId=user_id,
        ownerId=user_id,
        amount=-amount,
        actionType=action_type,
        description=description,
        relatedOrderId=related_order_id,
        creditsSpent=int(amount),
        timestamp=datetime.utcnow(),
        triggeredByUserId=user_id,
        status="completed",
        projectId=project_id,
        keywordId=keyword_id,
        creditsReserved=0.0,
        creditsConsumed=float(amount),
        creditsRefunded=0.0,
        netCreditChange=-float(amount),
        balanceBefore=balance_before,
        balanceAfter=balance_after,
        taskId=task_id,
        requestId=request_id,
        creditPool="spendable",
        planCreditsChange=-plan_used,
        purchasedCreditsChange=-purchased_used,
    )
    db.add(ledger)
    db.flush()
    db.commit()
    return user.creditBalance


def refund_credits(db: Session, user_id: str, amount: float, description: str, related_order_id: str | None = None, project_id: str | None = None, keyword_id: str | None = None, task_id: str | None = None, request_id: str | None = None) -> float:
    if amount <= 0:
        return get_credit_balance(db, user_id)

    user = db.scalar(
        select(User).where(User.id == user_id).with_for_update()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan, purchased = _normalize_spendable_pools(user)
    current = plan + purchased
    balance_before = round(current, 2)
    balance_after = round(current + amount, 2)
    user.planCreditBalance = round(plan + amount, 2)
    user.creditBalance = round(user.planCreditBalance + purchased, 2)
    db.add(user)

    ledger = CreditLedger(
        userId=user_id,
        ownerId=user_id,
        amount=amount,
        actionType="refund",
        description=description,
        relatedOrderId=related_order_id,
        creditsSpent=0,
        timestamp=datetime.utcnow(),
        triggeredByUserId=user_id,
        status="completed",
        projectId=project_id,
        keywordId=keyword_id,
        creditsConsumed=0.0,
        creditsRefunded=float(amount),
        netCreditChange=float(amount),
        balanceBefore=balance_before,
        balanceAfter=balance_after,
        taskId=task_id,
        requestId=request_id,
        creditPool="spendable",
        planCreditsChange=float(amount),
    )
    db.add(ledger)
    db.flush()
    db.commit()
    return user.creditBalance


def add_purchased_credits(db: Session, user_id: str, amount: float, description: str, related_order_id: str) -> float:
    if amount <= 0:
        return get_credit_balance(db, user_id)

    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_purchase = db.scalar(select(CreditLedger).where(
        CreditLedger.relatedOrderId == related_order_id,
        CreditLedger.creditPool == "purchased",
        CreditLedger.status == "completed",
    ))
    if existing_purchase:
        return round(_to_float(user.creditBalance), 2)

    plan, purchased = _normalize_spendable_pools(user)
    current = plan + purchased
    balance_before = round(current, 2)
    balance_after = round(current + amount, 2)
    user.purchasedCreditBalance = round(purchased + amount, 2)
    user.creditBalance = round(plan + user.purchasedCreditBalance, 2)
    db.add(user)

    ledger = db.scalar(select(CreditLedger).where(CreditLedger.relatedOrderId == related_order_id))
    if ledger is None:
        ledger = CreditLedger(userId=user_id, ownerId=user_id, relatedOrderId=related_order_id)
    ledger.amount = amount
    ledger.actionType = "purchase"
    ledger.description = description
    ledger.status = "completed"
    ledger.creditsReserved = 0.0
    ledger.creditsConsumed = float(amount)
    ledger.creditsRefunded = 0.0
    ledger.netCreditChange = float(amount)
    ledger.balanceBefore = balance_before
    ledger.balanceAfter = balance_after
    ledger.creditPool = "purchased"
    ledger.purchasedCreditsChange = float(amount)
    db.add(ledger)
    db.flush()
    db.commit()
    return user.creditBalance


def reserve_credits(
    db: Session,
    user_id: str,
    amount: float,
    action_type: str,
    description: str,
    reference: str | None = None,
    related_order_id: str | None = None,
    project_id: str | None = None,
    keyword_id: str | None = None,
    task_id: str | None = None,
    request_id: str | None = None,
) -> float:
    if amount <= 0:
        return get_credit_balance(db, user_id)

    user = db.scalar(
        select(User).where(User.id == user_id).with_for_update()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if reference:
        existing = db.scalar(
            select(CreditLedger).where(
                CreditLedger.actionType == "reservation",
                CreditLedger.description == f"{description} [ref:{reference}]",
                CreditLedger.userId == user_id,
                CreditLedger.status == "pending",
            )
        )
        if existing:
            return round(_to_float(getattr(user, "creditBalance", 0.0)), 2)

    balance_before, balance_after, plan_used, purchased_used = _debit_spendable(user, float(amount))
    db.add(user)

    ref_description = f"{description} [ref:{reference}]" if reference else description

    ledger = CreditLedger(
        userId=user_id,
        ownerId=user_id,
        amount=-amount,
        actionType="reservation",
        description=ref_description,
        relatedOrderId=related_order_id,
        status="pending",
        creditsSpent=0,
        timestamp=datetime.utcnow(),
        triggeredByUserId=user_id,
        projectId=project_id,
        keywordId=keyword_id,
        creditsReserved=float(amount),
        creditsConsumed=0.0,
        creditsRefunded=0.0,
        netCreditChange=-float(amount),
        balanceBefore=balance_before,
        balanceAfter=balance_after,
        taskId=task_id,
        requestId=request_id,
        creditPool="spendable",
        planCreditsChange=-plan_used,
        purchasedCreditsChange=-purchased_used,
    )
    db.add(ledger)
    db.flush()
    db.commit()
    return user.creditBalance


def consume_reserved(
    db: Session,
    user_id: str,
    reference: str,
    amount: float,
    action_type: str = "charge",
    description: str | None = None,
    related_order_id: str | None = None,
    project_id: str | None = None,
    keyword_id: str | None = None,
    task_id: str | None = None,
    request_id: str | None = None,
) -> float:
    if amount <= 0:
        return get_credit_balance(db, user_id)

    ledger = db.scalar(
        select(CreditLedger).where(
            CreditLedger.actionType == "reservation",
            CreditLedger.description.like(f"%[ref:{reference}]"),
            CreditLedger.userId == user_id,
            CreditLedger.status == "pending",
        )
    )
    if not ledger:
        raise HTTPException(status_code=404, detail="Reservation not found or already processed")

    remaining = float(ledger.creditsReserved or 0.0) - float(ledger.creditsConsumed or 0.0) - float(ledger.creditsRefunded or 0.0)
    actual_consume = min(float(amount), remaining)
    if actual_consume <= 0:
        return get_credit_balance(db, user_id)

    ledger.creditsConsumed = float(ledger.creditsConsumed or 0.0) + actual_consume
    ledger.actionType = action_type
    ledger.relatedOrderId = related_order_id or ledger.relatedOrderId
    ledger.projectId = project_id or ledger.projectId
    ledger.keywordId = keyword_id or ledger.keywordId
    ledger.taskId = task_id or ledger.taskId
    ledger.requestId = request_id or ledger.requestId
    ledger.status = "completed"

    db.add(ledger)
    db.flush()
    db.commit()
    return get_credit_balance(db, user_id)


def refund_reserved(
    db: Session,
    user_id: str,
    reference: str,
    amount: float,
    description: str | None = None,
    related_order_id: str | None = None,
    project_id: str | None = None,
    keyword_id: str | None = None,
    task_id: str | None = None,
    request_id: str | None = None,
) -> float:
    if amount <= 0:
        return get_credit_balance(db, user_id)

    ledger = db.scalar(
        select(CreditLedger).where(
            CreditLedger.description.like(f"%[ref:{reference}]"),
            CreditLedger.userId == user_id,
        )
    )
    if not ledger:
        raise HTTPException(status_code=404, detail="Reservation not found")

    remaining = float(ledger.creditsReserved or 0.0) - float(ledger.creditsConsumed or 0.0) - float(ledger.creditsRefunded or 0.0)
    actual_refund = min(float(amount), remaining)
    if actual_refund <= 0:
        return get_credit_balance(db, user_id)

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan, purchased = _normalize_spendable_pools(user)
    current = plan + purchased
    balance_before = round(current, 2)
    balance_after = round(current + actual_refund, 2)
    reserved_plan = abs(float(getattr(ledger, "planCreditsChange", 0.0) or 0.0))
    plan_refund = min(actual_refund, reserved_plan)
    purchased_refund = actual_refund - plan_refund
    user.planCreditBalance = round(plan + plan_refund, 2)
    user.purchasedCreditBalance = round(purchased + purchased_refund, 2)
    user.creditBalance = round(user.planCreditBalance + user.purchasedCreditBalance, 2)
    db.add(user)

    ledger.creditsRefunded = float(ledger.creditsRefunded or 0.0) + actual_refund
    ledger.netCreditChange = float(ledger.netCreditChange or 0.0) + actual_refund
    ledger.balanceBefore = balance_before
    ledger.balanceAfter = balance_after
    ledger.status = "refunded"
    ledger.planCreditsChange = float(ledger.planCreditsChange or 0.0) + plan_refund
    ledger.purchasedCreditsChange = float(ledger.purchasedCreditsChange or 0.0) + purchased_refund
    ledger.relatedOrderId = related_order_id or ledger.relatedOrderId
    ledger.projectId = project_id or ledger.projectId
    ledger.keywordId = keyword_id or ledger.keywordId
    ledger.taskId = task_id or ledger.taskId
    ledger.requestId = request_id or ledger.requestId

    db.add(ledger)
    db.flush()
    db.commit()
    return user.creditBalance


def reserve_automatic_credits(
    db: Session,
    user_id: str,
    amount: float,
    description: str,
    reference: str,
    project_id: str | None = None,
    keyword_id: str | None = None,
    task_id: str | None = None,
) -> float:
    """Atomically reserve core tracking credits without touching spendable credits."""
    if amount <= 0:
        return 0.0
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.scalar(select(CreditLedger).where(
        CreditLedger.userId == user_id,
        CreditLedger.creditPool == "automatic",
        CreditLedger.description == f"{description} [ref:{reference}]",
        CreditLedger.status.in_(["pending", "completed"]),
    ))
    if existing:
        return round(_to_float(getattr(user, "automaticCreditBalance", 0.0)), 2)
    current = _to_float(getattr(user, "automaticCreditBalance", 0.0))
    if current < amount:
        raise HTTPException(status_code=402, detail=f"Insufficient automatic tracking credits. Required: {amount}, Available: {current}")
    after = round(current - amount, 2)
    user.automaticCreditBalance = after
    ledger = CreditLedger(
        userId=user_id, ownerId=user_id, amount=-amount, actionType="reservation",
        description=f"{description} [ref:{reference}]", status="pending",
        creditsReserved=float(amount), creditsConsumed=0.0, creditsRefunded=0.0,
        netCreditChange=-float(amount), balanceBefore=current, balanceAfter=after,
        projectId=project_id, keywordId=keyword_id, taskId=task_id,
        creditPool="automatic", automaticCreditsChange=-float(amount),
        timestamp=datetime.utcnow(), triggeredByUserId=user_id,
    )
    db.add_all([user, ledger])
    db.commit()
    return after


def consume_automatic_reserved(
    db: Session,
    user_id: str,
    reference: str,
    amount: float,
    description: str,
    project_id: str | None = None,
    keyword_id: str | None = None,
    task_id: str | None = None,
) -> float:
    ledger = db.scalar(select(CreditLedger).where(
        CreditLedger.userId == user_id,
        CreditLedger.creditPool == "automatic",
        CreditLedger.description.like(f"%[ref:{reference}]"),
        CreditLedger.status == "pending",
    ).with_for_update())
    if not ledger:
        # A completed reservation makes retries idempotent.
        completed = db.scalar(select(CreditLedger).where(
            CreditLedger.userId == user_id,
            CreditLedger.creditPool == "automatic",
            CreditLedger.description.like(f"%[ref:{reference}]"),
            CreditLedger.status == "completed",
        ))
        if completed:
            return round(_to_float(db.scalar(select(User).where(User.id == user_id)).automaticCreditBalance), 2)
        raise HTTPException(status_code=404, detail="Automatic credit reservation not found")
    remaining = float(ledger.creditsReserved or 0) - float(ledger.creditsConsumed or 0) - float(ledger.creditsRefunded or 0)
    actual = min(float(amount), remaining)
    if actual <= 0:
        return round(_to_float(db.scalar(select(User).where(User.id == user_id)).automaticCreditBalance), 2)
    ledger.creditsConsumed = float(ledger.creditsConsumed or 0) + actual
    ledger.description = f"{description} [ref:{reference}]"
    ledger.projectId = project_id or ledger.projectId
    ledger.keywordId = keyword_id or ledger.keywordId
    ledger.taskId = task_id or ledger.taskId
    if ledger.creditsConsumed + float(ledger.creditsRefunded or 0) >= float(ledger.creditsReserved or 0):
        ledger.status = "completed"
        ledger.actionType = "charge"
    db.add(ledger)
    db.commit()
    user = db.scalar(select(User).where(User.id == user_id))
    return round(_to_float(user.automaticCreditBalance), 2)


def refund_automatic_reserved(db: Session, user_id: str, reference: str, amount: float, description: str) -> float:
    ledger = db.scalar(select(CreditLedger).where(
        CreditLedger.userId == user_id,
        CreditLedger.creditPool == "automatic",
        CreditLedger.description.like(f"%[ref:{reference}]"),
        CreditLedger.status == "pending",
    ).with_for_update())
    if not ledger:
        raise HTTPException(status_code=404, detail="Automatic credit reservation not found")
    remaining = float(ledger.creditsReserved or 0) - float(ledger.creditsConsumed or 0) - float(ledger.creditsRefunded or 0)
    actual = min(float(amount), remaining)
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    before = _to_float(user.automaticCreditBalance)
    user.automaticCreditBalance = round(before + actual, 2)
    ledger.creditsRefunded = float(ledger.creditsRefunded or 0) + actual
    ledger.automaticCreditsChange = float(ledger.automaticCreditsChange or 0) + actual
    ledger.netCreditChange = float(ledger.netCreditChange or 0) + actual
    ledger.balanceBefore = before
    ledger.balanceAfter = user.automaticCreditBalance
    ledger.description = f"{description} [ref:{reference}]"
    settled = float(ledger.creditsConsumed or 0) + float(ledger.creditsRefunded or 0)
    ledger.status = "refunded" if settled >= float(ledger.creditsReserved or 0) else "pending"
    db.add_all([user, ledger])
    db.commit()
    return user.automaticCreditBalance


def deduct_automatic_credits(
    db: Session,
    user_id: str,
    amount: float,
    description: str,
    project_id: str | None = None,
    keyword_id: str | None = None,
    task_id: str | None = None,
    request_id: str | None = None,
) -> float:
    """Direct idempotent automatic-pool charge for cache-hit/synchronous work."""
    if amount <= 0:
        return 0.0
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if task_id:
        existing = db.scalar(select(CreditLedger).where(
            CreditLedger.userId == user_id, CreditLedger.taskId == task_id,
            CreditLedger.creditPool == "automatic", CreditLedger.status == "completed",
        ))
        if existing:
            return round(_to_float(user.automaticCreditBalance), 2)
    before = _to_float(user.automaticCreditBalance)
    if before < amount:
        raise HTTPException(status_code=402, detail=f"Insufficient automatic tracking credits. Required: {amount}, Available: {before}")
    after = round(before - amount, 2)
    user.automaticCreditBalance = after
    ledger = CreditLedger(
        userId=user_id, ownerId=user_id, amount=-amount, actionType="charge",
        description=description, status="completed", creditsSpent=int(amount),
        creditsReserved=0.0, creditsConsumed=float(amount), creditsRefunded=0.0,
        netCreditChange=-float(amount), balanceBefore=before, balanceAfter=after,
        projectId=project_id, keywordId=keyword_id, taskId=task_id, requestId=request_id,
        creditPool="automatic", automaticCreditsChange=-float(amount),
        timestamp=datetime.utcnow(), triggeredByUserId=user_id,
    )
    db.add_all([user, ledger])
    db.commit()
    return after


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
        cost = settings.plan_config.credit_costs.get("tracked_keyword", 20)
        deduct_credits(db, user_id, cost, "charge", f"Tracked keyword: {keyword}")

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
            "credits_charged": cost,
        }
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to lock tracked keyword {keyword}: {exc}")
        refund_credits(db, user_id, cost, f"Refund: failed to lock tracked keyword {keyword}")
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


def track_dataforseo_cost(
    db: Session,
    user_id: str | None,
    task_type: str,
    endpoint: str,
    cost_credits: float,
    keyword_count: int = 1,
    cost_usd: float | None = None,
    meta: dict | None = None,
    project_id: str | None = None,
    keyword_id: str | None = None,
    task_id: str | None = None,
    request_id: str | None = None,
) -> DataForSEOCost:
    """Track DataForSEO API costs for profit/loss analysis."""
    cost = DataForSEOCost(
        userId=user_id,
        projectId=project_id,
        keywordId=keyword_id,
        taskType=task_type,
        endpoint=endpoint,
        costCredits=cost_credits,
        costUsd=cost_usd,
        keywordCount=keyword_count,
        meta=meta or {},
        taskId=task_id,
        requestId=request_id,
    )
    db.add(cost)
    db.flush()
    return cost


def get_dataforseo_costs(
    db: Session,
    user_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    task_type: str | None = None,
) -> list[dict]:
    """Get DataForSEO costs with optional filters."""
    query = select(DataForSEOCost)
    
    if user_id:
        query = query.where(DataForSEOCost.userId == user_id)
    
    if start_date:
        query = query.where(DataForSEOCost.createdAt >= start_date)
    
    if end_date:
        query = query.where(DataForSEOCost.createdAt <= end_date)
    
    if task_type:
        query = query.where(DataForSEOCost.taskType == task_type)
    
    query = query.order_by(DataForSEOCost.createdAt.desc())
    
    rows = db.scalars(query).all()
    
    return [
        {
            "id": r.id,
            "user_id": r.userId,
            "task_type": r.taskType,
            "endpoint": r.endpoint,
            "cost_credits": r.costCredits,
            "cost_usd": r.costUsd,
            "keyword_count": r.keywordCount,
            "meta": r.meta,
            "created_at": r.createdAt.isoformat() if r.createdAt else None,
        }
        for r in rows
    ]


def get_total_dataforseo_cost(
    db: Session,
    user_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict:
    """Get total DataForSEO costs summary."""
    query = select(func.sum(DataForSEOCost.costCredits), func.sum(DataForSEOCost.costUsd), func.count(DataForSEOCost.id))
    
    if user_id:
        query = query.where(DataForSEOCost.userId == user_id)
    
    if start_date:
        query = query.where(DataForSEOCost.createdAt >= start_date)
    
    if end_date:
        query = query.where(DataForSEOCost.createdAt <= end_date)
    
    result = db.execute(query).one()
    
    return {
        "total_credits": float(result[0] or 0),
        "total_usd": float(result[1] or 0) if result[1] else 0,
        "total_tasks": result[2] or 0,
    }
