"""Database-backed commercial configuration with deterministic config.py bootstrap defaults."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import CommercialConfigAudit, PlanCommercialConfig, SubscriptionEntitlementSnapshot, TopUpPackage, User
from datetime import datetime, timedelta

EDITABLE_PLAN_KEYS = ("free_trial", "starter", "pro", "agency")


def _plan_payload(row: PlanCommercialConfig) -> dict[str, Any]:
    return {
        "key": row.planKey, "name": row.name,
        "monthlyPrice": row.monthlyPriceInr, "yearlyPrice": row.monthlyPriceInr * 11,
        "monthlyPriceUsd": row.monthlyPriceUsd, "yearlyPriceUsd": row.monthlyPriceUsd * 11,
        "domain_limit": row.projectLimit, "keywordLimit": row.keywordLimit,
        "monthlyCredits": row.monthlyCredits, "automaticCredits": row.automaticCredits,
        "spendableCredits": row.monthlyCredits - row.automaticCredits,
        "manualRefreshLimit": row.manualRefreshLimit,
        "keywordResearchLimit": row.keywordResearchLimit,
        "competitorSpyLimit": row.competitorSpyLimit, "version": row.version,
    }


def bootstrap_commercial_config(db: Session) -> None:
    """Seed only missing rows from immutable launch defaults; never overwrite admin edits."""
    settings = get_settings()
    existing = set(db.scalars(select(PlanCommercialConfig.planKey)).all())
    for key in EDITABLE_PLAN_KEYS:
        if key in existing:
            continue
        plan = settings.plan_config.plans[key]
        db.add(PlanCommercialConfig(
            planKey=key, name=plan.name, monthlyPriceInr=plan.monthly_price_inr,
            monthlyPriceUsd=plan.monthly_price_usd, projectLimit=plan.domain_limit,
            keywordLimit=plan.keyword_limit, monthlyCredits=plan.monthly_credits,
            automaticCredits=plan.automatic_credits, manualRefreshLimit=plan.manual_refresh_limit,
            keywordResearchLimit=plan.keyword_research_limit, competitorSpyLimit=plan.competitor_spy_limit,
        ))
    if not db.scalars(select(TopUpPackage.id).limit(1)).first():
        for order, multiplier in enumerate((1, 2, 3, 5, 10), start=1):
            db.add(TopUpPackage(name=f"{multiplier * 600:,} credits", credits=multiplier * 600,
                                priceInr=multiplier * 100, priceUsd=0, displayOrder=order))
    db.commit()


def ensure_commercial_config(db: Session) -> None:
    if db.scalars(select(PlanCommercialConfig.id).limit(1)).first() is None:
        bootstrap_commercial_config(db)


def plan_definitions(db: Session) -> dict[str, dict[str, Any]]:
    ensure_commercial_config(db)
    settings = get_settings()
    rows = {row.planKey: row for row in db.scalars(select(PlanCommercialConfig)).all()}
    result: dict[str, dict[str, Any]] = {}
    for key, default in settings.plan_config.plans.items():
        row = rows.get(key)
        if row is None:
            # Enterprise remains static/sales-assisted and is never purchasable.
            result[key] = {
                "key": default.key, "name": default.name, "monthlyPrice": default.monthly_price_inr,
                "yearlyPrice": default.yearly_price_inr, "monthlyPriceUsd": default.monthly_price_usd,
                "yearlyPriceUsd": default.yearly_price_usd, "domain_limit": default.domain_limit,
                "keywordLimit": default.keyword_limit, "monthlyCredits": default.monthly_credits,
                "automaticCredits": default.automatic_credits, "spendableCredits": default.monthly_credits - default.automatic_credits,
                "manualRefreshLimit": default.manual_refresh_limit, "keywordResearchLimit": default.keyword_research_limit,
                "competitorSpyLimit": default.competitor_spy_limit,
            }
        else:
            result[key] = _plan_payload(row)
        result[key].update({
            "description": default.description, "cta": default.cta, "highlighted": default.highlighted,
            "refreshFrequency": default.refresh_frequency,
            "competitorsPerProject": default.competitors_per_project, "reportsPerMonth": default.reports_per_month,
            "weeklyTrackingEnabled": key in {"starter", "pro", "agency", "enterprise"},
        })
        result[key]["limits"] = {k: result[key][k] for k in (
            "keywordLimit", "monthlyCredits", "automaticCredits", "spendableCredits", "manualRefreshLimit",
            "keywordResearchLimit", "competitorSpyLimit", "weeklyTrackingEnabled",
        )}
    return result


def list_top_up_packages(db: Session, active_only: bool = True) -> list[TopUpPackage]:
    ensure_commercial_config(db)
    statement = select(TopUpPackage).order_by(TopUpPackage.displayOrder, TopUpPackage.id)
    if active_only:
        statement = statement.where(TopUpPackage.isActive.is_(True))
    return list(db.scalars(statement).all())


def serialize_top_up(package: TopUpPackage) -> dict[str, Any]:
    return {"id": package.id, "name": package.name, "credits": package.credits,
            "priceInr": package.priceInr, "priceUsd": package.priceUsd,
            "isActive": package.isActive, "displayOrder": package.displayOrder}


def audit(db: Session, admin_id: str, entity_type: str, entity_id: str, action: str, before: dict | None, after: dict | None) -> None:
    db.add(CommercialConfigAudit(adminUserId=admin_id, entityType=entity_type, entityId=entity_id,
                                 action=action, before=before, after=after))


def create_cycle_snapshot(db: Session, user: User, plan_key: str, cycle_start: datetime | None = None, cycle_end: datetime | None = None) -> SubscriptionEntitlementSnapshot:
    """Create one immutable snapshot from the current commercial definition."""
    now = cycle_start or datetime.utcnow()
    existing = db.scalar(select(SubscriptionEntitlementSnapshot).where(
        SubscriptionEntitlementSnapshot.userId == user.id,
        SubscriptionEntitlementSnapshot.cycleStart == now,
    ))
    if existing:
        return existing
    commercial = plan_definitions(db)[plan_key]
    snapshot = SubscriptionEntitlementSnapshot(
        userId=user.id, planKey=plan_key, cycleStart=now,
        cycleEnd=cycle_end or (now + timedelta(days=30)),
        projectLimit=commercial["domain_limit"], keywordLimit=commercial["keywordLimit"],
        monthlyCredits=commercial["monthlyCredits"], automaticCredits=commercial["automaticCredits"],
        manualRefreshLimit=commercial["manualRefreshLimit"], keywordResearchLimit=commercial["keywordResearchLimit"],
        competitorSpyLimit=commercial["competitorSpyLimit"],
    )
    db.add(snapshot)
    return snapshot


def _create_legacy_snapshot(db: Session, user: User) -> SubscriptionEntitlementSnapshot:
    """Build the deterministic legacy entitlement used as a safety fallback.

    This deliberately uses immutable config.py launch defaults, not a possibly
    Admin-edited Phase-19 offering. The migration persists the production
    backfill; this transient form keeps non-migrated/test-created rows safe
    without introducing a concurrent lazy-insert race.
    """
    key = (user.selectedPlan or "free_trial").strip().lower()
    settings = get_settings()
    if key not in EDITABLE_PLAN_KEYS:
        key = "free_trial"
    default = settings.plan_config.plans[key]
    start = user.lastCreditResetAt or user.planAnniversaryAt or user.createdAt or datetime.utcnow()
    existing = db.scalar(select(SubscriptionEntitlementSnapshot).where(
        SubscriptionEntitlementSnapshot.userId == user.id,
        SubscriptionEntitlementSnapshot.cycleStart == start,
    ))
    if existing:
        return existing
    snapshot = SubscriptionEntitlementSnapshot(
        userId=user.id, planKey=key, cycleStart=start,
        cycleEnd=start + timedelta(days=30) if key == "free_trial" else None,
        projectLimit=default.domain_limit, keywordLimit=default.keyword_limit,
        monthlyCredits=default.monthly_credits, automaticCredits=default.automatic_credits,
        manualRefreshLimit=default.manual_refresh_limit,
        keywordResearchLimit=default.keyword_research_limit,
        competitorSpyLimit=default.competitor_spy_limit,
    )
    return snapshot


def snapshot_entitlements(snapshot: SubscriptionEntitlementSnapshot) -> dict[str, Any]:
    defaults = get_settings().plan_config.plans[snapshot.planKey]
    return {
        "domain_limit": snapshot.projectLimit, "keywordLimit": snapshot.keywordLimit,
        "monthlyCredits": snapshot.monthlyCredits, "automaticCredits": snapshot.automaticCredits,
        "spendableCredits": snapshot.monthlyCredits - snapshot.automaticCredits,
        "manualRefreshLimit": snapshot.manualRefreshLimit, "keywordResearchLimit": snapshot.keywordResearchLimit,
        "competitorSpyLimit": snapshot.competitorSpyLimit,
        # Static, non-editable capabilities remain config metadata.
        "competitorsPerProject": defaults.competitors_per_project,
        "reportsPerMonth": defaults.reports_per_month,
        "weeklyTrackingEnabled": snapshot.planKey in {"starter", "pro", "agency"},
    }


def active_entitlements(db: Session, user: User) -> dict[str, Any]:
    """Return current-cycle immutable values, with a deterministic legacy fallback."""
    snapshot = db.scalars(select(SubscriptionEntitlementSnapshot).where(SubscriptionEntitlementSnapshot.userId == user.id).order_by(SubscriptionEntitlementSnapshot.cycleStart.desc()).limit(1)).first()
    if snapshot is None:
        snapshot = _create_legacy_snapshot(db, user)
    return snapshot_entitlements(snapshot)
