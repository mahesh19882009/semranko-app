from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
import threading
import requests
import json
import uuid
import base64
import http.client


from app.api.deps import db_session, get_current_user
from app.db.models import Keyword, KeywordCache, User, CreditLedger, Project
from app.services.keyword_service import get_project_keywords
from app.services.team_service import get_team_owner_id
from app.services.credit_service import deduct_credits, refund_credits
from app.core.config import get_settings
from app.core.errors import ApiError

import logging

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/keywords", tags=["keywords"])


def execute_direct_dataforseo_http_post(keywords_list: list, target_domain: str, pingback_url: str):
    """
    Isolated native HTTP client. 
    REMOVED 'pingback_url' tracking parameter to fix the low-level '//dataforseo.com' socket crash.
    """
    host = "://dataforseo.com"
    path = "/v3/serp/google/organic/task_post"
    
    task_elements = []
    for kw in keywords_list:
        # 🚨 PINGBACK_URL DELETED COMPLETELY FOR PURE HANDSHAKE TESTING
        task_elements.append({
            "keyword": kw,
            "location_code": 2840, # India
            "language_code": "en",
            "device": "desktop",
            "os": "windows"
        })
        
    master_payload = {
        "tasks": task_elements
    }

    # Extract raw hardcoded credentials natively
    username = "mahesh1988.2009@gmail.com"
    password = "6941ad7804dcd08e" # <-- Apne .env se aslee 69xxxx wala API Key password yahan type kar de!
    
    raw_auth_str = f"{username}:{password}"
    auth_bytes = raw_auth_str.encode('utf-8')
    base64_auth_str = base64.b64encode(auth_bytes).decode('utf-8')
    
    try:
        conn = http.client.HTTPSConnection(host, timeout=15)
        headers = {
            "Authorization": f"Basic {base64_auth_str}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        conn.request("POST", path, body=json.dumps(master_payload), headers=headers)
        response = conn.getresponse()
        res_data = response.read().decode('utf-8')
        
        print(f"[RAW CLIENT TRACE] Gateway Return HTTP Status: {response.status}")
        print(f"[RAW CLIENT TRACE] SUCCESS JSON RECEIVED! Payload Body: {res_data}")
            
        conn.close()
    except Exception as e:
        print(f"[RAW CLIENT TRACE] Low-level socket handshake collapsed: {str(e)}")


@router.get("/{project_id}/table")
def get_keyword_table(project_id: str, db: Session = Depends(db_session), user: dict = Depends(get_current_user)):
    keywords = db.scalars(select(Keyword).where(Keyword.projectId == project_id)).all()
    enriched_data = []
    for kw in keywords:
        cache = db.scalar(select(KeywordCache).where(KeywordCache.keyword == kw.keyword))
        enriched_data.append({
            "id": kw.id,
            "keyword": kw.keyword,
            "volume": cache.volume if cache else "—",
            "kd": cache.kd if cache else "—",
            "cpc": cache.cpc if cache else "—",
            "competition": cache.competition if cache else "—",
            "backlinks": cache.backlinks if cache else "—",
            "referring_domains": cache.referring_domains if cache else "—",
            "intent": cache.intent if cache else "—",
            "position": cache.position if cache else "Fetching...",
            "ai_badge": cache.ai_badge if cache else "No",
            "isActive": kw.isActive,
            "createdAt": kw.createdAt.isoformat() if kw.createdAt else None,
            "updatedAt": kw.updatedAt.isoformat() if kw.updatedAt else None,
        })
    return {"success": True, "data": enriched_data}


@router.get("/{project_id}")
def list_keywords(project_id: str, db: Session = Depends(db_session), user: dict = Depends(get_current_user)):
    keywords = get_project_keywords(db, user["userId"], project_id)
    return {"success": True, "data": keywords}


@router.post("/{project_id}")
async def create_keyword(
    project_id: str,
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> JSONResponse:
    keyword_text = payload.get("keyword")
    location = payload.get("location") or "India"
    
    if not keyword_text:
        raise ApiError(400, "Keyword is required")

    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user["userId"]))
    if not project:
        raise ApiError(404, "Project not found")

    normalized_keyword = keyword_text.strip().lower()
    if not normalized_keyword:
        raise ApiError(400, "Keyword is required")

    existing = db.scalar(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword == normalized_keyword,
        )
    )
    if existing:
        raise ApiError(409, "Keyword already exists for this project")

    user_record = db.scalar(select(User).where(User.id == user["userId"]))
    if not user_record:
        raise ApiError(404, "User not found")

    if user_record.creditBalance < 15:
        raise ApiError(400, "Insufficient credits. 15 credits required per keyword tracking entry.")

    try:
        user_record.creditBalance -= 15
        user_record.updatedAt = datetime.utcnow()
        
        owner_id = get_team_owner_id(db, user["userId"])
        deduct_credits(db, owner_id, 15.0, "ON_DEMAND_ADD", f"Day-one single tracking: {normalized_keyword}")

        keyword = Keyword(
            projectId=project_id,
            userId=user["userId"],
            keyword=normalized_keyword,
            location=location,
            device=(payload.get("device") or "desktop"),
            volume=0,
            kd=0,
            cpc=0.0,
            competition=0.0,
            backlinks=0.0,
            referring_domains=0.0,
            intent="—",
            position=0,
            ai_badge="—",
        )
        db.add(keyword)
        db.flush()

        cache_row = db.scalar(select(KeywordCache).where(KeywordCache.keyword == normalized_keyword))
        if not cache_row:
            cache_row = KeywordCache(
                keyword=normalized_keyword,
                location=location,
                volume=None,
                kd=None,
                cpc=None,
                competition=None,
                backlinks=None,
                referring_domains=None,
                intent=None,
                position=None,
                ai_badge=None,
            )
            db.add(cache_row)
        else:
            cache_row.position = "Fetching..."
            cache_row.updatedAt = datetime.utcnow()

        db.commit()
        db.refresh(keyword)

        pingback = settings.PINGBACK_URL if hasattr(settings, 'PINGBACK_URL') else ""
        if not pingback:
            pingback = f"{settings.FRONTEND_URL}/api/webhooks/dataforseo"

        # NATIVE ISOLATED THREADING DISPATCH FOR FAST MODAL CLOSURES
        t = threading.Thread(
            target=execute_direct_dataforseo_http_post, 
            args=([normalized_keyword], project.domain, pingback)
        )
        t.daemon = True
        t.start()

        return JSONResponse(status_code=201, content={
            "success": True,
            "message": "Keyword registered successfully.",
            "data": {
                "id": keyword.id,
                "keyword": keyword.keyword,
                "location": keyword.location,
                "device": keyword.device,
                "volume": keyword.volume,
                "kd": keyword.kd,
                "cpc": keyword.cpc,
                "competition": keyword.competition,
                "backlinks": keyword.backlinks,
                "referring_domains": keyword.referring_domains,
                "intent": keyword.intent,
                "position": keyword.position,
                "ai_badge": keyword.ai_badge,
                "isActive": keyword.isActive,
                "createdAt": keyword.createdAt.isoformat() if keyword.createdAt else None,
                "updatedAt": keyword.updatedAt.isoformat() if keyword.updatedAt else None,
            },
        })
    except Exception as e:
        db.rollback()
        logger.error(f"create_keyword failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create keyword")


