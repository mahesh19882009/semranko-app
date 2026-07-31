import base64
import logging
import requests
from typing import Optional
from requests.auth import HTTPBasicAuth
from app.core.config import get_settings
from app.services.cache_service import get_cached, set_cached

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
        if not settings.effective_serp_login or not settings.effective_serp_key:
            return None
        cred = f"{settings.effective_serp_login}:{settings.effective_serp_key}"
        token = base64.b64encode(cred.encode()).decode()
        return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

    @classmethod
    def _find_domain_in_results(cls, organic_items, target_domain):
        target = target_domain.lower()
        for item in organic_items:
            item_domain = item.get("domain", "")
            item_url = item.get("url", "")
            if target in item_domain.lower() or target in (item_url or "").lower():
                return {"position": item.get("rank_group"), "url": item_url or f"https://{item_domain}"}
        return None

    @classmethod
    def get_rank(cls, keyword: str, domain: str, location: str = "India", device: str = "desktop") -> Optional[dict]:
        result = cls.get_rank_batch([{"keyword": keyword, "location": location, "device": device}], domain)
        return result.get(keyword)

    @classmethod
    def get_rank_batch(cls, keywords: list[dict], domain: str, location: str = "India", device: str = "desktop") -> dict:
        if not keywords:
            return {}

        serp_map = cls.get_serp_data_batch(keywords, location, device)
        results = {}
        for kw in keywords:
            keyword_text = kw.get("keyword", "")
            serp_data = serp_map.get(keyword_text)
            if not serp_data:
                continue

            rank = cls._find_domain_in_results(serp_data.get("organic_items", []), domain)
            if rank is None:
                for snippet_item in (serp_data.get("featured_snippet") or {}).get("items", []):
                    if domain.lower() in (snippet_item.get("domain") or "").lower():
                        rank = {"position": 0, "url": snippet_item.get("url"), "featured_snippet": True}
                        break

            if rank:
                results[keyword_text] = {
                    "position": rank.get("position"),
                    "url": rank.get("url"),
                    "featured_snippet": rank.get("featured_snippet", False),
                }
        return results

    @classmethod
    def get_keyword_data(cls, seed_keyword: str, location: str = "India", force_refresh: bool = False) -> Optional[dict]:
        if not force_refresh:
            cached = get_cached("keyword_research", (seed_keyword, location))
            if cached:
                return cached

        result = cls._fetch_keyword_data_batch([seed_keyword], location)
        if not result:
            return None
        return result.get(seed_keyword)

    @classmethod
    def get_keyword_data_batch(cls, keywords: list[str], location: str = "India", force_refresh: bool = False) -> dict:
        if not keywords:
            return {}

        if not force_refresh:
            results = {}
            missing = []
            for kw in keywords:
                cached = get_cached("keyword_research", (kw, location))
                if cached:
                    results[kw] = cached
                else:
                    missing.append(kw)
            if not missing:
                return results
            batch_result = cls._fetch_keyword_data_batch(missing, location) or {}
            results.update(batch_result)
            return results

        return cls._fetch_keyword_data_batch(keywords, location) or {}

    @classmethod
    def _fetch_keyword_data_batch(cls, keywords: list[str], location: str = "India") -> dict:
        if not settings.effective_serp_login or not settings.effective_serp_key:
            return {}

        if not keywords:
            return {}

        results = {}

        payload = [
            {
                "keywords": keywords,
                "location_name": location,
                "language_name": "English",
            }
        ]

        try:
            response = requests.post(
                f"{cls.BASE_URL}/dataforseo_labs/google/keyword_overview/live",
                auth=HTTPBasicAuth(settings.effective_serp_login or "", settings.effective_serp_key or ""),
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            if response.status_code != 200:
                logger.error(f"DataForSEO HTTP error for batch: {response.status_code} body={response.text[:500]}")
                return results

            data = response.json() or {}
            tasks = data.get("tasks") or []
            if data.get("status_code") != 20000:
                logger.error(f"DataForSEO API error for batch: {data.get('status_code')} msg={data.get('status_message')}")
                return results

            for task in tasks:
                task_result = (task or {}).get("result") or []
                for result_item in task_result or []:
                    if not result_item:
                        continue
                    items = result_item.get("items") or []
                    for item in items or []:
                        if not item:
                            continue
                        keyword_text = item.get("keyword")
                        if keyword_text:
                            keyword_info = item.get("keyword_info") or {}
                            keyword_properties = item.get("keyword_properties") or {}
                            search_intent_info = item.get("search_intent_info") or {}
                            avg_backlinks_info = item.get("avg_backlinks_info") or {}
                            serp_info = item.get("serp_info") or {}
                            results[keyword_text] = {
                                "seed": keyword_text,
                                "volume": keyword_info.get("search_volume"),
                                "difficulty": keyword_properties.get("keyword_difficulty"),
                                "cpc": keyword_info.get("cpc"),
                                "competition": keyword_info.get("competition"),
                                "intent": cls._normalize_intent(search_intent_info.get("main_intent")),
                                "backlinks": avg_backlinks_info.get("backlinks"),
                                "referring_domains": avg_backlinks_info.get("referring_domains"),
                                "serp_features": serp_info.get("serp_item_types") or [],
                                "search_volume_trend": keyword_info.get("search_volume_trend") or {},
                            }
        except Exception as e:
            logger.error(f"DataForSEO keyword error for batch: {e}")

        if not results:
            logger.warning("DataForSEO returned empty results for batch")
        return results

    @classmethod
    def get_competitor_keywords(cls, domain: str, location: str = "India", limit: int = 100) -> list:
        if not settings.effective_serp_login or not settings.effective_serp_key:
            return []

        location_code = LOCATION_MAP.get(location, 2356)
        payload = [{
            "target": domain,
            "location_code": location_code,
            "language_code": "en",
            "limit": limit,
        }]

        try:
            response = requests.post(
                f"{cls.BASE_URL}/keywords_data/google/competitor_site",
                auth=HTTPBasicAuth(settings.effective_serp_login or "", settings.effective_serp_key or ""),
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            if response.status_code != 200:
                return []

            data = response.json()
            if data.get("status_code") != 20000:
                return []

            results = []
            for task in data.get("tasks", []):
                for item in task.get("result", [{}])[0].get("items", []):
                    results.append({
                        "keyword": item.get("keyword"),
                        "position": item.get("position"),
                        "url": item.get("url"),
                        "volume": item.get("search_volume"),
                        "difficulty": item.get("keyword_difficulty"),
                    })
            return results
        except Exception as e:
            logger.error(f"DataForSEO competitor keywords error: {e}")
            return []

    @classmethod
    def get_serp_data_batch(cls, keywords: list[dict], location: str = "India", device: str = "desktop", result_type: str = "regular") -> dict:
        if not keywords:
            return {}

        results = {}
        missing = []

        for kw in keywords:
            keyword_text = kw.get("keyword", "")
            cache_key = ("serp", keyword_text, location, device)
            cached = get_cached("serp", cache_key)
            if cached is not None:
                results[keyword_text] = cached
            else:
                missing.append(kw)

        if not missing:
            return results

        location_code = LOCATION_MAP.get(location, 2356)
        se_type = DEVICE_MAP.get(device, "desktop")
        pingback_url = settings.PINGBACK_URL
        payload = [
            {
                "keyword": kw.get("keyword", ""),
                "location_code": location_code,
                "language_code": "en",
                "depth": 100,
                "se_type": se_type,
                **({"pingback_url": pingback_url} if pingback_url else {}),
            }
            for kw in missing
        ]

        import time

        try:
            response = requests.post(
                f"{cls.BASE_URL}/serp/google/organic/task_post",
                auth=HTTPBasicAuth(settings.effective_serp_login or "", settings.effective_serp_key or ""),
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            if response.status_code != 200:
                logger.error(f"DataForSEO batch task_post HTTP error: {response.status_code} body={response.text[:500]}")
                return results

            task_response = response.json()
            if task_response.get("status_code") != 20000:
                logger.error(f"DataForSEO batch task_post failed: {task_response}")
                return results

            tasks = task_response.get("tasks", [])
            if not tasks:
                logger.error(f"DataForSEO batch task_post returned no tasks: {task_response}")
                return results

            task_id = tasks[0].get("id")
            if not task_id:
                logger.error(f"DataForSEO batch task_post returned task without id: {tasks[0]}")
                return results

            logger.info(f"DataForSEO SERP task created: task_id={task_id} keywords={len(missing)} result_type={result_type}")

            result_data = None
            for attempt in range(60):
                result_response = requests.get(
                    f"{cls.BASE_URL}/serp/google/organic/task_get/{result_type}/{task_id}",
                    auth=HTTPBasicAuth(settings.effective_serp_login or "", settings.effective_serp_key or ""),
                    timeout=60,
                )
                if result_response.status_code == 200:
                    result_data = result_response.json()
                    status_code = result_data.get("status_code")
                    if status_code != 20000:
                        logger.warning(f"DataForSEO task_get attempt {attempt+1}/60: status_code={status_code} msg={result_data.get('status_message')} task_id={task_id}")
                    else:
                        task_items = result_data.get("tasks", [])
                        if task_items and task_items[0].get("status_code") == 20000 and task_items[0].get("result"):
                            logger.info(f"DataForSEO task_get succeeded on attempt {attempt+1}: task_id={task_id}")
                            break
                        task_status = task_items[0].get("status_code") if task_items else None
                        task_msg = task_items[0].get("status_message") if task_items else "no tasks"
                        if attempt % 12 == 0:
                            logger.info(f"DataForSEO task_get attempt {attempt+1}/60: task_status={task_status} msg={task_msg} task_id={task_id}")
                else:
                    logger.warning(f"DataForSEO task_get attempt {attempt+1}/60: HTTP {result_response.status_code} body={result_response.text[:200]} task_id={task_id}")
                if attempt < 59:
                    time.sleep(5)

            if not result_data or result_data.get("status_code") != 20000:
                logger.error(f"DataForSEO batch task_get failed after retries: task_id={task_id} last_status={result_data.get('status_code') if result_data else 'no_response'}")
                return results

            result_tasks = result_data.get("tasks", [])
            if not result_tasks:
                return results

            for task_result in result_tasks:
                serp_result = (task_result.get("result") or [{}])[0]
                keyword_text = serp_result.get("keyword", "")
                if not keyword_text:
                    continue

                items = serp_result.get("items", [])
                item_groups = serp_result.get("item_groups", [])

                organic_items = [item for item in items if item.get("type") == "organic"]

                featured_snippet = None
                paa_items = []
                ai_overview = None
                ai_answer = None
                cited_domains = {}

                for group in item_groups:
                    group_type = group.get("type")
                    if group_type == "featured_snippet":
                        snippet_items = group.get("items", [])
                        if snippet_items:
                            featured_snippet = snippet_items[0]
                    elif group_type == "people_also_ask":
                        paa_items = group.get("items", [])
                    elif group_type == "ai_overview":
                        ai_overview_items = group.get("items", [])
                        if ai_overview_items:
                            ai_overview = ai_overview_items[0]
                            for ref in ai_overview_items[0].get("references", []):
                                domain = ref.get("domain") or ref.get("source_domain")
                                if domain:
                                    cited_domains[domain] = cited_domains.get(domain, 0) + 1
                    elif group_type == "ai_answer":
                        ai_answer_items = group.get("items", [])
                        if ai_answer_items:
                            ai_answer = ai_answer_items[0]

                parsed = {
                    "organic_items": organic_items,
                    "featured_snippet": featured_snippet,
                    "people_also_ask": paa_items,
                    "ai_overview": ai_overview,
                    "ai_answer": ai_answer,
                    "cited_domains": cited_domains,
                    "items": items,
                }
                results[keyword_text] = parsed
                set_cached("serp", ("serp", keyword_text, location, device), parsed, ttl_seconds=3600)

            return results
        except Exception as e:
            logger.error(f"DataForSEO batch SERP error: {e}")
            return results

    @classmethod
    def _retrieve_task_result(cls, task_id: str, result_type: str = "regular") -> Optional[dict]:
        """Retrieve a single task result via task_get (used by webhook callback)."""
        try:
            response = requests.get(
                f"{cls.BASE_URL}/serp/google/organic/task_get/{result_type}/{task_id}",
                auth=HTTPBasicAuth(settings.effective_serp_login or "", settings.effective_serp_key or ""),
                timeout=60,
            )
            if response.status_code != 200:
                logger.error(f"DataForSEO task_get HTTP error: {response.status_code} task_id={task_id}")
                return None

            data = response.json()
            if data.get("status_code") != 20000:
                logger.warning(f"DataForSEO task_get failed: {data.get('status_message')} task_id={task_id}")
                return None

            tasks = data.get("tasks", [])
            if not tasks:
                return None

            task = tasks[0]
            if task.get("status_code") != 20000 or not task.get("result"):
                logger.warning(f"DataForSEO task not ready: status={task.get('status_message')} task_id={task_id}")
                return None

            return (task.get("result") or [{}])[0]
        except Exception as e:
            logger.error(f"DataForSEO task_get error: {e} task_id={task_id}")
            return None

    @classmethod
    def _parse_serp_result(cls, serp_result: dict) -> dict:
        """Parse a single SERP result into the standard format for caching."""
        keyword_text = serp_result.get("keyword", "")
        if not keyword_text:
            return {}

        items = serp_result.get("items", [])
        item_groups = serp_result.get("item_groups", [])

        organic_items = [item for item in items if item.get("type") == "organic"]

        featured_snippet = None
        paa_items = []
        ai_overview = None
        ai_answer = None
        cited_domains = {}

        for group in item_groups:
            group_type = group.get("type")
            if group_type == "featured_snippet":
                snippet_items = group.get("items", [])
                if snippet_items:
                    featured_snippet = snippet_items[0]
            elif group_type == "people_also_ask":
                paa_items = group.get("items", [])
            elif group_type == "ai_overview":
                ai_overview_items = group.get("items", [])
                if ai_overview_items:
                    ai_overview = ai_overview_items[0]
                    for ref in ai_overview_items[0].get("references", []):
                        domain = ref.get("domain") or ref.get("source_domain")
                        if domain:
                            cited_domains[domain] = cited_domains.get(domain, 0) + 1
            elif group_type == "ai_answer":
                ai_answer_items = group.get("items", [])
                if ai_answer_items:
                    ai_answer = ai_answer_items[0]

        return {
            keyword_text: {
                "organic_items": organic_items,
                "featured_snippet": featured_snippet,
                "people_also_ask": paa_items,
                "ai_overview": ai_overview,
                "ai_answer": ai_answer,
                "cited_domains": cited_domains,
                "items": items,
            }
        }

    @classmethod
    def get_serp_data(cls, keyword: str, location: str = "India", device: str = "desktop") -> Optional[dict]:
        return cls.get_serp_data_batch([{"keyword": keyword, "location": location, "device": device}], location, device).get(keyword)

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

    @staticmethod
    def _normalize_intent(raw_intent) -> Optional[str]:
        if not raw_intent:
            return None
        if isinstance(raw_intent, list):
            return raw_intent[0].get("name", "").lower() if raw_intent else None
        if isinstance(raw_intent, str):
            return raw_intent.lower()
        return None
