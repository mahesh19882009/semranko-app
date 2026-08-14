from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_admin
from app.db.models import PlanCommercialConfig, TopUpPackage, User
from app.schemas.common import ok
from app.services.commercial_config_service import (
    EDITABLE_PLAN_KEYS, audit, ensure_commercial_config, list_top_up_packages,
    plan_definitions, serialize_top_up,
)

router = APIRouter(prefix="/admin/commercial", tags=["admin-commercial"])

PLAN_FIELDS = {
    "monthlyPriceInr", "monthlyPriceUsd", "projectLimit", "keywordLimit", "monthlyCredits",
    "automaticCredits", "manualRefreshLimit", "keywordResearchLimit", "competitorSpyLimit",
}
PACKAGE_FIELDS = {"name", "credits", "priceInr", "priceUsd", "isActive", "displayOrder"}


def _plan(row: PlanCommercialConfig) -> dict:
    return {"key": row.planKey, "name": row.name, "monthlyPriceInr": row.monthlyPriceInr,
            "monthlyPriceUsd": row.monthlyPriceUsd, "yearlyPriceInr": row.monthlyPriceInr * 11,
            "yearlyPriceUsd": row.monthlyPriceUsd * 11, "projectLimit": row.projectLimit,
            "keywordLimit": row.keywordLimit, "monthlyCredits": row.monthlyCredits,
            "automaticCredits": row.automaticCredits, "spendableCredits": row.monthlyCredits - row.automaticCredits,
            "manualRefreshLimit": row.manualRefreshLimit, "keywordResearchLimit": row.keywordResearchLimit,
            "competitorSpyLimit": row.competitorSpyLimit, "version": row.version}


def _validate_plan(values: dict, key: str) -> None:
    if any(float(values[field]) < 0 for field in PLAN_FIELDS if field in values):
        raise HTTPException(422, "Commercial values cannot be negative")
    if key != "free_trial" and (int(values["projectLimit"]) <= 0 or int(values["keywordLimit"]) <= 0):
        raise HTTPException(422, "Paid plans require positive project and keyword limits")
    if int(values["automaticCredits"]) > int(values["monthlyCredits"]):
        raise HTTPException(422, "Automatic reserved credits cannot exceed monthly total credits")


@router.get("/plans")
def get_plans(db: Session = Depends(db_session), _: User = Depends(require_admin)) -> dict:
    ensure_commercial_config(db)
    rows = db.scalars(select(PlanCommercialConfig).order_by(PlanCommercialConfig.planKey)).all()
    return ok("Commercial plans fetched", [_plan(row) for row in rows])


@router.put("/plans/{plan_key}")
def update_plan(plan_key: str, payload: dict = Body(...), db: Session = Depends(db_session), admin: User = Depends(require_admin)) -> dict:
    if plan_key not in EDITABLE_PLAN_KEYS:
        raise HTTPException(404, "Unknown configurable plan")
    ensure_commercial_config(db)
    row = db.scalar(select(PlanCommercialConfig).where(PlanCommercialConfig.planKey == plan_key).with_for_update())
    if not row:
        raise HTTPException(404, "Plan configuration not found")
    before = _plan(row)
    candidate = {**before, **{field: payload[field] for field in PLAN_FIELDS & payload.keys()}}
    _validate_plan(candidate, plan_key)
    for field in PLAN_FIELDS & payload.keys():
        setattr(row, field, payload[field])
    row.version += 1
    after = _plan(row)
    audit(db, admin.id, "plan", row.id, "update", before, after)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Commercial configuration conflict") from exc
    return ok("Commercial plan updated", after)


@router.get("/top-up-packages")
def get_top_up_packages(db: Session = Depends(db_session), _: User = Depends(require_admin)) -> dict:
    return ok("Top-up packages fetched", [serialize_top_up(p) for p in list_top_up_packages(db, active_only=False)])


def _validate_package(values: dict) -> None:
    if not str(values.get("name", "")).strip():
        raise HTTPException(422, "Package name is required")
    if int(values["credits"]) <= 0 or float(values["priceInr"]) < 0 or float(values["priceUsd"]) < 0:
        raise HTTPException(422, "Package credits must be positive and prices cannot be negative")
    if int(values["displayOrder"]) < 0:
        raise HTTPException(422, "Display order cannot be negative")


@router.post("/top-up-packages")
def create_top_up_package(payload: dict = Body(...), db: Session = Depends(db_session), admin: User = Depends(require_admin)) -> dict:
    values = {field: payload.get(field) for field in PACKAGE_FIELDS}
    _validate_package(values)
    package = TopUpPackage(**values)
    db.add(package)
    try:
        db.flush()
        after = serialize_top_up(package)
        audit(db, admin.id, "top_up_package", package.id, "create", None, after)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Top-up display order must be unique") from exc
    return ok("Top-up package created", after)


@router.put("/top-up-packages/{package_id}")
def update_top_up_package(package_id: str, payload: dict = Body(...), db: Session = Depends(db_session), admin: User = Depends(require_admin)) -> dict:
    package = db.scalar(select(TopUpPackage).where(TopUpPackage.id == package_id).with_for_update())
    if not package:
        raise HTTPException(404, "Top-up package not found")
    before = serialize_top_up(package)
    for field in PACKAGE_FIELDS & payload.keys():
        setattr(package, field, payload[field])
    _validate_package(serialize_top_up(package))
    after = serialize_top_up(package)
    audit(db, admin.id, "top_up_package", package.id, "update", before, after)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Top-up display order must be unique") from exc
    return ok("Top-up package updated", after)