@router.post("/{project_id}/bulk")
async def bulk_create_keywords(
    project_id: str,
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    keywords_list = payload.get("keywords", [])
    location = payload.get("location") or "India"

    if not keywords_list:
        raise ApiError(400, "keywords list is required")

    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user["userId"]))
    if not project:
        raise ApiError(404, "Project not found")

    normalized_keywords = []
    for kw in keywords_list:
        kw = kw.strip().lower()
        if kw:
            normalized_keywords.append(kw)

    if not normalized_keywords:
        return {
            "success": True,
            "message": "No valid keywords provided",
            "data": {"added": 0, "skipped": 0, "keywords": []},
        }

    existing = db.scalars(
        select(Keyword.keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword.in_(normalized_keywords),
        )
    ).all()
    existing_set = set(existing)

    added = []
    for kw in normalized_keywords:
        if kw in existing_set:
            continue

        keyword = Keyword(
            projectId=project_id,
            userId=user["userId"],
            keyword=kw,
            location=location,
            device="desktop",
            volume=0,
            kd=0,
            cpc=0.0,
            competition=0.0,
            backlinks=0.0,
            referring_domains=0.0,
            intent="—",
            position=0,
            ai_badge="—",
        )
        db.add(keyword)
        added.append(kw)
        existing_set.add(kw)

    if added:
        owner_id = get_team_owner_id(db, user["userId"])
        credits_needed = len(added) * 15
        deduct_credits(db, owner_id, float(credits_needed), "ON_DEMAND_ADD", f"Day-one tracking: {len(added)} keyword(s)")

    db.commit()

    for kw_text in added:
        cache_row = db.scalar(select(KeywordCache).where(KeywordCache.keyword == kw_text))
        if not cache_row:
            cache_row = KeywordCache(
                keyword=kw_text,
                location=location,
                volume=None,
                kd=None,
                cpc=None,
                competition=None,
                backlinks=None,
                referring_domains=None,
                intent=None,
                position=None,
                ai_badge=None,
            )
            db.add(cache_row)
        else:
            cache_row.position = "Fetching..."
            cache_row.updatedAt = datetime.utcnow()

    db.commit()

    pingback = settings.PINGBACK_URL if hasattr(settings, 'PINGBACK_URL') else ""
    if not pingback:
        pingback = f"{settings.FRONTEND_URL}/api/webhooks/dataforseo"

    if added:
        t = threading.Thread(
            target=execute_direct_dataforseo_http_post,
            args=(added, project.domain, pingback),
        )
        t.daemon = True
        t.start()

    return {
        "success": True,
        "message": f"Added {len(added)} keywords, skipped {len(normalized_keywords) - len(added)} duplicates",
        "data": {
            "added": len(added),
            "skipped": len(normalized_keywords) - len(added),
            "keywords": added,
        },
    }
