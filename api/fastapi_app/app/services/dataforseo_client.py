import base64
import hashlib
import json
import logging
import math
import time
from datetime import datetime
from typing import Optional
from requests.auth import HTTPBasicAuth

import requests
from app.core.config import get_settings
from app.services.cache_service import get_cached, set_cached
from app.db.models import DataForSEOCost
from app.services.credit_service import track_dataforseo_cost

logger = logging.getLogger(__name__)
settings = get_settings()


def check_dfs_cost_ceiling(db, user_id: str, estimated_cost_usd: float) -> None:
    """
    Check if the user has exceeded their monthly DataForSEO cost ceiling.
    Uses advisory lock to prevent concurrent ceiling bypass.
    Raises HTTPException 403 if the ceiling would be exceeded.
    """
    from app.db.models import User, DataForSEOCost
    from sqlalchemy import select, func, text
    from fastapi import HTTPException

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # An incomplete legacy record must never inherit paid-plan DFS allowance.
    plan = user.selectedPlan or "free_trial"
    plan_def = settings.plan_config.plans.get(plan)
    if not plan_def:
        return

    ceiling = getattr(plan_def, "dfs_cost_ceiling_usd", 0.0)
    if ceiling <= 0:
        return

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    lock_id = (hash(f"{user_id}:{month_start.year}:{month_start.month}") & 0x7FFFFFFF)
    if db.bind.dialect.name == "postgresql":
        acquired = db.scalar(
            select(func.pg_try_advisory_xact_lock(lock_id))
        )
        if not acquired:
            raise HTTPException(
                status_code=429,
                detail="Concurrent cost ceiling check in progress, please retry",
            )

    current_spend = db.scalar(
        select(func.coalesce(func.sum(DataForSEOCost.costUsd), 0.0))
        .where(DataForSEOCost.userId == user_id)
        .where(DataForSEOCost.createdAt >= month_start)
    ) or 0.0

    if current_spend + estimated_cost_usd > ceiling:
        raise HTTPException(
            status_code=403,
            detail=(
                f"DataForSEO monthly cost ceiling exceeded. "
                f"Current spend: ${current_spend:.2f}, Ceiling: ${ceiling:.2f}, "
                f"Estimated additional cost: ${estimated_cost_usd:.2f}"
            ),
        )

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

CODE_TO_LOCATION = {code: name for name, code in LOCATION_MAP.items()}


def _build_serp_cache_key(keyword: str, location_code: int, language: str, device: str, os_name: str, depth: int, aio_flag: bool, engine: str = "google") -> str:
    keyword_hash = hashlib.md5(keyword.strip().lower().encode()).hexdigest()[:12]
    return f"serp:v1:{engine}:{keyword_hash}:{location_code}:{language}:{device}:{os_name or 'unknown'}:{depth}:{str(aio_flag).lower()}"


def _build_kw_metrics_cache_key(keyword: str, location_code: int, language: str) -> str:
    keyword_hash = hashlib.md5(keyword.strip().lower().encode()).hexdigest()[:12]
    return f"kw_metrics:v1:{keyword_hash}:{location_code}:{language}"


def _get_cached_serp(cache_key: str) -> Optional[dict]:
    try:
        return get_cached("serp", cache_key)
    except Exception as exc:
        logger.warning("SERP cache read failed: %s", exc)
        return None


def _set_cached_serp(cache_key: str, value: dict, ttl: int = 86400) -> bool:
    try:
        set_cached("serp", cache_key, value, ttl_seconds=ttl)
        return True
    except Exception as exc:
        logger.warning("SERP cache write failed: %s", exc)
        return False


def _get_cached_kw_metrics(cache_key: str) -> Optional[dict]:
    try:
        return get_cached("kw_metrics", cache_key)
    except Exception as exc:
        logger.warning("Keyword metrics cache read failed: %s", exc)
        return None


def _build_labs_cache_key(endpoint: str, identifier: str, location_code: int, language: str) -> str:
    identifier_hash = hashlib.md5(identifier.strip().lower().encode()).hexdigest()[:12]
    return f"labs:v1:{endpoint}:{identifier_hash}:{location_code}:{language}"


