from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional

from app.api.deps import db_session, get_current_user
from app.db.models import User
from app.schemas.common import ok

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


@router.get("/gst")
def get_user_gst_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    return ok("GST info fetched", {
        "gstin": current_user.userGstin,
        "gstName": current_user.userGstName,
        "gstAddress": current_user.userGstAddress,
        "gstState": current_user.userGstState,
        "gstStateCode": current_user.userGstStateCode,
        "companyGstin": "06FHDPK2516L1ZB",
        "companyName": "CodMonks Technologies",
        "companyAddress": "HOUSE NO 769, Sector-64, Ballabhgarh, Faridabad-121004, Haryana",
        "companyState": "Haryana",
        "companyStateCode": "06",
    })


@router.post("/gst")
def update_user_gst_info(
    payload: UserGstInfo,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    current_user.userGstin = payload.gstin
    current_user.userGstName = payload.gstName
    current_user.userGstAddress = payload.gstAddress
    current_user.userGstState = payload.gstState
    current_user.userGstStateCode = payload.gstStateCode
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return ok("GST info updated", {
        "gstin": current_user.userGstin,
        "gstName": current_user.userGstName,
        "gstAddress": current_user.userGstAddress,
        "gstState": current_user.userGstState,
        "gstStateCode": current_user.userGstStateCode,
    })