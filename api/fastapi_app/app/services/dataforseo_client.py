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
    def get_keyword_metrics(cls, db, user_id: str, keywords: list[dict]) -> dict:
        from app.services.keyword_cache_service import query_cached_keyword, save_cached_keyword
        from app.services.credit_service import deduct_credits, refund_credits
        from app.services.user_cache_service import check_user_cache_unlock, create_user_cache_unlock
        from app.services.team_service import get_team_owner_id

        if not keywords:
            logger.info("get_keyword_metrics: empty keywords list")
            return {"results": [], "credits_charged": 0, "cached_count": 0}

        keyword_count = len(keywords)
        is_single = keyword_count == 1
        
        owner_id = get_team_owner_id(db, user_id)
        logger.info(f"get_keyword_metrics: user={user_id} owner={owner_id} count={keyword_count} is_single={is_single}")

        cached_results = []
        missing = []
        cached_count = 0
        user_cache_hits = 0

        for kw in keywords:
            keyword_text = kw.get("keyword", "")
            location = kw.get("location", "India")
            
            if check_user_cache_unlock(db, owner_id, keyword_text):
                global_cached = query_cached_keyword(db, keyword_text, location)
                if global_cached:
                    cached_results.append(global_cached)
                    user_cache_hits += 1
                    cached_count += 1
                    logger.info(f"get_keyword_metrics: user_cache_hit + global_cache_hit for '{keyword_text}'")
                else:
                    missing.append({"keyword": keyword_text, "location": location, "already_paid": True})
                    logger.info(f"get_keyword_metrics: user_cache_hit but global_cache_miss for '{keyword_text}'")
            else:
                missing.append({"keyword": keyword_text, "location": location, "already_paid": False})
                logger.info(f"get_keyword_metrics: user_cache_miss for '{keyword_text}'")

        if not missing:
            logger.info(f"get_keyword_metrics: all cached, returning {len(cached_results)} results")
            return {
                "results": cached_results,
                "credits_charged": 0,
                "cached_count": cached_count,
                "user_cache_hits": user_cache_hits,
            }

        already_paid_keywords = [kw for kw in missing if kw.get("already_paid")]
        need_charge_keywords = [kw for kw in missing if not kw.get("already_paid")]
        logger.info(f"get_keyword_metrics: already_paid={len(already_paid_keywords)} need_charge={len(need_charge_keywords)}")

        # STEP B: Charge only for users who haven't paid
        if need_charge_keywords:
            credits_to_charge = 15 * len(need_charge_keywords)
            logger.info(f"get_keyword_metrics: deducting {credits_to_charge} credits from owner={owner_id} for {len(need_charge_keywords)} keywords")
            deduct_credits(db, owner_id, credits_to_charge, "charge", f"Keyword metrics: {len(need_charge_keywords)} keyword(s)")
            
            for kw in need_charge_keywords:
                keyword_text = kw.get("keyword", "")
                create_user_cache_unlock(db, owner_id, keyword_text)
                logger.info(f"get_keyword_metrics: created unlock for '{keyword_text}'")

        all_missing = already_paid_keywords + need_charge_keywords
        logger.info(f"get_keyword_metrics: all_missing count={len(all_missing)}")

        raw_results = {}
        try:
            if is_single:
                kw = all_missing[0]
                keyword_text = kw.get("keyword", "")
                location = kw.get("location", "India")
                
                global_cached = query_cached_keyword(db, keyword_text, location)
                if global_cached:
                    cached_results.append(global_cached)
                    total_credits = credits_to_charge if need_charge_keywords else 0
                    logger.info(f"get_keyword_metrics: single keyword global_cache_hit for '{keyword_text}'")
                    return {
                        "results": cached_results,
                        "credits_charged": total_credits,
                        "cached_count": cached_count + 1,
                        "user_cache_hits": user_cache_hits,
                        "global_cache_hit": True,
                    }
                
                logger.info(f"get_keyword_metrics: single keyword global_cache_miss, calling DataForSEO for '{keyword_text}'")
                if not settings.effective_serp_login or not settings.effective_serp_key:
                    raise Exception("DataForSEO credentials are not configured")

                payload = [{
                    "keywords": [keyword_text],
                    "location_name": location,
                    "language_name": "English",
                }]
                response = requests.post(
                    f"{cls.BASE_URL}/dataforseo_labs/google/keyword_overview/live",
                    auth=HTTPBasicAuth(settings.effective_serp_login or "", settings.effective_serp_key or ""),
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=60,
                )
                logger.info(f"get_keyword_metrics: DataForSEO labs status={response.status_code} for '{keyword_text}' body={response.text[:500]}")
                if response.status_code != 200:
                    if response.status_code == 404:
                        logger.warning(f"DataForSEO 404 for keyword '{keyword_text}' - keyword may have no data")
                        raw_results[keyword_text] = {
                            "seed": keyword_text,
                            "volume": None,
                            "difficulty": None,
                            "cpc": None,
                            "competition": None,
                            "intent": None,
                            "backlinks": None,
                            "referring_domains": None,
                        }
                    else:
                        raise Exception(f"DataForSEO HTTP {response.status_code}: {response.text[:200]}")
                else:
                    data = response.json() or {}
                    if data.get("status_code") != 20000:
                        raise Exception(f"DataForSEO error: {data.get('status_message')}")

                    for task in data.get("tasks", []):
                        for result_item in task.get("result") or []:
                            for item in result_item.get("items") or []:
                                keyword_text = item.get("keyword")
                                if keyword_text:
                                    keyword_info = item.get("keyword_info") or {}
                                    keyword_properties = item.get("keyword_properties") or {}
                                    search_intent_info = item.get("search_intent_info") or {}
                                    avg_backlinks_info = item.get("avg_backlinks_info") or {}
                                    raw_results[keyword_text] = {
                                        "seed": keyword_text,
                                        "volume": keyword_info.get("search_volume"),
                                        "difficulty": keyword_properties.get("keyword_difficulty"),
                                        "cpc": keyword_info.get("cpc"),
                                        "competition": keyword_info.get("competition"),
                                        "intent": cls._normalize_intent(search_intent_info.get("main_intent")),
                                        "backlinks": avg_backlinks_info.get("backlinks"),
                                        "referring_domains": avg_backlinks_info.get("referring_domains"),
                                    }
            else:
                # STEP C: Check global cache for each missing keyword before burning API credits
                global_cache_hits = []
                need_api_call = []
                for kw in all_missing:
                    keyword_text = kw.get("keyword", "")
                    location = kw.get("location", "India")
                    global_cached = query_cached_keyword(db, keyword_text, location)
                    if global_cached:
                        global_cache_hits.append((kw, global_cached))
                        logger.info(f"get_keyword_metrics: batch global_cache_hit for '{keyword_text}'")
                    else:
                        need_api_call.append(kw)
                        logger.info(f"get_keyword_metrics: batch global_cache_miss for '{keyword_text}'")

                # Serve global cache hits instantly — zero DataForSEO cost
                for _, global_cached in global_cache_hits:
                    cached_results.append(global_cached)

                # STEP D: Only hit DataForSEO for keywords truly missing from global cache
                if need_api_call:
                    chunks = [need_api_call[i:i + 700] for i in range(0, len(need_api_call), 700)]
                    for chunk in chunks:
                        chunk_keywords = [kw.get("keyword", "") for kw in chunk]
                        payload = [{
                            "keywords": chunk_keywords,
                            "location_name": chunk[0].get("location", "India"),
                            "language_name": "English",
                        }]
                        logger.info(f"get_keyword_metrics: batch calling DataForSEO for {len(chunk_keywords)} keywords")
                        response = requests.post(
                            f"{cls.BASE_URL}/dataforseo_labs/google/keyword_overview/live",
                            auth=HTTPBasicAuth(settings.effective_serp_login or "", settings.effective_serp_key or ""),
                            json=payload,
                            headers={"Content-Type": "application/json"},
                            timeout=60,
                        )
                        logger.info(f"get_keyword_metrics: DataForSEO batch status={response.status_code}")
                        if response.status_code != 200:
                            raise Exception(f"DataForSEO HTTP {response.status_code}")

                        data = response.json() or {}
                        if data.get("status_code") != 20000:
                            raise Exception(f"DataForSEO error: {data.get('status_message')}")

                        for task in data.get("tasks", []):
                            for result_item in task.get("result") or []:
                                for item in result_item.get("items") or []:
                                    keyword_text = item.get("keyword")
                                    if keyword_text:
                                        keyword_info = item.get("keyword_info") or {}
                                        keyword_properties = item.get("keyword_properties") or {}
                                        search_intent_info = item.get("search_intent_info") or {}
                                        avg_backlinks_info = item.get("avg_backlinks_info") or {}
                                        raw_results[keyword_text] = {
                                            "seed": keyword_text,
                                            "volume": keyword_info.get("search_volume"),
                                            "difficulty": keyword_properties.get("keyword_difficulty"),
                                            "cpc": keyword_info.get("cpc"),
                                            "competition": keyword_info.get("competition"),
                                            "intent": cls._normalize_intent(search_intent_info.get("main_intent")),
                                            "backlinks": avg_backlinks_info.get("backlinks"),
                                            "referring_domains": avg_backlinks_info.get("referring_domains"),
                                        }
                else:
                    logger.info("get_keyword_metrics: batch all keywords found in global cache, skipping DataForSEO")

            # Persist API results to global cache and append to response
            for kw in all_missing:
                keyword_text = kw.get("keyword", "")
                location = kw.get("location", "India")
                data = raw_results.get(keyword_text)
                if data:
                    save_cached_keyword(db, keyword_text, location, data)
                    data["cached"] = False
                    cached_results.append(data)
                    logger.info(f"get_keyword_metrics: appended API result for '{keyword_text}'")
                else:
                    logger.info(f"get_keyword_metrics: no data for '{keyword_text}' in raw_results")

            total_credits = credits_to_charge if need_charge_keywords else 0
            logger.info(f"get_keyword_metrics: returning {len(cached_results)} results, charged={total_credits}")
            return {
                "results": cached_results,
                "credits_charged": total_credits,
                "cached_count": cached_count,
                "user_cache_hits": user_cache_hits,
            }

        except Exception as e:
            logger.error(f"DataForSEO keyword metrics error: {e}")
            raise

    @classmethod
    def bulk_keyword_lookup(cls, db, user_id: str, keywords: list[dict]) -> dict:
        from app.services.keyword_cache_service import query_cached_keyword, save_cached_keyword
        from app.services.credit_service import deduct_credits
        from app.services.team_service import get_team_owner_id

        if not keywords:
            return {"results": [], "credits_charged": 0, "cached_count": 0, "missing_count": 0}

        owner_id = get_team_owner_id(db, user_id)
        keyword_count = len(keywords)
        credits_to_charge = 15 * keyword_count

        deduct_credits(db, owner_id, credits_to_charge, "charge", f"Bulk keyword metrics: {keyword_count} keyword(s)")

        cached_items = []
        missing_items = []
        cached_count = 0

        for kw in keywords:
            keyword_text = kw.get("keyword", "")
            location = kw.get("location", "India")
            cached = query_cached_keyword(db, keyword_text, location)
            if cached:
                cached_items.append(cached)
                cached_count += 1
            else:
                missing_items.append({"keyword": keyword_text, "location": location})

        logger.info(f"bulk_keyword_lookup: total={keyword_count} cached={cached_count} missing={len(missing_items)}")

        live_results = []
        if missing_items:
            chunk_keywords = [kw["keyword"] for kw in missing_items]
            locations = [kw["location"] for kw in missing_items]
            unique_locations = list(set(locations))
            primary_location = unique_locations[0] if unique_locations else "India"

            payload = [{
                "keywords": chunk_keywords,
                "location_name": primary_location,
                "language_name": "English",
            }]

            try:
                response = requests.post(
                    f"{cls.BASE_URL}/dataforseo_labs/google/keyword_overview/live",
                    auth=HTTPBasicAuth(settings.effective_serp_login or "", settings.effective_serp_key or ""),
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=60,
                )
                if response.status_code == 200:
                    data = response.json() or {}
                    if data.get("status_code") == 20000:
                        for task in data.get("tasks", []):
                            for result_item in task.get("result") or []:
                                for item in result_item.get("items") or []:
                                    keyword_text = item.get("keyword")
                                    if keyword_text:
                                        keyword_info = item.get("keyword_info") or {}
                                        keyword_properties = item.get("keyword_properties") or {}
                                        search_intent_info = item.get("search_intent_info") or {}
                                        avg_backlinks_info = item.get("avg_backlinks_info") or {}
                                        result = {
                                            "seed": keyword_text,
                                            "volume": keyword_info.get("search_volume"),
                                            "difficulty": keyword_properties.get("keyword_difficulty"),
                                            "cpc": keyword_info.get("cpc"),
                                            "competition": keyword_info.get("competition"),
                                            "intent": cls._normalize_intent(search_intent_info.get("main_intent")),
                                            "backlinks": avg_backlinks_info.get("backlinks"),
                                            "referring_domains": avg_backlinks_info.get("referring_domains"),
                                        }
                                        save_cached_keyword(db, keyword_text, primary_location, result)
                                        result["cached"] = False
                                        live_results.append(result)
                    else:
                        logger.error(f"DataForSEO error: {data.get('status_message')}")
                else:
                    logger.error(f"DataForSEO HTTP {response.status_code}")
            except Exception as e:
                logger.error(f"DataForSEO bulk lookup error: {e}")
                raise

        stitched_results = cached_items + live_results
        return {
            "results": stitched_results,
            "credits_charged": credits_to_charge,
            "cached_count": cached_count,
            "missing_count": len(missing_items),
        }

    @classmethod
    def get_keyword_ideas(cls, db, user_id: str, seed_keyword: str, location: str = "India") -> dict:
        from app.services.keyword_cache_service import save_cached_keyword, query_cached_keyword
        from app.services.credit_service import deduct_credits, refund_credits
        from app.services.user_cache_service import check_user_cache_unlock, create_user_cache_unlock
        from app.services.team_service import get_team_owner_id

        owner_id = get_team_owner_id(db, user_id)
        
        # STEP A: Check if THIS USER has unlocked in last 30 days
        if check_user_cache_unlock(db, owner_id, seed_keyword):
            global_cached = query_cached_keyword(db, seed_keyword, location)
            if global_cached:
                return {
                    "seed": seed_keyword,
                    "ideas": [global_cached],
                    "credits_charged": 0,
                    "user_cache_hit": True,
                }

        # STEP B: User cache miss - ALWAYS charge (even if global cache exists)
        deduct_credits(db, user_id, 30, "charge", f"Keyword ideas: {seed_keyword}")
        create_user_cache_unlock(db, owner_id, seed_keyword)

        try:
            # STEP C: Check global cache (Profit Bridge - but AFTER charging user)
            global_cached = query_cached_keyword(db, seed_keyword, location)
            if global_cached:
                return {
                    "seed": seed_keyword,
                    "ideas": [global_cached],
                    "credits_charged": 30,
                    "global_cache_hit": True,
                }
            
            # STEP D: Global cache miss - call DataForSEO
            payload = [{
                "keyword": seed_keyword,
                "location_name": location,
                "language_name": "English",
                "limit": 50,
            }]
            response = requests.post(
                f"{cls.BASE_URL}/dataforseo_labs/google/keyword_ideas/live",
                auth=HTTPBasicAuth(settings.effective_serp_login or "", settings.effective_serp_key or ""),
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            if response.status_code != 200:
                raise Exception(f"DataForSEO HTTP {response.status_code}")

            data = response.json() or {}
            if data.get("status_code") != 20000:
                raise Exception(f"DataForSEO error: {data.get('status_message')}")

            ideas = []
            for task in data.get("tasks", []):
                for result_item in task.get("result") or []:
                    for item in result_item.get("items") or []:
                        keyword_text = item.get("keyword")
                        if keyword_text:
                            keyword_info = item.get("keyword_info") or {}
                            keyword_properties = item.get("keyword_properties") or {}
                            ideas.append({
                                "keyword": keyword_text,
                                "volume": keyword_info.get("search_volume"),
                                "difficulty": keyword_properties.get("keyword_difficulty"),
                                "cpc": keyword_info.get("cpc"),
                                "competition": keyword_info.get("competition"),
                            })
                            save_cached_keyword(db, keyword_text, location, {
                                "volume": keyword_info.get("search_volume"),
                                "difficulty": keyword_properties.get("keyword_difficulty"),
                                "cpc": keyword_info.get("cpc"),
                                "competition": keyword_info.get("competition"),
                            })

            return {
                "seed": seed_keyword,
                "ideas": ideas,
                "credits_charged": 30,
            }

        except Exception as e:
            logger.error(f"DataForSEO keyword ideas error: {e}")
            refund_credits(db, user_id, 30, f"Refund for failed keyword ideas: {seed_keyword}")
            raise

    @classmethod
    def get_competitor_keywords_cached(cls, db, user_id: str, domain: str, location: str = "India", limit: int = 100) -> dict:
        from app.services.competitor_cache_service import query_cached_competitor, save_cached_competitor
        from app.services.credit_service import deduct_credits, refund_credits
        from app.services.user_cache_service import check_user_cache_unlock, create_user_cache_unlock
        from app.services.team_service import get_team_owner_id

        owner_id = get_team_owner_id(db, user_id)
        
        # STEP A: Check if THIS USER has unlocked in last 30 days
        if check_user_cache_unlock(db, owner_id, domain):
            cached = query_cached_competitor(db, domain, location)
            if cached:
                return {
                    "domain": domain,
                    "keywords": cached.get("keywords", []),
                    "credits_charged": 0,
                    "cached": True,
                    "user_cache_hit": True,
                }

        # STEP B: User cache miss - ALWAYS charge (even if global cache exists)
        deduct_credits(db, user_id, 30, "charge", f"Competitor spy: {domain}")
        create_user_cache_unlock(db, owner_id, domain)

        try:
            # STEP C: Check global cache (Profit Bridge - but AFTER charging user)
            cached = query_cached_competitor(db, domain, location)
            if cached:
                return {
                    "domain": domain,
                    "keywords": cached.get("keywords", []),
                    "credits_charged": 30,
                    "cached": True,
                    "global_cache_hit": True,
                }
            
            # STEP D: Global cache miss - call DataForSEO
            location_code = LOCATION_MAP.get(location, 2356)
            payload = [{
                "target": domain,
                "location_code": location_code,
                "language_code": "en",
                "limit": limit,
                "filters": [
                    ["search_volume", ">=", 100],
                    ["rank", "<=", 20],
                ],
            }]

            response = requests.post(
                f"{cls.BASE_URL}/dataforseo_labs/google/ranked_keywords/live",
                auth=HTTPBasicAuth(settings.effective_serp_login or "", settings.effective_serp_key or ""),
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            if response.status_code != 200:
                raise Exception(f"DataForSEO HTTP {response.status_code}")

            data = response.json() or {}
            if data.get("status_code") != 20000:
                raise Exception(f"DataForSEO error: {data.get('status_message')}")

            keywords = []
            for task in data.get("tasks", []):
                for result_item in task.get("result") or []:
                    for item in result_item.get("items") or []:
                        keywords.append({
                            "keyword": item.get("keyword"),
                            "position": item.get("position"),
                            "url": item.get("url"),
                            "volume": item.get("search_volume"),
                            "difficulty": item.get("keyword_difficulty"),
                        })

            save_cached_competitor(db, domain, location, keywords)
            return {
                "domain": domain,
                "keywords": keywords,
                "credits_charged": 30,
                "cached": False,
            }

        except Exception as e:
            logger.error(f"DataForSEO competitor spy error: {e}")
            refund_credits(db, user_id, 30, f"Refund for failed competitor spy: {domain}")
            raise

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
    def get_serp_data_batch(cls, keywords: list[dict], location: str = "India", device: str = "desktop", result_type: str = "regular", aio_keyword_texts: set | None = None) -> dict:
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
                **({"ai_overview": True} if aio_keyword_texts and kw.get("keyword", "") in aio_keyword_texts else {}),
            }
            for kw in missing
        ]

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