def _get_cached_labs(cache_key: str) -> Optional[dict]:
    try:
        return get_cached("labs", cache_key)
    except Exception as exc:
        logger.warning("Labs cache read failed: %s", exc)
        return None


def _set_cached_labs(cache_key: str, value: dict, ttl: int = 604800) -> bool:
    try:
        set_cached("labs", cache_key, value, ttl_seconds=ttl)
        return True
    except Exception as exc:
        logger.warning("Labs cache write failed: %s", exc)
        return False


def _set_cached_kw_metrics(cache_key: str, value: dict, ttl: int = 604800) -> bool:
    try:
        set_cached("kw_metrics", cache_key, value, ttl_seconds=ttl)
        return True
    except Exception as exc:
        logger.warning("Keyword metrics cache write failed: %s", exc)
        return False


def _estimate_dataforseo_cost(
    endpoint: str,
    keyword_count: int = 1,
    depth: int | None = None,
    cache_hit: bool = False,
    priority: int | str | None = None,
    safety_buffer_pct: float = 0.0,
) -> float:
    """Estimate official DataForSEO task cost.

    Google Organic SERP is billed per requested SERP (10 results), multiplied
    by requested depth. Labs "all other endpoints" are billed as a $0.012
    task plus $0.00012 per returned item. A safety buffer is opt-in only; the
    default reports the official formula without inventing markup.
    """
    if cache_hit:
        return 0.0

    count = max(0, int(keyword_count or 0))
    depth_units = max(1, math.ceil(max(1, int(depth or 10)) / 10))
    if endpoint == "/serp/google/organic/live/advanced":
        cost = 0.002 * depth_units * count
    elif endpoint == "/serp/google/organic/task_post":
        priority_queue = priority in (1, "1", "priority", "high")
        cost = (0.0012 if priority_queue else 0.0006) * depth_units * count
    elif endpoint == "/dataforseo_labs/google/bulk_traffic_estimation/live":
        cost = 0.12 + (0.0012 * count)
    elif endpoint.startswith("/dataforseo_labs/google/"):
        cost = 0.012 + (0.00012 * count)
    elif endpoint == "/backlinks/summary/live":
        cost = 0.040
    else:
        cost = 0.0

    return round(cost * (1 + max(0.0, safety_buffer_pct) / 100.0), 8)


