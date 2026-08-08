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
    "China": 2156,
    "Italy": 2380,
    "Spain": 2724,
    "Mexico": 2484,
    "South Korea": 2410,
    "Netherlands": 2450,
    "Saudi Arabia": 2682,
    "UAE": 2786,
    "Singapore": 2468,
    "Hong Kong": 2328,
    "New York": 2840,
    "London": 2826,
    "Mumbai": 2356,
    "Delhi": 2356,
    "Sydney": 2036,
    "Toronto": 2124,
    "Berlin": 2276,
    "Paris": 2250,
    "Tokyo": 2392,
    "Dubai": 2786,
    "Riyadh": 2682,
    "Seoul": 2410,
    "Madrid": 2724,
    "Barcelona": 2724,
    "Rome": 2380,
    "Amsterdam": 2450,
    "Bangkok": 2556,
    "Jakarta": 2330,
    "Cairo": 2180,
    "Istanbul": 2794,
    "Moscow": 2458,
    "São Paulo": 2076,
    "Buenos Aires": 2052,
    "Cape Town": 2720,
    "Nairobi": 2378,
    "Lagos": 2374,
    "Karachi": 2356,
    "Dhaka": 2150,
    "Kuala Lumpur": 2438,
    "Manila": 2464,
    "Hanoi": 2262,
    "Athens": 2206,
    "Lisbon": 2416,
    "Vienna": 2810,
    "Stockholm": 2754,
    "Oslo": 2462,
    "Helsinki": 2266,
    "Warsaw": 2620,
    "Prague": 2204,
    "Budapest": 2300,
    "Zurich": 2750,
    "Dublin": 2254,
    "Edinburgh": 2826,
    "Manchester": 2826,
    "Birmingham": 2826,
    "Leeds": 2826,
    "Glasgow": 2826,
    "Liverpool": 2826,
    "Newcastle": 2826,
    "Sheffield": 2826,
    "Bristol": 2826,
    "Leicester": 2826,
    "Cardiff": 2826,
    "Belfast": 2826,
    "Southampton": 2826,
    "Nottingham": 2826,
    "Brighton": 2826,
    "Cambridge": 2826,
    "Oxford": 2826,
    "York": 2826,
    "Bath": 2826,
    "Norwich": 2826,
    "Exeter": 2826,
    "Plymouth": 2826,
    "Swansea": 2826,
    "Aberdeen": 2826,
    "Dundee": 2826,
    "Inverness": 2826,
    "Bournemouth": 2826,
    "Reading": 2826,
    "Milton Keynes": 2826,
    "Luton": 2826,
    "Coventry": 2826,
    "Hull": 2826,
    "Stoke-on-Trent": 2826,
    "Derby": 2826,
    "Northampton": 2826,
    "Middlesbrough": 2826,
    "Sunderland": 2826,
    "Warrington": 2826,
    "Blackpool": 2826,
    "Peterborough": 2826,
    "Ipswich": 2826,
    "Colchester": 2826,
    "Chelmsford": 2826,
    "Maidstone": 2826,
    "Guildford": 2826,
    "Swindon": 2826,
    "Lancaster": 2826,
    "Preston": 2826,
    "Blackburn": 2826,
    "Bradford": 2826,
    "Huddersfield": 2826,
    "Wakefield": 2826,
    "Doncaster": 2826,
    "Rotherham": 2826,
    "Barnsley": 2826,
    "Lincoln": 2826,
    "Chesterfield": 2826,
    "Scunthorpe": 2826,
    "Grimsby": 2826,
    "Mansfield": 2826,
    "Loughborough": 2826,
    "Nuneaton": 2826,
    "Rugby": 2826,
    "Stratford-upon-Avon": 2826,
    "Worcester": 2826,
    "Hereford": 2826,
    "Shrewsbury": 2826,
    "Telford": 2826,
    "Stafford": 2826,
    "Lichfield": 2826,
    "Tamworth": 2826,
    "Burton upon Trent": 2826,
    "Uttoxeter": 2826,
    "Congleton": 2826,
    "Crewe": 2826,
    "Nantwich": 2826,
    "Chester": 2826,
    "Ellesmere Port": 2826,
    "Birkenhead": 2826,
    "Wallasey": 2826,
    "Southport": 2826,
    "Barrow-in-Furness": 2826,
    "Carlisle": 2826,
    "Penrith": 2826,
    "Workington": 2826,
    "Whitehaven": 2826,
    "Kendal": 2826,
    "Barrowford": 2826,
    "Burnley": 2826,
    "Accrington": 2826,
    "Clitheroe": 2826,
    "Skipton": 2826,
    "Ilkley": 2826,
    "Otley": 2826,
    "Castleford": 2826,
    "Pontefract": 2826,
    "Selby": 2826,
    "Goole": 2826,
    "Howden": 2826,
    "Beverley": 2826,
    "Bridlington": 2826,
    "Scarborough": 2826,
    "Whitby": 2826,
    "Redcar": 2826,
    "Stockton-on-Tees": 2826,
    "Darlington": 2826,
    "Durham": 2826,
    "Chester-le-Street": 2826,
    "Gateshead": 2826,
    "South Shields": 2826,
    "Tynemouth": 2826,
    "North Shields": 2826,
    "Cullercoats": 2826,
    "Whitley Bay": 2826,
    "Cramlington": 2826,
    "Morpeth": 2826,
    "Berwick-upon-Tweed": 2826,
    "Perth": 2826,
    "Kirkcaldy": 2826,
    "Glenrothes": 2826,
    "Dunfermline": 2826,
    "Motherwell": 2826,
    "Hamilton": 2826,
    "East Kilbride": 2826,
    "Cumbernauld": 2826,
    "Kilmarnock": 2826,
    "Irvine": 2826,
    "Greenock": 2826,
    "Paisley": 2826,
    "Dumfries": 2826,
    "Ayr": 2826,
    "Arbroath": 2826,
    "Montrose": 2826,
    "Forfar": 2826,
    "Brechin": 2826,
    "Stonehaven": 2826,
    "Inverurie": 2826,
    "Elgin": 2826,
    "Nairn": 2826,
    "Forres": 2826,
    "Keith": 2826,
    "Buckie": 2826,
    "Peterhead": 2826,
    "Fraserburgh": 2826,
    "Ellon": 2826,
    "Turriff": 2826,
    "New Delhi": 2356,
    "Faridabad": 2356,
    "Gurgaon": 2356,
    "Noida": 2356,
    "Chennai": 2356,
    "Bangalore": 2356,
    "Hyderabad": 2356,
    "Kolkata": 2356,
    "Ahmedabad": 2356,
    "Jaipur": 2356,
    "Pune": 2356,
    "Nagpur": 2356,
    "Thane": 2356,
    "Navi Mumbai": 2356,
    "Mysore": 2356,
    "Mangalore": 2356,
    "Coimbatore": 2356,
    "Madurai": 2356,
    "Salem": 2356,
    "Warangal": 2356,
    "Nizamabad": 2356,
    "Howrah": 2356,
    "Durgapur": 2356,
    "Surat": 2356,
    "Vadodara": 2356,
    "Rajkot": 2356,
    "Udaipur": 2356,
    "Kota": 2356,
    "Lucknow": 2356,
    "Kanpur": 2356,
    "Varanasi": 2356,
    "Ghaziabad": 2356,
    "Los Angeles": 2840,
    "San Francisco": 2840,
    "San Diego": 2840,
    "San Jose": 2840,
    "Buffalo": 2840,
    "Rochester": 2840,
    "Houston": 2840,
    "Austin": 2840,
    "Dallas": 2840,
    "San Antonio": 2840,
    "Orlando": 2840,
    "Tampa": 2840,
    "Aurora": 2840,
    "Naperville": 2840,
    "Vancouver": 2124,
    "Victoria": 2124,
    "Ottawa": 2124,
    "Mississauga": 2124,
    "Montreal": 2124,
    "Quebec City": 2124,
    "Calgary": 2124,
    "Edmonton": 2124,
    "Melbourne": 2036,
    "Brisbane": 2036,
    "Gold Coast": 2036,
    "Cairns": 2036,
    "Fremantle": 2036,
    "Munich": 2276,
    "Nuremberg": 2276,
    "Hamburg": 2276,
    "Versailles": 2250,
    "Nice": 2250,
    "Shibuya": 2392,
    "Kyoto": 2392,
    "Campinas": 2076,
    "Niterói": 2076,
    "Guangzhou": 2156,
    "Shenzhen": 2156,
    "Global": 2840,
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
    def _find_domain_in_results(cls, items, target_domain):
        target = target_domain.lower()
        for item in items:
            item_type = item.get("type", "")
            item_domain = item.get("domain", "")
            item_url = item.get("url", "")
            domain_match = target in (item_domain or "").lower() or target in (item_url or "").lower()

            if not domain_match:
                continue

            if item_type == "organic":
                return {
                    "position": item.get("rank_absolute") or item.get("rank_group"),
                    "url": item_url or f"https://{item_domain}",
                    "etv": item.get("etv"),
                }

            if item_type in ("local_pack", "map", "local_services", "knowledge_graph", "google_hotels"):
                return {
                    "position": 1,
                    "url": item_url or f"https://{item_domain}",
                    "etv": None,
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

            all_items = serp_data.get("items", []) or []
            rank = cls._find_domain_in_results(all_items, domain)

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
                    "etv": rank.get("etv"),
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
        payload = [
            {
                "keywords": keywords,
                "language_code": "en",
                "item_types": ["organic", "paid", "ai_overview_reference"],
            }
        ]

        try:
            logger.info("DataForSEO client Labs payload: %s", payload)
            response = requests.post(url, json=payload, auth=HTTPBasicAuth(settings.effective_serp_login, settings.effective_serp_key), timeout=60)
            logger.info("DataForSEO client Labs status: %s", response.status_code)
            logger.debug("DataForSEO client Labs full response: %s", response.text)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("DataForSEO keyword_overview request failed: %s", exc)
            return {}

        results = {}
        tasks = data.get("tasks", []) or []
        for task in tasks:
            result = task.get("result")
            if not result:
                continue
            if isinstance(result, list) and result:
                result = result[0]
            if not isinstance(result, dict):
                continue

            items = result.get("items") or []
            if not isinstance(items, list) or not items:
                logger.warning("DataForSEO client Labs returned no items. Full result=%s", result)
                continue

            item = items[0]
            keyword_properties = item.get("keyword_properties", {}) or {}
            keyword_info = item.get("keyword_info", {}) or {}
            avg_backlinks_info = item.get("avg_backlinks_info", {}) or {}
            search_intent_info = item.get("search_intent_info", {}) or {}

            kw = item.get("keyword") or (task.get("data") or {}).get("keyword")
            if not kw:
                continue
            results[kw] = {
                "volume": keyword_info.get("search_volume"),
                "difficulty": keyword_properties.get("keyword_difficulty"),
                "cpc": keyword_info.get("cpc"),
                "competition": keyword_info.get("competition"),
                "backlinks": avg_backlinks_info.get("backlinks"),
                "referring_domains": avg_backlinks_info.get("referring_domains"),
                "intent": search_intent_info.get("main_intent"),
            }
            logger.info("DataForSEO client Labs result for '%s': %s", kw, results[kw])
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
    def get_keyword_ideas(cls, db, user_id: str, seed_keyword: str, location_code: int = 2840) -> dict:
        from app.services.keyword_cache_service import query_cached_keyword

        cached = query_cached_keyword(db, seed_keyword, str(location_code))
        if cached:
            return {
                "seed": seed_keyword,
                "ideas": [cached],
                "credits_charged": 0,
            }

        ideas = cls.get_keyword_ideas_api(seed_keyword, location_code)
        return {
            "seed": seed_keyword,
            "ideas": ideas,
            "credits_charged": len(ideas),
        }

    @classmethod
    def get_keyword_ideas_api(cls, seed_keyword: str, location_code: int = 2840, limit: int = 50) -> list:
        url = f"{cls.BASE_URL}/dataforseo_labs/google/keyword_ideas/live"
        payload = [{
            "keywords": [seed_keyword],
            "location_code": location_code,
            "language_code": "en",
            "limit": min(limit, 1000),
        }]

        try:
            logger.info("DataForSEO keyword_ideas payload: %s", payload)
            response = requests.post(url, json=payload, auth=HTTPBasicAuth(settings.effective_serp_login, settings.effective_serp_key), timeout=60)
            logger.info("DataForSEO keyword_ideas status: %s", response.status_code)
            logger.debug("DataForSEO keyword_ideas full response: %s", response.text)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error("DataForSEO keyword_ideas request failed: %s", exc)
            return []

        results = []
        tasks = data.get("tasks", []) or []
        for task in tasks:
            task_status = task.get("status_code")
            if task_status and task_status != 20000:
                logger.warning("DataForSEO keyword_ideas task error %s: %s", task_status, task.get("status_message"))
                continue
            result = task.get("result")
            if not result:
                continue
            if isinstance(result, list) and result:
                result = result[0]
            if not isinstance(result, dict):
                continue
            items = result.get("items", []) or []
            for item in items:
                keyword_info = item.get("keyword_info", {}) or {}
                keyword_properties = item.get("keyword_properties", {}) or {}
                search_intent_info = item.get("search_intent_info", {}) or {}
                results.append({
                    "keyword": item.get("keyword"),
                    "volume": item.get("search_volume") or keyword_info.get("search_volume"),
                    "difficulty": item.get("keyword_difficulty") or keyword_properties.get("keyword_difficulty"),
                    "cpc": item.get("cpc") or keyword_info.get("cpc"),
                    "intent": item.get("search_intent") or search_intent_info.get("main_intent"),
                })
        logger.info("DataForSEO keyword_ideas returned %d ideas for '%s'", len(results), seed_keyword)
        return results

    @classmethod
    def get_competitor_keywords_cached(cls, db, user_id: str, domain: str, location_code: int = 2840, limit: int = 100) -> dict:
        from app.services.competitor_cache_service import query_cached_competitor

        cached = query_cached_competitor(db, domain, str(location_code))
        if cached:
            return {
                "domain": domain,
                "keywords": cached.get("keywords", []),
                "credits_charged": 0,
                "cached": True,
            }

        keywords = cls.get_competitor_keywords(domain, location_code, limit)
        return {
            "domain": domain,
            "keywords": keywords,
            "credits_charged": 1 if keywords else 0,
            "cached": False,
        }

    @classmethod
    def get_competitor_keywords(cls, domain: str, location_code: int = 2840, limit: int = 100) -> list:
        url = f"{cls.BASE_URL}/dataforseo_labs/google/competitors_domain/live"
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
            logger.debug("DataForSEO competitors_domain full response: %s", data)
        except Exception as exc:
            logger.error("DataForSEO competitors_domain request failed: %s", exc)
            return []

        results = []
        tasks = data.get("tasks", []) or []
        for task in tasks:
            task_status = task.get("status_code")
            if task_status and task_status != 20000:
                logger.warning("DataForSEO competitors_domain task error %s: %s", task_status, task.get("status_message"))
                continue

            result = task.get("result")
            if not result:
                continue
            if isinstance(result, list) and result:
                result = result[0]
            if not isinstance(result, dict):
                continue

            target_domain = (task.get("data") or {}).get("target", domain)
            items = result.get("items", []) or []
            for item in items:
                comp_domain = item.get("domain")
                if not comp_domain or comp_domain == target_domain:
                    continue

                metrics = item.get("metrics", {}) or {}
                organic = (metrics.get("organic") or {})
                paid = (metrics.get("paid") or {})

                results.append({
                    "domain": comp_domain,
                    "avg_position": item.get("avg_position"),
                    "intersections": item.get("intersections"),
                    "organic_keywords": organic.get("count"),
                    "etv": organic.get("etv"),
                    "paid_traffic_cost": paid.get("estimated_paid_traffic_cost"),
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
                "expand_ai_overview": True,
            }
            if result_type == "async":
                task["pingback_url"] = None
            tasks.append(task)

        payload = [{"tasks": tasks}]

        try:
            response = requests.post(url, json=payload, auth=HTTPBasicAuth(settings.effective_serp_login, settings.effective_serp_key), timeout=120)
            response.raise_for_status()
            data = response.json()
            logger.debug("DataForSEO SERP batch full response: %s", data)
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
            result = task.get("result")
            if not result:
                continue
            if isinstance(result, list) and result:
                result = result[0]
            if not isinstance(result, dict):
                continue

            items = result.get("items", []) or []
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
            result = task.get("result")
            if not result:
                continue
            if isinstance(result, list) and result:
                result = result[0]
            if not isinstance(result, dict):
                continue

            items = result.get("items", []) or []
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
            result = task.get("result")
            if not result:
                continue
            if isinstance(result, list) and result:
                result = result[0]
            if not isinstance(result, dict):
                continue

            items = result.get("items", []) or []
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
            result = task.get("result")
            if not result:
                continue
            if isinstance(result, list) and result:
                result = result[0]
            if not isinstance(result, dict):
                continue

            items = result.get("items", []) or []
            for item in items:
                keyword_info = item.get("keyword_info", {}) or {}
                keyword_properties = item.get("keyword_properties", {}) or {}
                results.append({
                    "keyword": item.get("keyword"),
                    "search_volume": item.get("search_volume") or keyword_info.get("search_volume"),
                    "difficulty": item.get("keyword_difficulty") or keyword_properties.get("keyword_difficulty"),
                    "cpc": item.get("cpc") or keyword_info.get("cpc"),
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
            result = task.get("result")
            if not result:
                continue
            if isinstance(result, list) and result:
                result = result[0]
            if not isinstance(result, dict):
                continue

            items = result.get("items", []) or []
            for item in items:
                keyword_info = item.get("keyword_info", {}) or {}
                keyword_properties = item.get("keyword_properties", {}) or {}
                search_intent_info = item.get("search_intent_info", {}) or {}
                results.append({
                    "keyword": item.get("keyword"),
                    "search_volume": item.get("search_volume") or keyword_info.get("search_volume"),
                    "difficulty": item.get("keyword_difficulty") or keyword_properties.get("keyword_difficulty"),
                    "cpc": item.get("cpc") or keyword_info.get("cpc"),
                    "intent": item.get("search_intent") or search_intent_info.get("main_intent"),
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
