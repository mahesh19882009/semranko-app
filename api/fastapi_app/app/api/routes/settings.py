from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional

from app.api.deps import db_session, get_current_user
from app.db.models import User, Subscription
from app.schemas.common import ok
from app.services.auth_service import change_user_password
from app.services.plan_service import get_subscription_status, get_effective_plan_key

router = APIRouter(prefix="/settings", tags=["settings"])


class UserGstInfo(BaseModel):
    gstin: Optional[str] = None
    gstName: Optional[str] = None
    gstAddress: Optional[str] = None
    gstState: Optional[str] = None
    gstStateCode: Optional[str] = None


class UserSettingsResponse(BaseModel):
    gstin: Optional[str]
    gstName: Optional[str]
    gstAddress: Optional[str]
    gstState: Optional[str]
    gstStateCode: Optional[str]
    companyGstin: str
    companyName: str
    companyAddress: str
    companyState: str
    companyStateCode: str


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class ProfileResponse(BaseModel):
    name: str
    email: str
    selectedPlan: str
    subscriptionStatus: str
    trialEndsAt: Optional[str]
    subscriptionEndDate: Optional[str]
    creditBalance: float
    createdAt: Optional[str]
    authProvider: str


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str = Field(min_length=8)


@router.get("/gst")
def get_user_gst_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    user = db.scalar(select(User).where(User.id == current_user["id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return ok("GST info fetched", {
        "gstin": user.userGstin,
        "gstName": user.userGstName,
        "gstAddress": user.userGstAddress,
        "gstState": user.userGstState,
        "gstStateCode": user.userGstStateCode,
        "companyGstin": "06FHDPK2516L1ZB",
        "companyName": "CodMonks Technologies",
        "companyAddress": "HOUSE NO 769, Sector-64, Ballabhgarh, Faridabad-121004, Haryana",
        "companyState": "Haryana",
        "companyStateCode": "06",
    })


@router.post("/gst")
def update_user_gst_info(
    payload: UserGstInfo,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    user = db.scalar(select(User).where(User.id == current_user["id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.userGstin = payload.gstin
    user.userGstName = payload.gstName
    user.userGstAddress = payload.gstAddress
    user.userGstState = payload.gstState
    user.userGstStateCode = payload.gstStateCode
    db.add(user)
    db.commit()
    db.refresh(user)
    return ok("GST info updated", {
        "gstin": user.userGstin,
        "gstName": user.userGstName,
        "gstAddress": user.userGstAddress,
        "gstState": user.userGstState,
        "gstStateCode": user.userGstStateCode,
    })


@router.get("/profile")
def get_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    user = db.scalar(select(User).where(User.id == current_user["id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    subscription = db.scalar(
        select(Subscription).where(
            Subscription.userId == user.id,
            Subscription.isActive == True
        )
    )

    return ok("Profile fetched", {
        "name": user.name,
        "email": user.email,
        "selectedPlan": get_effective_plan_key(user),
        "subscriptionStatus": get_subscription_status(user),
        "trialEndsAt": None if get_effective_plan_key(user) == "free_trial" else (user.trialEndsAt.isoformat() if user.trialEndsAt else None),
        "subscriptionEndDate": subscription.endDate.isoformat() if subscription and subscription.endDate and get_effective_plan_key(user) != "free_trial" else None,
        "creditBalance": user.creditBalance,
        "createdAt": user.createdAt.isoformat() if user.createdAt else None,
        "authProvider": user.authProvider,
    })


@router.put("/profile")
def update_profile(
    payload: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    user = db.scalar(select(User).where(User.id == current_user["id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.name = payload.name.strip()
    db.add(user)
    db.commit()
    db.refresh(user)

    return ok("Profile updated", {
        "name": user.name,
        "email": user.email,
    })


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    result = change_user_password(
        db,
        current_user["id"],
        payload.currentPassword,
        payload.newPassword,
    )
    return ok("Password changed successfully", result)
