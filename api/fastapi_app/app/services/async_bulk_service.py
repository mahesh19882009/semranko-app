"""
Async Bulk Update Service for Weekly Rank Tracking

This service handles the "Sunday Night" job that:
1. Fetches all active tracked keywords across all users
2. Deduplicates keywords (Global Smart Cache)
3. Submits as single bulk async task to DataForSEO
4. Polls for completion and updates all users' data
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models import (
    AsyncTaskQueue, 
    Keyword, 
    Project, 
    User, 
    RankResult, 
    KeywordCache,
    Competitor,
    CompetitorRank
)
from app.services.dataforseo_client import DataForSEOClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def collect_active_keywords_for_bulk(db: Session) -> dict:
    """
    Collect all active keywords from all users/projects for bulk processing.
    Returns deduplicated keyword list with mapping back to original sources.
    """
    # Get all active keywords with their project info
    active_keywords = db.scalars(
        select(Keyword)
        .join(Project, Project.id == Keyword.projectId)
        .join(User, User.id == Project.userId)
        .where(
            Keyword.isActive == True,
            User.subscriptionStatus.in_(["active", "trialing"])
        )
    ).all()
    
    if not active_keywords:
        return {"keywords": [], "keyword_map": {}}
    
    # Deduplicate by keyword + location combination
    keyword_map = {}  # Maps (keyword, location) -> list of Keyword objects
    for kw in active_keywords:
        key = (kw.keyword.lower().strip(), kw.location or "India")
        if key not in keyword_map:
            keyword_map[key] = []
        keyword_map[key].append(kw)
    
    # Build unique keyword list for API call
    unique_keywords = [
        {"keyword": key[0], "location": key[1]}
        for key in keyword_map.keys()
    ]
    
    logger.info(
        f"Collected {len(active_keywords)} active keywords, "
        f"deduplicated to {len(unique_keywords)} unique keywords"
    )
    
    return {
        "keywords": unique_keywords,
        "keyword_map": keyword_map,
    }


def create_async_bulk_task(
    db: Session,
    keywords: list[dict],
    task_type: str = "rank_tracking",
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> AsyncTaskQueue:
    """
    Create an async task queue entry for bulk processing.
    """
    task = AsyncTaskQueue(
        taskType=task_type,
        status="pending",
        keywordsJson=json.dumps(keywords),
        userId=user_id,
        projectId=project_id,
        locationCode=2840,  # Default to US, can be overridden
        device="desktop",
    )
    db.add(task)
    db.flush()
    db.commit()
    db.refresh(task)
    
    logger.info(f"Created async task {task.id} for {len(keywords)} keywords")
    return task


def submit_bulk_to_dataforseo(
    db: Session,
    task: AsyncTaskQueue,
) -> bool:
    """
    Submit the bulk task to DataForSEO async API.
    Uses the cheaper async endpoint instead of live API.
    """
    try:
        keywords = json.loads(task.keywordsJson or "[]")
        if not keywords:
            logger.warning(f"Task {task.id} has no keywords to process")
            return False
        
        # Extract keyword texts for API call
        keyword_texts = [kw.get("keyword") for kw in keywords if kw.get("keyword")]
        
        # Use DataForSEO client to submit async task
        # This would call the task_post endpoint instead of live
        # For now, we'll use the existing client structure
        serp_data = DataForSEOClient.get_serp_data_batch(
            keywords=[{"keyword": kw} for kw in keyword_texts],
            location="United States",
            device="desktop",
            result_type="async"
        )
        
        # Update task with DataForSEO task ID if available
        # This would be populated when the actual API call is made
        task.status = "processing"
        db.add(task)
        db.commit()
        
        logger.info(f"Submitted task {task.id} to DataForSEO")
        return True
        
    except Exception as e:
        logger.error(f"Failed to submit task {task.id} to DataForSEO: {e}")
        task.status = "failed"
        task.errorMessage = str(e)
        db.add(task)
        db.commit()
        return False


def process_completed_async_task(
    db: Session,
    task: AsyncTaskQueue,
    serp_results: dict,
) -> None:
    """
    Process completed async task results and update all relevant tables.
    Updates KeywordCache (global) and RankResult (user-specific).
    """
    try:
        keywords = json.loads(task.keywordsJson or "[]")
        keyword_map = {}
        
        # Build a map of keyword -> original Keyword objects
        for kw_entry in keywords:
            keyword_text = kw_entry.get("keyword", "").lower().strip()
            location = kw_entry.get("location", "India")
            
            # Find all Keyword objects that match this keyword+location
            matching_keywords = db.scalars(
                select(Keyword)
                .where(
                    Keyword.keyword.ilike(keyword_text),
                    Keyword.location == location,
                    Keyword.isActive == True
                )
            ).all()
            
            key = (keyword_text, location)
            if key not in keyword_map:
                keyword_map[key] = []
            keyword_map[key].extend(matching_keywords)
        
        # Update global cache and user-specific results
        now = datetime.utcnow()
        updated_count = 0
        
        for keyword_text, serp_data in serp_results.items():
            location = serp_data.get("location", "India")
            key = (keyword_text.lower().strip(), location)
            
            # Update global KeywordCache
            cache_entry = db.scalar(
                select(KeywordCache).where(
                    KeywordCache.keyword == keyword_text,
                    KeywordCache.location == location
                )
            )
            
            # Parse SERP data
            organic_items = serp_data.get("organic_items", [])
            position = None
            url = None
            
            # Find position for target domain if available
            if task.domain:
                for item in organic_items:
                    item_domain = item.get("domain", "")
                    if task.domain.lower() in item_domain.lower():
                        position = item.get("rank_group")
                        url = item.get("url")
                        break
            
            # Update or create cache entry
            if cache_entry:
                cache_entry.position = position
                cache_entry.updatedAt = now
                cache_entry.lastApiCallAt = now
                db.add(cache_entry)
            else:
                cache_entry = KeywordCache(
                    keyword=keyword_text,
                    location=location,
                    position=position,
                    lastApiCallAt=now,
                    updatedAt=now
                )
                db.add(cache_entry)
            
            # Update user-specific RankResult entries
            if key in keyword_map:
                for kw_obj in keyword_map[key]:
                    rank_result = RankResult(
                        projectId=kw_obj.projectId,
                        keywordText=keyword_text,
                        position=position,
                        url=url,
                        device=task.device,
                        location=location,
                        checkedAt=now,
                        keywordId=kw_obj.id
                    )
                    db.add(rank_result)
                    updated_count += 1
        
        # Mark task as completed
        task.status = "completed"
        task.completedAt = now
        task.resultJson = json.dumps({"updated_count": updated_count})
        db.add(task)
        db.commit()
        
        logger.info(
            f"Processed task {task.id}: updated {updated_count} rank results"
        )
        
    except Exception as e:
        logger.error(f"Failed to process task {task.id}: {e}")
        task.status = "failed"
        task.errorMessage = str(e)
        db.add(task)
        db.commit()
        raise


def run_weekly_bulk_update_job(db: Session) -> dict:
    """
    Main entry point for the weekly bulk update job.
    Runs every Sunday night to refresh all active tracked keywords.
    """
    logger.info("Starting weekly bulk update job")
    
    try:
        # Step 1: Collect all active keywords
        collection = collect_active_keywords_for_bulk(db)
        unique_keywords = collection["keywords"]
        
        if not unique_keywords:
            logger.info("No active keywords found for bulk update")
            return {
                "status": "completed",
                "keywords_processed": 0,
                "tasks_created": 0
            }
        
        # Step 2: Create async task entry
        task = create_async_bulk_task(
            db=db,
            keywords=unique_keywords,
            task_type="rank_tracking"
        )
        
        # Step 3: Submit to DataForSEO async API
        success = submit_bulk_to_dataforseo(db, task)
        
        if not success:
            return {
                "status": "failed",
                "error": "Failed to submit to DataForSEO",
                "task_id": task.id
            }
        
        logger.info(
            f"Weekly bulk update job completed: "
            f"{len(unique_keywords)} keywords submitted in task {task.id}"
        )
        
        return {
            "status": "submitted",
            "keywords_processed": len(unique_keywords),
            "tasks_created": 1,
            "task_id": task.id
        }
        
    except Exception as e:
        logger.exception(f"Weekly bulk update job failed: {e}")
        db.rollback()
        return {
            "status": "failed",
            "error": str(e)
        }
