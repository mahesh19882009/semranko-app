from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.api_key_service import (
    create_api_key,
    get_user_api_keys,
    deactivate_api_key,
    delete_api_key,
)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class CreateApiKeyRequest(BaseModel):
    name: str
    expires_in_days: Optional[int] = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key: str
    isActive: bool
    lastUsed: Optional[str]
    createdAt: str
    expiresAt: Optional[str]


@router.post("/create")
async def create_api_key_endpoint(
    request: CreateApiKeyRequest,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new API key
    """
    api_key = create_api_key(
        db,
        current_user["id"],
        request.name,
        request.expires_in_days
    )
    
    return ok("API key created", {
        "id": api_key.id,
        "name": api_key.name,
        "key": api_key.key,
        "isActive": api_key.isActive,
        "lastUsed": api_key.lastUsed.isoformat() if api_key.lastUsed else None,
        "createdAt": api_key.createdAt.isoformat(),
        "expiresAt": api_key.expiresAt.isoformat() if api_key.expiresAt else None
    })


@router.get("/list")
async def list_api_keys(
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    List all API keys for the current user
    """
    api_keys = get_user_api_keys(db, current_user["id"])
    
    keys_data = [
        {
            "id": key.id,
            "name": key.name,
            "key": key.key[:8] + "..." if len(key.key) > 8 else key.key,  # Partial key for security
            "isActive": key.isActive,
            "lastUsed": key.lastUsed.isoformat() if key.lastUsed else None,
            "createdAt": key.createdAt.isoformat(),
            "expiresAt": key.expiresAt.isoformat() if key.expiresAt else None
        }
        for key in api_keys
    ]
    
    return ok("API keys retrieved", {"keys": keys_data})


@router.post("/{api_key_id}/deactivate")
async def deactivate_api_key_endpoint(
    api_key_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Deactivate an API key
    """
    success = deactivate_api_key(db, api_key_id, current_user["id"])
    
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return ok("API key deactivated", {"success": True})


@router.delete("/{api_key_id}")
async def delete_api_key_endpoint(
    api_key_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an API key
    """
    success = delete_api_key(db, api_key_id, current_user["id"])
    
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return ok("API key deleted", {"success": True})
