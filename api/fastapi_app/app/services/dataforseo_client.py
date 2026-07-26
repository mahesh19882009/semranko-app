import base64
import logging
import requests
from typing import Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class DataForSEOClient:
    BASE_URL = "https://api.dataforseo.com/v3"

    @staticmethod
    def _get_headers():
        if not settings.DATAFORSEO_LOGIN or not settings.DATAFORSEO_PASSWORD:
            return None
        cred = f"{settings.DATAFORSEO_LOGIN}:{settings.DATAFORSEO_PASSWORD}"
        token = base64.b64encode(cred.encode()).decode()
        return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

    @classmethod
    def get_rank(cls, keyword: str, domain: str, location_code: int = 2840, device: str = "desktop") -> Optional[dict]:
        """Fetches SERP data to find a domain's rank."""
        headers = cls._get_headers()
        if not headers: return None
        
        url = f"{cls.BASE_URL}/serp/google/organic/live/advanced"
        payload = [{
            "keyword": keyword, "location_code": location_code, "language_code": "en",
            "device": device, "os": "windows", "depth": 20
        }]
        
        try:
            response = requests.post(url, json=payload, headers=headers).json()
            if response.get("status_code") == 20000:
                for task in response.get("tasks", []):
                    for result in task.get("result", []):
                        for item in result.get("items", []):
                            if item.get("type") == "organic" and domain in item.get("domain", ""):
                                return {"position": item.get("rank_absolute"), "url": item.get("url")}
            return None
        except Exception as e:
            logger.error(f"DataForSEO SERP Error: {e}")
            return None

    @classmethod
    def get_backlinks(cls, target_domain: str, limit: int = 100) -> list:
        """Fetches top backlinks for a domain."""
        headers = cls._get_headers()
        if not headers: return []
        
        url = f"{cls.BASE_URL}/backlinks/backlinks/live"
        payload = [{"target": target_domain, "limit": limit, "order_by": ["rank_desc"]}]
        
        try:
            response = requests.post(url, json=payload, headers=headers).json()
            backlinks = []
            if response.get("status_code") == 20000:
                for task in response.get("tasks", []):
                    for result in task.get("result", []):
                        for bl in result.get("backlinks", []):
                            backlinks.append({
                                "source_url": bl.get("page_from", {}).get("url"),
                                "source_domain": bl.get("page_from", {}).get("domain"),
                                "anchor": bl.get("anchor"),
                                "rank": bl.get("page_from_rank"),
                                "first_seen": bl.get("first_seen")
                            })
            return backlinks
        except Exception as e:
            logger.error(f"DataForSEO Backlinks Error: {e}")
            return []