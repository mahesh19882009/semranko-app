from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.white_label_service import (
    get_white_label_settings,
    create_or_update_white_label_settings,
    delete_white_label_settings,
    is_white_label_enabled,
)

router = APIRouter(prefix="/white-label", tags=["white-label"])


class WhiteLabelSettingsRequest(BaseModel):
    company_name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    custom_domain: Optional[str] = None
    hide_branding: Optional[bool] = None


@router.get("/settings")
async def get_white_label_settings_endpoint(
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Get white label settings for the current user
    """
    settings = get_white_label_settings(db, current_user["id"])
    
    if not settings:
        return ok("No white label settings", {"settings": None})
    
    return ok("White label settings retrieved", {
        "settings": {
            "id": settings.id,
            "companyName": settings.companyName,
            "logoUrl": settings.logoUrl,
            "primaryColor": settings.primaryColor,
            "secondaryColor": settings.secondaryColor,
            "customDomain": settings.customDomain,
            "hideBranding": settings.hideBranding,
            "updatedAt": settings.updatedAt.isoformat()
        }
    })


@router.post("/settings")
async def update_white_label_settings_endpoint(
    request: WhiteLabelSettingsRequest,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Create or update white label settings
    """
    settings = create_or_update_white_label_settings(
        db,
        current_user["id"],
        request.company_name,
        request.logo_url,
        request.primary_color,
        request.secondary_color,
        request.custom_domain,
        request.hide_branding
    )
    
    return ok("White label settings saved", {
        "id": settings.id,
        "companyName": settings.companyName,
        "logoUrl": settings.logoUrl,
        "primaryColor": settings.primaryColor,
        "secondaryColor": settings.secondaryColor,
        "customDomain": settings.customDomain,
        "hideBranding": settings.hideBranding,
        "updatedAt": settings.updatedAt.isoformat()
    })


@router.delete("/settings")
async def delete_white_label_settings_endpoint(
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete white label settings
    """
    success = delete_white_label_settings(db, current_user["id"])
    
    if success:
        return ok("White label settings deleted", {"success": True})
    else:
        return ok("No white label settings to delete", {"success": False})


@router.get("/enabled")
async def is_white_label_enabled_endpoint(
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Check if white label is enabled for the current user
    """
    enabled = is_white_label_enabled(db, current_user["id"])
    
    return ok("White label status retrieved", {"enabled": enabled})
