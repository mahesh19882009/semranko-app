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
                return {"position": item.get("rank_group"), "url": item_url or f"https://{item_domain}"}
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
        return {}

    @classmethod
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

        for kw in keywords:
            keyword_text = kw.get("keyword", "")
            location = kw.get("location", "India")
            cached = query_cached_keyword(db, keyword_text, location)
            if cached:
                cached_items.append(cached)
                cached_count += 1

        return {
            "results": cached_items,
            "credits_charged": 0,
            "cached_count": cached_count,
            "missing_count": len(keywords) - cached_count,
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
        return {
            "seed": seed_keyword,
            "ideas": [],
            "credits_charged": 0,
        }

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
        return {
            "domain": domain,
            "keywords": [],
            "credits_charged": 0,
            "cached": False,
        }

    @classmethod
    def get_competitor_keywords(cls, domain: str, location: str = "India", limit: int = 100) -> list:
        return []

    @classmethod
    def get_serp_data_batch(cls, keywords: list[dict], location: str = "India", device: str = "desktop", result_type: str = "regular", aio_keyword_texts: set | None = None) -> dict:
        if not keywords:
            return {}

        results = {}
        for kw in keywords:
            keyword_text = kw.get("keyword", "")
            cache_key = ("serp", keyword_text, location, device)
            cached = get_cached("serp", cache_key)
            if cached is not None:
                results[keyword_text] = cached
        return results

    @classmethod
    def _retrieve_task_result(cls, task_id: str, result_type: str = "regular") -> Optional[dict]:
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
