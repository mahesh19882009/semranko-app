import logging
from fastapi import APIRouter, Request, HTTPException
from app.core.config import get_settings
from app.services.cache_service import set_cached
from app.services.dataforseo_client import DataForSEOClient

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/dataforseo")
async def dataforseo_webhook(request: Request):
    """Receive DataForSEO pingback callbacks when SERP tasks complete."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    task_id = data.get("task_id") or data.get("id") or request.query_params.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="Missing task_id")

    logger.info(f"DataForSEO webhook received: task_id={task_id}")

    result_type = data.get("result_type", "regular")

    serp_data = DataForSEOClient._retrieve_task_result(task_id, result_type)
    if serp_data:
        keyword_text = serp_data.get("keyword", "")
        location = serp_data.get("location", "India")
        device = serp_data.get("device", "desktop")
        parsed = DataForSEOClient._parse_serp_result(serp_data)
        if parsed:
            for kw_text, parsed_data in parsed.items():
                set_cached("serp", ("serp", kw_text, location, device), parsed_data, ttl_seconds=3600)
            logger.info(f"DataForSEO webhook cached results: task_id={task_id} keywords={len(parsed)}")
        return {"success": True, "message": f"Task {task_id} results cached"}
    else:
        logger.warning(f"DataForSEO webhook: no results for task_id={task_id}")
        return {"success": True, "message": f"Task {task_id} no results yet"}
