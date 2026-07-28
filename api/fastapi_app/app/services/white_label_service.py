from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import WhiteLabelSettings, User
import logging

logger = logging.getLogger(__name__)


def get_white_label_settings(db: Session, user_id: str) -> Optional[WhiteLabelSettings]:
    """
    Get white label settings for a user
    """
    return db.execute(
        select(WhiteLabelSettings)
        .where(WhiteLabelSettings.userId == user_id)
    ).scalar_one_or_none()


def create_or_update_white_label_settings(
    db: Session,
    user_id: str,
    company_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    primary_color: Optional[str] = None,
    secondary_color: Optional[str] = None,
    custom_domain: Optional[str] = None,
    hide_branding: Optional[bool] = None
) -> WhiteLabelSettings:
    """
    Create or update white label settings for a user
    """
    settings = get_white_label_settings(db, user_id)
    
    if settings:
        # Update existing
        if company_name is not None:
            settings.companyName = company_name
        if logo_url is not None:
            settings.logoUrl = logo_url
        if primary_color is not None:
            settings.primaryColor = primary_color
        if secondary_color is not None:
            settings.secondaryColor = secondary_color
        if custom_domain is not None:
            settings.customDomain = custom_domain
        if hide_branding is not None:
            settings.hideBranding = hide_branding
        
        db.commit()
        db.refresh(settings)
        return settings
    else:
        # Create new
        settings = WhiteLabelSettings(
            userId=user_id,
            companyName=company_name,
            logoUrl=logo_url,
            primaryColor=primary_color or "#000000",
            secondaryColor=secondary_color or "#ffffff",
            customDomain=custom_domain,
            hideBranding=hide_branding or False
        )
        
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings


def delete_white_label_settings(db: Session, user_id: str) -> bool:
    """
    Delete white label settings for a user
    """
    settings = get_white_label_settings(db, user_id)
    
    if settings:
        db.delete(settings)
        db.commit()
        return True
    
    return False


def is_white_label_enabled(db: Session, user_id: str) -> bool:
    """
    Check if white label is enabled for a user
    """
    settings = get_white_label_settings(db, user_id)
    return settings is not None and settings.hideBranding
