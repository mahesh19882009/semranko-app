import base64
import json
import logging
import math
import time
from typing import Optional
from requests.auth import HTTPBasicAuth

import requests
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
                return {
                    "position": item.get("rank_absolute") or item.get("rank_group"),
                    "url": item_url or f"https://{item_domain}",
                }
        return None

    @classmethod
    def get_rank(cls, keyword: str, domain: str, location: str = "India", device: str = "desktop") -> Optional[dict]:
        result = cls.get_rank_batch([{"keyword": keyword, "location": location, "device": device}], domain)
        return result.get(keyword)

    @classmethod
    def get_rank_batch(cls, keywords: list[dict], domain: str, location: str = "India", device: str = "desktop", aio_keyword_texts: set | None = None) -> dict:
        if not keywords:
            return {}

        serp_map = cls.get_serp_data_batch(keywords, location, device, aio_keyword_texts=aio_keyword_texts)
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
        if not keywords:
            return {}

        location_code = LOCATION_MAP.get(location, 2840)
        url = f"{cls.BASE_URL}/dataforseo_labs/google/keyword_overview/live"
        payload = [{
            "keywords": keywords,
            "location_code": location_code,
            "language_code": "en",
        }]

        try:
            response = requests.post(url, json=payload, auth=HTTPBasicAuth(settings.effective_serp_login, settings.effective_serp_key), timeout=60)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("DataForSEO keyword_overview request failed: %s", exc)
            return {}

        results = {}
        tasks = data.get("tasks", []) or []
        for task in tasks:
            items = (task.get("result") or {}).get("items", []) or []
            for item in items:
                kw = item.get("keyword")
                if not kw:
                    continue
                kp = item.get("keyword_properties", {}) or {}
                ki = item.get("keyword_info", {}) or {}
                abi = item.get("avg_backlinks_info", {}) or {}
                results[kw] = {
                    "volume": ki.get("search_volume"),
                    "difficulty": kp.get("keyword_difficulty"),
                    "cpc": ki.get("cpc"),
                    "competition": ki.get("competition"),
                    "backlinks": abi.get("backlinks"),
                    "referring_domains": abi.get("referring_domains"),
                    "intent": kp.get("search_intent"),
                }
        return results

    @classmethod
    def get_keyword_metrics(cls, db, user_id: str, keywords: list[dict]) -> dict:
        from app.services.keyword_cache_service import query_cached_keyword

        if not keywords:
            return {"results": [], "credits_charged": 0, "cached_count": 0, "user_cache_hits": 0}

        cached_results = []
        cached_count = 0

        for kw in keywords:
            keyword_text = kw.get("keyword", "")
            location = kw.get("location", "India")
            cached = query_cached_keyword(db, keyword_text, location)
            if cached:
                cached_results.append(cached)
                cached_count += 1

        return {
            "results": cached_results,
            "credits_charged": 0,
            "cached_count": cached_count,
            "user_cache_hits": cached_count,
        }

    @classmethod
    def bulk_keyword_lookup(cls, db, user_id: str, keywords: list[dict]) -> dict:
        from app.services.keyword_cache_service import query_cached_keyword

        if not keywords:
            return {"results": [], "credits_charged": 0, "cached_count": 0, "missing_count": 0}

        cached_items = []
        cached_count = 0
        missing = []

        for kw in keywords:
            keyword_text = kw.get("keyword", "")
            location = kw.get("location", "India")
            cached = query_cached_keyword(db, keyword_text, location)
            if cached:
                cached_items.append(cached)
                cached_count += 1
            else:
                missing.append(kw)

        missing_count = len(missing)
        credits_charged = 0

        if missing:
            keyword_texts = [kw.get("keyword", "") for kw in missing]
            api_results = cls._fetch_keyword_data_batch(keyword_texts, missing[0].get("location", "India") if missing else "India")
            for kw in missing:
                keyword_text = kw.get("keyword", "")
                data = api_results.get(keyword_text)
                if data:
                    credits_charged += 1
                    cached_items.append({
                        "keyword": keyword_text,
                        "location": kw.get("location", "India"),
                        **data,
                    })

        return {
            "results": cached_items,
            "credits_charged": credits_charged,
            "cached_count": cached_count,
            "missing_count": missing_count,
        }

    @classmethod
    def get_keyword_ideas(cls, db, user_id: str, seed_keyword: str, location: str = "India") -> dict:
        from app.services.keyword_cache_service import query_cached_keyword

        cached = query_cached_keyword(db, seed_keyword, location)
        if cached:
            return {
                "seed": seed_keyword,
                "ideas": [cached],
                "credits_charged": 0,
            }

        ideas = cls.get_keyword_ideas_api(seed_keyword, location)
        return {
            "seed": seed_keyword,
            "ideas": ideas,
            "credits_charged": len(ideas),
        }

    @classmethod
    def get_keyword_ideas_api(cls, seed_keyword: str, location: str = "India", limit: int = 50) -> list:
        location_code = LOCATION_MAP.get(location, 2840)
        url = f"{cls.BASE_URL}/dataforseo_labs/google/keyword_ideas/live"
        payload = [{
            "keyword": seed_keyword,
            "location_code": location_code,
            "language_code": "en",
            "limit": min(limit, 1000),
        }]

        try:
            response = requests.post(url, json=payload, auth=HTTPBasicAuth(settings.effective_serp_login, settings.effective_serp_key), timeout=60)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("DataForSEO keyword_ideas request failed: %s", exc)
            return []

        results = []
        tasks = data.get("tasks", []) or []
        for task in tasks:
            items = (task.get("result") or {}).get("items", []) or []
            for item in items:
                results.append({
                    "keyword": item.get("keyword"),
                    "search_volume": item.get("search_volume"),
                    "difficulty": item.get("keyword_difficulty"),
                    "cpc": item.get("cpc"),
                    "intent": item.get("search_intent"),
                })
        return results

    @classmethod
    def get_competitor_keywords_cached(cls, db, user_id: str, domain: str, location: str = "India", limit: int = 100) -> dict:
        from app.services.competitor_cache_service import query_cached_competitor

        cached = query_cached_competitor(db, domain, location)
        if cached:
            return {
                "domain": domain,
                "keywords": cached.get("keywords", []),
                "credits_charged": 0,
                "cached": True,
            }

        keywords = cls.get_competitor_keywords(domain, location, limit)
        return {
            "domain": domain,
            "keywords": keywords,
            "credits_charged": 1 if keywords else 0,
            "cached": False,
        }

    @classmethod
    def get_competitor_keywords(cls, domain: str, location: str = "India", limit: int = 100) -> list:
        location_code = LOCATION_MAP.get(location, 2840)
        url = f"{cls.BASE_URL}/dataforseo_labs/google/serp_competitors/live"
        payload = [{
            "target": domain,
            "location_code": location_code,
            "language_code": "en",
            "limit": min(limit, 100),
        }]

        try:
            response = requests.post(url, json=payload, auth=HTTPBasicAuth(settings.effective_serp_login, settings.effective_serp_key), timeout=60)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("DataForSEO serp_competitors request failed: %s", exc)
            return []

        results = []
        tasks = data.get("tasks", []) or []
        for task in tasks:
            task_status = task.get("status_code")
            if task_status and task_status != 20000:
                logger.warning("DataForSEO serp_competitors task error %s: %s", task_status, task.get("status_message"))
                continue

            items = (task.get("result") or {}).get("items", []) or []
            for item in items:
                if item.get("domain") and item.get("keyword"):
                    results.append({
                        "domain": item.get("domain"),
                        "keyword": item.get("keyword"),
                        "position": item.get("rank_group"),
                        "url": item.get("url"),
                    })
        return results[:limit]

    @classmethod
    def get_serp_data_batch(cls, keywords: list[dict], location: str = "India", device: str = "desktop", result_type: str = "regular", aio_keyword_texts: set | None = None) -> dict:
        if not keywords:
            return {}

        location_code = LOCATION_MAP.get(location, 2840)
        url = f"{cls.BASE_URL}/serp/google/organic/live/advanced"

        tasks = []
        for kw in keywords:
            task = {
                "keyword": kw.get("keyword", ""),
                "location_code": location_code,
                "language_code": "en",
                "device": DEVICE_MAP.get(device, "desktop"),
                "depth": 100,
            }
            if result_type == "async":
                task["pingback_url"] = None
            tasks.append(task)

        payload = [{"tasks": tasks}]

        try:
            response = requests.post(url, json=payload, auth=HTTPBasicAuth(settings.effective_serp_login, settings.effective_serp_key), timeout=120)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("DataForSEO serp/live/advanced request failed: %s", exc)
            return {}

        results = {}
        tasks_data = data.get("tasks", []) or []
        for task in tasks_data:
            keyword_text = (task.get("data") or {}).get("keyword", "")
            if not keyword_text:
                continue

            serp_entry = {
                "keyword": keyword_text,
                "location": location,
                "device": device,
                "items": [],
                "organic_items": [],
                "featured_snippet": None,
                "people_also_ask": [],
                "ai_overview": None,
                "ai_answer": None,
                "cited_domains": {},
            }

            result_blocks = task.get("result", []) or []
            if isinstance(result_blocks, list) and result_blocks:
                first_block = result_blocks[0]
                serp_entry["items"] = first_block.get("items", []) or []
                serp_entry["organic_items"] = [i for i in serp_entry["items"] if i.get("type") == "organic"]

                # Check items directly for AIO data (DataForSEO may put AIO in items array)
                for item in serp_entry["items"]:
                    item_type = item.get("type", "")
                    if item_type == "ai_overview" and not serp_entry["ai_overview"]:
                        serp_entry["ai_overview"] = item
                        references = item.get("ai_overview_reference", []) or item.get("references", []) or []
                        for ref in references:
                            d = ref.get("domain") or ref.get("source_domain") or ref.get("url")
                            if d:
                                serp_entry["cited_domains"][d] = serp_entry["cited_domains"].get(d, 0) + 1
                    elif item_type == "ai_answer" and not serp_entry["ai_answer"]:
                        serp_entry["ai_answer"] = item

                # Also check item_groups for AIO data
                item_groups = first_block.get("item_groups", []) or []
                for group in item_groups:
                    group_type = group.get("type")
                    group_items = group.get("items", []) or []
                    if group_type == "featured_snippet" and group_items and not serp_entry["featured_snippet"]:
                        serp_entry["featured_snippet"] = group_items[0]
                    elif group_type == "people_also_ask" and not serp_entry["people_also_ask"]:
                        serp_entry["people_also_ask"] = group_items
                    elif group_type == "ai_overview" and group_items and not serp_entry["ai_overview"]:
                        serp_entry["ai_overview"] = group_items[0]
                        for ref in group_items[0].get("references", []):
                            d = ref.get("domain") or ref.get("source_domain")
                            if d:
                                serp_entry["cited_domains"][d] = serp_entry["cited_domains"].get(d, 0) + 1
                    elif group_type == "ai_answer" and group_items and not serp_entry["ai_answer"]:
                        serp_entry["ai_answer"] = group_items[0]

            if aio_keyword_texts and keyword_text in aio_keyword_texts:
                ai_items = [i for i in serp_entry["items"] if i.get("type") == "ai_overview"]
                if ai_items:
                    serp_entry["ai_overview"] = ai_items[0]

            results[keyword_text] = serp_entry

        return results

    @classmethod
    def _retrieve_task_result(cls, task_id: str, result_type: str = "regular") -> Optional[dict]:
        url = f"{cls.BASE_URL}/serp/google/organic/task_get/advanced/{task_id}"
        try:
            response = requests.get(url, auth=HTTPBasicAuth(settings.effective_serp_login, settings.effective_serp_key), timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.error("DataForSEO task_get failed: %s", exc)
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
        cache_key = ("serp", keyword, location, device)
        cached = get_cached("serp", cache_key)
        return cached

    @classmethod
    def get_backlinks(cls, target_domain: str, limit: int = 100) -> list:
        url = f"{cls.BASE_URL}/backlinks/summary/live"
        payload = [{
            "target": target_domain,
            "limit": min(limit, 1000),
        }]

        try:
            response = requests.post(url, json=payload, auth=HTTPBasicAuth(settings.effective_serp_login, settings.effective_serp_key), timeout=60)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("DataForSEO backlinks request failed: %s", exc)
            return []

        results = []
        tasks = data.get("tasks", []) or []
        for task in tasks:
            items = (task.get("result") or {}).get("items", []) or []
            for item in items:
                results.append({
                    "source_url": item.get("source_url"),
                    "source_title": item.get("source_title"),
                    "domain_rank": item.get("domain_rank"),
                    "page_rank": item.get("page_rank"),
                })
        return results[:limit]

    @classmethod
    def get_domain_rank_overview(cls, domain: str, location: str = "India") -> Optional[dict]:
        location_code = LOCATION_MAP.get(location, 2840)
        url = f"{cls.BASE_URL}/dataforseo_labs/google/domain_rank_overview/live"
        payload = [{
            "target": domain,
            "location_code": location_code,
            "language_code": "en",
        }]

        try:
            response = requests.post(url, json=payload, auth=HTTPBasicAuth(settings.effective_serp_login, settings.effective_serp_key), timeout=60)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("DataForSEO domain_rank_overview request failed: %s", exc)
            return None

        tasks = data.get("tasks", []) or []
        for task in tasks:
            items = (task.get("result") or {}).get("items", []) or []
            if items:
                return items[0]
        return None

    @classmethod
    def get_bulk_traffic_estimation(cls, domains: list[str], location: str = "India") -> list:
        if not domains:
            return []

        location_code = LOCATION_MAP.get(location, 2840)
        url = f"{cls.BASE_URL}/dataforseo_labs/google/bulk_traffic_estimation/live"
        payload = [{
            "targets": domains,
            "location_code": location_code,
            "language_code": "en",
        }]

        try:
            response = requests.post(url, json=payload, auth=HTTPBasicAuth(settings.effective_serp_login, settings.effective_serp_key), timeout=60)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("DataForSEO bulk_traffic_estimation request failed: %s", exc)
            return []

        results = []
        tasks = data.get("tasks", []) or []
        for task in tasks:
            items = (task.get("result") or {}).get("items", []) or []
            results.extend(items)
        return results

    @classmethod
    def get_keyword_suggestions(cls, seed_keyword: str, location: str = "India", limit: int = 100) -> list:
        location_code = LOCATION_MAP.get(location, 2840)
        url = f"{cls.BASE_URL}/dataforseo_labs/google/keyword_suggestions/live"
        payload = [{
            "keyword": seed_keyword,
            "location_code": location_code,
            "language_code": "en",
            "limit": min(limit, 1000),
        }]

        try:
            response = requests.post(url, json=payload, auth=HTTPBasicAuth(settings.effective_serp_login, settings.effective_serp_key), timeout=60)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("DataForSEO keyword_suggestions request failed: %s", exc)
            return []

        results = []
        tasks = data.get("tasks", []) or []
        for task in tasks:
            items = (task.get("result") or {}).get("items", []) or []
            for item in items:
                results.append({
                    "keyword": item.get("keyword"),
                    "search_volume": item.get("search_volume"),
                    "difficulty": item.get("keyword_difficulty"),
                    "cpc": item.get("cpc"),
                })
        return results[:limit]

    @classmethod
    def get_keywords_for_keywords(cls, keywords: list[str], location: str = "India", limit: int = 100) -> list:
        if not keywords:
            return []

        location_code = LOCATION_MAP.get(location, 2840)
        url = f"{cls.BASE_URL}/dataforseo_labs/google/keywords_for_keywords/live"
        payload = [{
            "keywords": keywords[:10],
            "location_code": location_code,
            "language_code": "en",
            "limit": min(limit, 1000),
        }]

        try:
            response = requests.post(url, json=payload, auth=HTTPBasicAuth(settings.effective_serp_login, settings.effective_serp_key), timeout=60)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("DataForSEO keywords_for_keywords request failed: %s", exc)
            return []

        results = []
        tasks = data.get("tasks", []) or []
        for task in tasks:
            items = (task.get("result") or {}).get("items", []) or []
            for item in items:
                results.append({
                    "keyword": item.get("keyword"),
                    "search_volume": item.get("search_volume"),
                    "difficulty": item.get("keyword_difficulty"),
                    "cpc": item.get("cpc"),
                    "intent": item.get("search_intent"),
                })
        return results[:limit]

    @staticmethod
    def _normalize_intent(raw_intent) -> Optional[str]:
        if not raw_intent:
            return None
        if isinstance(raw_intent, list):
            return raw_intent[0].get("name", "").lower() if raw_intent else None
        if isinstance(raw_intent, str):
            return raw_intent.lower()
        return None