def _log_dataforseo_cost(db, user_id, task_type, endpoint, method, keyword_count=1, priority=None, depth=None, expand_ai_overview=None, estimated_cost=None, actual_cost=None, cache_hit=False, success=True, error=None, meta=None, project_id=None, keyword_id=None, task_id=None, request_id=None):
    """Log DataForSEO cost for tracking and profitability analysis."""
    try:
        from app.services.credit_service import track_dataforseo_cost

        if estimated_cost is None:
            estimated_cost = _estimate_dataforseo_cost(
                endpoint, keyword_count, depth, cache_hit, priority=priority
            )

        cost_meta = {
            "method": method,
            "priority": priority,
            "depth": depth,
            "expand_ai_overview": expand_ai_overview,
            "cache_hit": cache_hit,
            "success": success,
        }
        if meta:
            cost_meta.update(meta)
        if error:
            cost_meta["error"] = str(error)[:500]

        track_dataforseo_cost(
            db=db,
            user_id=user_id,
            task_type=task_type,
            endpoint=endpoint,
            cost_credits=estimated_cost,
            keyword_count=keyword_count,
            cost_usd=actual_cost,
            meta=cost_meta,
            project_id=project_id,
            keyword_id=keyword_id,
            task_id=task_id,
            request_id=request_id,
        )
    except Exception as exc:
        logger.warning("Failed to log DataForSEO cost: %s", exc)


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
                    "position": item.get("rank_group") or item.get("rank_absolute"),
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
    def get_rank_batch(cls, keywords: list[dict], domain: str, location: str = "India", device: str = "desktop", aio_keyword_texts: set | None = None, depth: int = 100) -> dict:
        if not keywords:
            return {}

        serp_map = cls.get_serp_data_batch(keywords, location, device, aio_keyword_texts=aio_keyword_texts, depth=depth)
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
    def _fetch_keyword_data_batch(cls, keywords: list[str], location: str = "India", db=None, user_id: str | None = None) -> dict:
        if not keywords:
            return {}

        location_code = LOCATION_MAP.get(location, 2840)
        
        # Check keyword metrics cache first
        cached_results = {}
        missing_keywords = []
        for kw in keywords:
            cache_key = _build_kw_metrics_cache_key(kw, location_code, "en")
            cached = _get_cached_kw_metrics(cache_key)
            if cached:
                cached_results[kw] = cached
                if db and user_id:
                    _log_dataforseo_cost(db, user_id, "keyword_metrics_cache_hit", "/dataforseo_labs/google/keyword_overview/live", "GET", keyword_count=1, cache_hit=True, success=True)
            else:
                missing_keywords.append(kw)
        
        if not missing_keywords:
            return cached_results
        
        url = f"{cls.BASE_URL}/dataforseo_labs/google/keyword_overview/live"
        payload = [
            {
                "keywords": missing_keywords,
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
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "keyword_metrics_error", "/dataforseo_labs/google/keyword_overview/live", "POST", keyword_count=len(missing_keywords), cache_hit=False, success=False, error=exc)
            return {}

        results = dict(cached_results)
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
            metric_entry = {
                "volume": keyword_info.get("search_volume"),
                "difficulty": keyword_properties.get("keyword_difficulty"),
                "cpc": keyword_info.get("cpc"),
                "competition": keyword_info.get("competition"),
                "backlinks": avg_backlinks_info.get("backlinks"),
                "referring_domains": avg_backlinks_info.get("referring_domains"),
                "intent": search_intent_info.get("main_intent"),
            }
            results[kw] = metric_entry
            logger.info("DataForSEO client Labs result for '%s': %s", kw, metric_entry)
            
            # Store in keyword metrics cache
            cache_key = _build_kw_metrics_cache_key(kw, location_code, "en")
            _set_cached_kw_metrics(cache_key, metric_entry, ttl=604800)  # 7 days
            
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "keyword_metrics", "/dataforseo_labs/google/keyword_overview/live", "POST", keyword_count=1, cache_hit=False, success=True)

        return results

    @classmethod
    def fetch_dashboard_data(cls, keywords, target_domain, location_code=2840, language_code="en", pingback_url=None, db=None, user_id=None, depth: int = 100, aio_keyword_texts: set | None = None):
        if isinstance(keywords, str):
            keywords = [keywords]

        if not keywords:
            return []

        location = CODE_TO_LOCATION.get(location_code, "India") if isinstance(location_code, int) else (location_code or "India")

        labs_results = cls._fetch_keyword_data_batch(keywords, location, db=db, user_id=user_id)

        metrics_map = {}
        for kw in keywords:
            metric_entry = labs_results.get(kw)
            if metric_entry:
                metrics_map[kw] = {
                    "keyword": kw,
                    "volume": metric_entry.get("volume"),
                    "kd": metric_entry.get("difficulty"),
                    "cpc": metric_entry.get("cpc"),
                    "competition": metric_entry.get("competition"),
                    "competition_level": None,
                    "intent": metric_entry.get("intent"),
                    "foreign_intent": None,
                    "backlinks": metric_entry.get("backlinks"),
                    "dofollow": None,
                    "referring_pages": None,
                    "referring_domains": metric_entry.get("referring_domains"),
                    "referring_main_domains": None,
                    "domain_rank": None,
                    "etv": None,
                    "categories": None,
                    "monthly_searches": None,
                    "search_volume_trend": None,
                    "low_top_of_page_bid": None,
                    "high_top_of_page_bid": None,
                    "detected_language": None,
                    "words_count": None,
                }
                logger.info("DataForSEO client Labs metrics for '%s': volume=%s kd=%s cpc=%s competition=%s intent=%s",
                            kw,
                            metric_entry.get("volume"),
                            metric_entry.get("difficulty"),
                            metric_entry.get("cpc"),
                            metric_entry.get("competition"),
                            metric_entry.get("intent"))

        serp_data = cls.get_serp_data_batch(
            [{"keyword": kw, "location": location, "device": "desktop"} for kw in keywords],
            location,
            db=db,
            user_id=user_id,
            depth=depth,
            aio_keyword_texts=aio_keyword_texts,
        )

        serp_map = {}
        for kw in keywords:
            serp_entry = serp_data.get(kw, {})
            detected_position = None
            has_aio_badge = None
            check_url = None
            ai_description = None

            all_items = serp_entry.get("items", []) or []
            for item in all_items:
                item_type = item.get("type", "")

                if item_type == "organic" and item.get("url"):
                    if target_domain and target_domain.lower() in item.get("url", "").lower():
                        candidate_position = item.get("rank_group") or item.get("rank_absolute")
                        if candidate_position and (detected_position is None or candidate_position < detected_position):
                            detected_position = candidate_position
                        if not check_url:
                            check_url = item.get("url")

                if item_type in ("local_pack", "map", "local_services", "knowledge_graph", "google_hotels"):
                    url = item.get("url") or ""
                    domain = item.get("domain") or ""
                    if target_domain and (target_domain.lower() in url.lower() or target_domain.lower() in domain.lower()):
                        if detected_position is None:
                            detected_position = item.get("rank_group") or item.get("rank_absolute") or 1
                        if not check_url:
                            check_url = url or f"https://{domain}" if domain else url

                if item_type == "ai_overview":
                    if item.get("asynchronous_ai_overview") is True:
                        has_aio_badge = "AIO"
                    ai_description = item.get("description") or item.get("text") or item.get("content") or ai_description
                    if not ai_description and item.get("markdown"):
                        ai_description = item.get("markdown")
                    nested_items = item.get("items", []) or []
                    if isinstance(nested_items, list):
                        for nested in nested_items:
                            if not ai_description and nested and nested.get("description"):
                                ai_description = nested.get("description")
                            if not ai_description and nested and nested.get("text"):
                                ai_description = nested.get("text")
                    references = item.get("ai_overview_reference", []) or item.get("references", []) or []
                    if isinstance(references, list):
                        for ref in references:
                            if ref and ref.get("url") and target_domain:
                                if target_domain in ref.get("url", "").lower():
                                    has_aio_badge = "AIO"

                if item_type == "organic" and item.get("url"):
                    item_domain = (item.get("domain") or "").lower()
                    item_url = item.get("url") or ""
                    if target_domain and (target_domain.lower() in item_url.lower() or target_domain.lower() in item_domain):
                        if has_aio_badge != "AIO":
                            has_aio_badge = "AIO"
                        if not ai_description and item.get("description"):
                            ai_description = item.get("description")
                        if not check_url:
                            check_url = item_url

            item_groups = serp_entry.get("item_groups", []) or []
            for group in item_groups:
                group_type = group.get("type")
                group_items = group.get("items", []) or []
                if group_type == "ai_overview" and group_items and not has_aio_badge:
                    references = group_items[0].get("references", []) or group_items[0].get("ai_overview_reference", []) or []
                    if isinstance(references, list):
                        for ref in references:
                            if ref and ref.get("url") and target_domain:
                                if target_domain in ref.get("url", "").lower():
                                    has_aio_badge = "AIO"

            serp_map[kw] = {
                "position": detected_position,
                "ai_badge": has_aio_badge,
                "ai_description": ai_description,
                "check_url": check_url,
            }

        final_table_rows = []
        for kw in keywords:
            kw_metrics = metrics_map.get(kw, {
                "keyword": kw,
                "volume": None, "kd": None, "cpc": None,
                "competition": None, "backlinks": None, "referring_domains": None,
                "intent": None, "foreign_intent": None, "competition_level": None,
                "dofollow": None, "referring_pages": None, "referring_main_domains": None,
                "domain_rank": None, "etv": None, "categories": None,
                "monthly_searches": None, "search_volume_trend": None,
                "low_top_of_page_bid": None, "high_top_of_page_bid": None,
                "detected_language": None, "words_count": None,
            })
            serp_data_row = serp_map.get(kw, {})

            merged = {**kw_metrics, **serp_data_row}
            final_table_rows.append(merged)

        logger.info("DataForSEO client dashboard fetch complete: %d keywords, %d with metrics, %d with SERP",
                    len(keywords), len(metrics_map), len(serp_map))
        return final_table_rows

    @classmethod
    def get_keyword_metrics(cls, db, user_id: str, keywords: list[dict]) -> dict:
        if not keywords:
            return {"results": [], "credits_charged": 0, "cached_count": 0, "user_cache_hits": 0}

        keyword_texts = [kw.get("keyword", "") for kw in keywords if kw.get("keyword")]
        location = keywords[0].get("location", "India") if keywords else "India"
        results = cls._fetch_keyword_data_batch(keyword_texts, location, db=db, user_id=user_id)

        return {
            "results": list(results.values()),
            "credits_charged": len(results),
            "cached_count": 0,
            "user_cache_hits": 0,
        }

    @classmethod
    def bulk_keyword_lookup(cls, db, user_id: str, keywords: list[dict]) -> dict:
        if not keywords:
            return {"results": [], "credits_charged": 0, "cached_count": 0, "missing_count": 0}

        keyword_texts = [kw.get("keyword", "") for kw in keywords if kw.get("keyword")]
        location = keywords[0].get("location", "India") if keywords else "India"
        results = cls._fetch_keyword_data_batch(keyword_texts, location, db=db, user_id=user_id)

        return {
            "results": list(results.values()),
            "credits_charged": len(results),
            "cached_count": 0,
            "missing_count": 0,
        }

    @classmethod
    def get_keyword_ideas(cls, db, user_id: str, seed_keyword: str, location_code: int = 2840) -> dict:
        cache_key = _build_labs_cache_key("keyword_ideas", seed_keyword, location_code, "en")
        cached = _get_cached_labs(cache_key)
        if cached:
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "keyword_ideas", "/dataforseo_labs/google/keyword_ideas/live", "GET", keyword_count=len(cached.get("ideas", [])), cache_hit=True, success=True)
            return cached

        ideas = cls.get_keyword_ideas_api(seed_keyword, location_code, db=db, user_id=user_id)
        result = {
            "seed": seed_keyword,
            "ideas": ideas,
            "credits_charged": len(ideas),
        }
        _set_cached_labs(cache_key, result, ttl=604800)
        return result

    @classmethod
    def get_keyword_ideas_api(cls, seed_keyword: str, location_code: int = 2840, limit: int = 50, db=None, user_id: str | None = None) -> list:
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
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "keyword_ideas", "/dataforseo_labs/google/keyword_ideas/live", "POST", success=False, error=exc)
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
        
        if db and user_id:
            _log_dataforseo_cost(db, user_id, "keyword_ideas", "/dataforseo_labs/google/keyword_ideas/live", "POST", keyword_count=len(results), success=True)
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

        cache_key = _build_labs_cache_key("competitors_domain", domain, location_code, "en")
        labs_cached = _get_cached_labs(cache_key)
        if labs_cached:
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "competitors_domain", "/dataforseo_labs/google/competitors_domain/live", "GET", cache_hit=True, success=True)
            return {
                "domain": domain,
                "keywords": labs_cached.get("keywords", []),
                "credits_charged": 0,
                "cached": True,
            }

        keywords = cls.get_competitor_keywords(domain, location_code, limit, db=db, user_id=user_id)
        result = {
            "domain": domain,
            "keywords": keywords,
            "credits_charged": 1 if keywords else 0,
            "cached": False,
        }
        _set_cached_labs(cache_key, result, ttl=604800)
        return result

    @classmethod
    def get_competitor_keywords(cls, domain: str, location_code: int = 2840, limit: int = 100, db=None, user_id: str | None = None) -> list:
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
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "competitors_domain", "/dataforseo_labs/google/competitors_domain/live", "POST", success=False, error=exc)
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
        
        if db and user_id:
            _log_dataforseo_cost(db, user_id, "competitors_domain", "/dataforseo_labs/google/competitors_domain/live", "POST", keyword_count=limit, success=True)
        return results[:limit]

    @classmethod
    def get_serp_data_batch(cls, keywords: list[dict], location: str = "India", device: str = "desktop", result_type: str = "regular", aio_keyword_texts: set | None = None, db=None, user_id: str | None = None, priority: str | None = None, os_name: str | None = None, force_refresh: bool = False, depth: int = 100) -> dict:
        if not keywords:
            return {}

        location_code = LOCATION_MAP.get(location, 2840)
        expand_ai_overview = True if aio_keyword_texts else False
        cache_ttl = 86400  # 24 hours
        
        # Check shared SERP cache first unless force_refresh
        cached_results = {}
        missing_keywords = []
        if not force_refresh:
            for kw in keywords:
                keyword_text = kw.get("keyword", "")
                if not keyword_text:
                    continue
                cache_key = _build_serp_cache_key(keyword_text, location_code, "en", DEVICE_MAP.get(device, "desktop"), os_name or "unknown", depth, expand_ai_overview)
                cached = _get_cached_serp(cache_key)
                if cached:
                    cached_results[keyword_text] = cached
                    if db and user_id:
                        _log_dataforseo_cost(db, user_id, "serp_cache_hit", "/serp/google/organic/live/advanced", "GET", keyword_count=1, priority=priority, depth=depth, expand_ai_overview=expand_ai_overview, cache_hit=True, success=True)
                else:
                    missing_keywords.append(kw)
        else:
            missing_keywords = list(keywords)
            if db and user_id:
                for kw in keywords:
                    keyword_text = kw.get("keyword", "")
                    if keyword_text:
                        _log_dataforseo_cost(db, user_id, "manual_serp_force_refresh", "/serp/google/organic/live/advanced", "GET", keyword_count=1, priority=priority, depth=depth, expand_ai_overview=expand_ai_overview, cache_hit=False, success=True)
        
        if not missing_keywords:
            return cached_results
        
        # Fetch missing keywords from DataForSEO
        url = f"{cls.BASE_URL}/serp/google/organic/live/advanced"
        tasks = []
        for kw in missing_keywords:
            task = {
                "keyword": kw.get("keyword", ""),
                "location_code": location_code,
                "language_code": "en",
                "device": DEVICE_MAP.get(device, "desktop"),
                "depth": depth,
                "expand_ai_overview": expand_ai_overview,
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
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "serp_error", "/serp/google/organic/live/advanced", "POST", keyword_count=len(missing_keywords), priority=priority, depth=depth, expand_ai_overview=expand_ai_overview, cache_hit=False, success=False, error=exc)
            return {}

        results = dict(cached_results)
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
            
            # Store in shared cache
            cache_key = _build_serp_cache_key(keyword_text, location_code, "en", DEVICE_MAP.get(device, "desktop"), os_name or "unknown", depth, expand_ai_overview)
            _set_cached_serp(cache_key, serp_entry, ttl=cache_ttl)
            
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "weekly_serp" if result_type == "async" else "manual_serp", "/serp/google/organic/live/advanced", "POST", keyword_count=1, priority=priority, depth=depth, expand_ai_overview=expand_ai_overview, cache_hit=False, success=True)

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
    def get_backlinks(cls, target_domain: str, limit: int = 100, db=None, user_id: str | None = None) -> list:
        cache_key = _build_labs_cache_key("backlinks", target_domain, 0, "en")
        cached = _get_cached_labs(cache_key)
        if cached:
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "backlinks", "/backlinks/summary/live", "GET", cache_hit=True, success=True)
            return cached.get("results", [])[:limit]

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
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "backlinks", "/backlinks/summary/live", "POST", success=False, error=exc)
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
        
        if db and user_id:
            _log_dataforseo_cost(db, user_id, "backlinks", "/backlinks/summary/live", "POST", success=True)
        _set_cached_labs(cache_key, {"results": results[:limit]}, ttl=604800)
        return results[:limit]

    @classmethod
    def get_domain_rank_overview(cls, domain: str, location: str = "India", db=None, user_id: str | None = None) -> Optional[dict]:
        location_code = LOCATION_MAP.get(location, 2840)
        cache_key = _build_labs_cache_key("domain_rank_overview", domain, location_code, "en")
        cached = _get_cached_labs(cache_key)
        if cached:
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "domain_rank_overview", "/dataforseo_labs/google/domain_rank_overview/live", "GET", cache_hit=True, success=True)
            return cached.get("result")

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
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "domain_rank_overview", "/dataforseo_labs/google/domain_rank_overview/live", "POST", success=False, error=exc)
            return None

        tasks = data.get("tasks", []) or []
        result_data = None
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
                result_data = items[0]
                if db and user_id:
                    _log_dataforseo_cost(db, user_id, "domain_rank_overview", "/dataforseo_labs/google/domain_rank_overview/live", "POST", success=True)
                break
        
        if result_data is None and db and user_id:
            _log_dataforseo_cost(db, user_id, "domain_rank_overview", "/dataforseo_labs/google/domain_rank_overview/live", "POST", success=True)
        
        if result_data:
            _set_cached_labs(cache_key, {"result": result_data}, ttl=604800)
        return result_data

    @classmethod
    def get_bulk_traffic_estimation(cls, domains: list[str], location: str = "India", db=None, user_id: str | None = None) -> list:
        if not domains:
            return []

        location_code = LOCATION_MAP.get(location, 2840)
        domains_key = ",".join(sorted(domains))
        cache_key = _build_labs_cache_key("bulk_traffic_estimation", domains_key, location_code, "en")
        cached = _get_cached_labs(cache_key)
        if cached:
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "bulk_traffic_estimation", "/dataforseo_labs/google/bulk_traffic_estimation/live", "GET", keyword_count=len(domains), cache_hit=True, success=True)
            return cached.get("results", [])

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
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "bulk_traffic_estimation", "/dataforseo_labs/google/bulk_traffic_estimation/live", "POST", keyword_count=len(domains), success=False, error=exc)
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
        
        if db and user_id:
            _log_dataforseo_cost(db, user_id, "bulk_traffic_estimation", "/dataforseo_labs/google/bulk_traffic_estimation/live", "POST", keyword_count=len(domains), success=True)
        _set_cached_labs(cache_key, {"results": results}, ttl=604800)
        return results

    @classmethod
    def get_keyword_suggestions(cls, seed_keyword: str, location: str = "India", limit: int = 100, db=None, user_id: str | None = None) -> list:
        location_code = LOCATION_MAP.get(location, 2840)
        cache_key = _build_labs_cache_key("keyword_suggestions", seed_keyword, location_code, "en")
        cached = _get_cached_labs(cache_key)
        if cached:
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "keyword_suggestions", "/dataforseo_labs/google/keyword_suggestions/live", "GET", keyword_count=len(cached.get("results", [])), cache_hit=True, success=True)
            return cached.get("results", [])[:limit]

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
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "keyword_suggestions", "/dataforseo_labs/google/keyword_suggestions/live", "POST", success=False, error=exc)
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
        
        if db and user_id:
            _log_dataforseo_cost(db, user_id, "keyword_suggestions", "/dataforseo_labs/google/keyword_suggestions/live", "POST", keyword_count=len(results), success=True)
        _set_cached_labs(cache_key, {"results": results[:limit]}, ttl=604800)
        return results[:limit]

    @classmethod
    def get_keywords_for_keywords(cls, keywords: list[str], location: str = "India", limit: int = 100, db=None, user_id: str | None = None) -> list:
        if not keywords:
            return []

        location_code = LOCATION_MAP.get(location, 2840)
        keywords_key = ",".join(sorted(keywords))
        cache_key = _build_labs_cache_key("keywords_for_keywords", keywords_key, location_code, "en")
        cached = _get_cached_labs(cache_key)
        if cached:
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "keywords_for_keywords", "/dataforseo_labs/google/keywords_for_keywords/live", "GET", keyword_count=len(keywords), cache_hit=True, success=True)
            return cached.get("results", [])[:limit]

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
            if db and user_id:
                _log_dataforseo_cost(db, user_id, "keywords_for_keywords", "/dataforseo_labs/google/keywords_for_keywords/live", "POST", keyword_count=len(keywords), success=False, error=exc)
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
        
        if db and user_id:
            _log_dataforseo_cost(db, user_id, "keywords_for_keywords", "/dataforseo_labs/google/keywords_for_keywords/live", "POST", keyword_count=len(keywords), success=True)
        _set_cached_labs(cache_key, {"results": results[:limit]}, ttl=604800)
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
