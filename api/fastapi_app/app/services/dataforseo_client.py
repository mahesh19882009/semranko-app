import base64
import logging
import requests
from typing import Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

LOCATION_MAP = {
    "India": 2356,
    "United States": 2840,
    "United Kingdom": 2826,
    "Canada": 2124,
    "Australia": 2036,
    "Germany": 2276,
    "France": 2250,
    "Japan": 2392,
    "Brazil": 2076,
}

DEVICE_MAP = {
    "mobile": "mobile",
    "desktop": "desktop",
}


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
    def _find_domain_in_results(cls, organic_items, target_domain):
        target = target_domain.lower()
        for idx, item in enumerate(organic_items, start=1):
            item_domain = item.get("domain", "")
            item_url = item.get("url", "")
            if target in item_domain.lower() or target in (item_url or "").lower():
                return {"position": idx, "url": item_url or f"https://{item_domain}"}
        return None

    @classmethod
    def get_rank(cls, keyword: str, domain: str, location: str = "India", device: str = "desktop") -> Optional[dict]:
        headers = cls._get_headers()
        if not headers:
            return None

        location_code = LOCATION_MAP.get(location, 2356)
        se_type = DEVICE_MAP.get(device, "desktop")

        payload = [{
            "keyword": keyword,
            "location_code": location_code,
            "language_code": "en",
            "depth": 100,
            "se_type": se_type,
        }]

        try:
            response = requests.post(
                f"{cls.BASE_URL}/serp/google/organic/task_post",
                auth=HTTPBasicAuth(settings.SERP_API_LOGIN or "", settings.SERP_API_KEY or ""),
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            if response.status_code != 200:
                logger.error(f"DataForSEO task_post HTTP error: {response.status_code}")
                return None

            task_response = response.json()
            if task_response.get("status_code") != 20000:
                logger.error(f"DataForSEO task_post failed: {task_response}")
                return None

            task_id = task_response.get("tasks", [{}])[0].get("id")
            if not task_id:
                return None

            result_response = requests.get(
                f"{cls.BASE_URL}/serp/google/organic/task_get/{task_id}",
                auth=HTTPBasicAuth(settings.SERP_API_LOGIN or "", settings.SERP_API_KEY or ""),
                timeout=30,
            )

            if result_response.status_code != 200:
                logger.error(f"DataForSEO task_get HTTP error: {result_response.status_code}")
                return None

            result_data = result_response.json()
            if result_data.get("status_code") != 20000:
                return None

            tasks = result_data.get("tasks", [])
            if not tasks:
                return None

            task_result = tasks[0]
            if task_result.get("status_code") != 20000:
                return None

            organic_items = task_result.get("result", [{}])[0].get("items", [])
            rank = cls._find_domain_in_results(organic_items, domain)

            if rank is None:
                item_groups = task_result.get("result", [{}])[0].get("item_groups", [])
                for group in item_groups:
                    if group.get("type") == "featured_snippet":
                        snippet_items = group.get("items", [])
                        for item in snippet_items:
                            if domain.lower() in (item.get("domain") or "").lower():
                                return {"position": 0, "url": item.get("url"), "featured_snippet": True}

            return rank

        except requests.exceptions.RequestException as e:
            logger.error(f"DataForSEO request error: {e}")
            return None
        except Exception as e:
            logger.error(f"DataForSEO unexpected error: {e}")
            return None

    @classmethod
    def get_backlinks(cls, target_domain: str, limit: int = 100) -> list:
        headers = cls._get_headers()
        if not headers:
            return []

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
                                "first_seen": bl.get("first_seen"),
                            })
            return backlinks
        except Exception as e:
            logger.error(f"DataForSEO Backlinks Error: {e}")
            return []