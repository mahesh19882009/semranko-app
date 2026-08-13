"""Concurrency-safe paid-feature allowances scoped to subscription cycles."""

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import FeatureUsage, FeatureUsageReservation, Subscription, User
from app.services.plan_service import get_effective_plan_key, get_user_or_404, PLAN_DEFINITIONS


FEATURE_LIMIT_KEYS = {
    "manual_refresh": "manualRefreshLimit",
    "keyword_research": "keywordResearchLimit",
    "competitor_spy": "competitorSpyLimit",
}

UPGRADE_MESSAGE = "This feature is available on paid plans. Upgrade to continue."


def _billing_cycle(db: Session, user: User) -> tuple[datetime, datetime]:
    subscription = db.scalar(
        select(Subscription)
        .where(Subscription.userId == user.id, Subscription.isActive == True)
        .order_by(Subscription.startDate.desc())
    )
    if subscription and subscription.startDate and subscription.endDate:
        return subscription.startDate, subscription.endDate

    start = getattr(user, "lastCreditResetAt", None) or getattr(user, "planAnniversaryAt", None)
    if start is None:
        start = getattr(user, "createdAt", None) or datetime.utcnow()
    return start, start + timedelta(days=30)


def _limit_for(user: User, feature: str) -> tuple[str, int]:
    plan_key = get_effective_plan_key(user)
    plan = PLAN_DEFINITIONS.get(plan_key, PLAN_DEFINITIONS["free_trial"])
    return plan_key, int(plan.get(FEATURE_LIMIT_KEYS[feature], 0) or 0)


def _metadata(usage: FeatureUsage | None, limit: int, reset_at: datetime) -> dict:
    used = int(usage.usedUnits or 0) if usage else 0
    reserved = int(usage.reservedUnits or 0) if usage else 0
    return {
        "used": used,
        "reserved": reserved,
        "limit": limit,
        "remaining": max(0, limit - used - reserved),
        "resetAt": reset_at.isoformat(),
    }


def get_feature_usage(db: Session, user_id: str, feature: str) -> dict:
    user = get_user_or_404(db, user_id)
    _, limit = _limit_for(user, feature)
    cycle_start, cycle_end = _billing_cycle(db, user)
    usage = db.scalar(
        select(FeatureUsage).where(
            FeatureUsage.userId == user_id,
            FeatureUsage.feature == feature,
            FeatureUsage.cycleStart == cycle_start,
        )
    )
    return _metadata(usage, limit, cycle_end)


def ensure_feature_available(db: Session, user_id: str, feature: str) -> dict:
    user = get_user_or_404(db, user_id)
    plan_key, limit = _limit_for(user, feature)
    metadata = get_feature_usage(db, user_id, feature)
    if plan_key == "free_trial" or limit <= 0:
        raise ApiError(403, UPGRADE_MESSAGE, {
            "error": "upgrade_required",
            "upgrade_required": True,
            "feature": feature,
            "usage": metadata,
        })
    return metadata


def reserve_feature_usage(db: Session, user_id: str, feature: str, units: int, reference: str | None = None) -> tuple[str, dict]:
    if feature not in FEATURE_LIMIT_KEYS:
        raise ValueError(f"Unknown feature allowance: {feature}")
    if units <= 0:
        raise ValueError("Allowance reservation units must be positive")

    user = get_user_or_404(db, user_id)
    plan_key, limit = _limit_for(user, feature)
    cycle_start, cycle_end = _billing_cycle(db, user)
    if plan_key == "free_trial" or limit <= 0:
        raise ApiError(403, UPGRADE_MESSAGE, {
            "error": "upgrade_required",
            "upgrade_required": True,
            "feature": feature,
            "usage": _metadata(None, 0, cycle_end),
        })

    usage_id = str(uuid4())
    values = {
        "id": usage_id,
        "userId": user_id,
        "feature": feature,
        "cycleStart": cycle_start,
        "cycleEnd": cycle_end,
        "usedUnits": 0,
        "reservedUnits": 0,
    }
    dialect = db.bind.dialect.name
    if dialect == "postgresql":
        stmt = pg_insert(FeatureUsage).values(**values).on_conflict_do_nothing(
            index_elements=["userId", "feature", "cycleStart"]
        )
    elif dialect == "sqlite":
        stmt = sqlite_insert(FeatureUsage).values(**values).on_conflict_do_nothing(
            index_elements=["userId", "feature", "cycleStart"]
        )
    else:
        existing = db.scalar(select(FeatureUsage.id).where(
            FeatureUsage.userId == user_id,
            FeatureUsage.feature == feature,
            FeatureUsage.cycleStart == cycle_start,
        ))
        stmt = None
        if existing is None:
            db.add(FeatureUsage(**values))
            db.flush()
    if stmt is not None:
        db.execute(stmt)
        db.flush()

    usage = db.scalar(select(FeatureUsage).where(
        FeatureUsage.userId == user_id,
        FeatureUsage.feature == feature,
        FeatureUsage.cycleStart == cycle_start,
    ))
    result = db.execute(
        update(FeatureUsage)
        .where(
            FeatureUsage.id == usage.id,
            FeatureUsage.usedUnits + FeatureUsage.reservedUnits + units <= limit,
        )
        .values(reservedUnits=FeatureUsage.reservedUnits + units, updatedAt=datetime.utcnow())
    )
    if result.rowcount != 1:
        db.rollback()
        current = get_feature_usage(db, user_id, feature)
        raise ApiError(429, "Feature usage limit reached for this billing cycle.", {
            "error": "feature_limit_exceeded",
            "feature": feature,
            "usage": current,
        })

    reservation_ref = reference or f"{feature}:{user_id}:{uuid4()}"
    db.add(FeatureUsageReservation(
        usageId=usage.id,
        reference=reservation_ref,
        units=units,
        status="pending",
    ))
    db.commit()
    return reservation_ref, get_feature_usage(db, user_id, feature)


def finalize_feature_usage(db: Session, reference: str, consumed_units: int) -> dict:
    reservation = db.scalar(
        select(FeatureUsageReservation)
        .where(FeatureUsageReservation.reference == reference)
        .with_for_update()
    )
    if not reservation:
        raise ApiError(404, "Feature usage reservation not found")
    usage = db.scalar(select(FeatureUsage).where(FeatureUsage.id == reservation.usageId).with_for_update())
    if reservation.status != "pending":
        return _metadata(usage, _limit_for(get_user_or_404(db, usage.userId), usage.feature)[1], usage.cycleEnd)

    consumed = max(0, min(int(consumed_units), int(reservation.units)))
    usage.reservedUnits = max(0, int(usage.reservedUnits) - int(reservation.units))
    usage.usedUnits = int(usage.usedUnits) + consumed
    reservation.consumedUnits = consumed
    reservation.status = "completed" if consumed else "released"
    db.add_all([usage, reservation])
    db.commit()
    limit = _limit_for(get_user_or_404(db, usage.userId), usage.feature)[1]
    return _metadata(usage, limit, usage.cycleEnd)


def release_feature_usage(db: Session, reference: str) -> dict:
    return finalize_feature_usage(db, reference, 0)
