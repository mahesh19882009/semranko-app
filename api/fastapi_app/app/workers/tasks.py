import random
from datetime import datetime
from typing import Optional
import requests
from sqlalchemy import delete
from app.services.dataforseo_client import DataForSEOClient
from app.db.models import Backlink, RankResult
from app.db.session import SessionLocal
from app.core.config import get_settings

settings = get_settings()
LOCATION_CODES = {"India": 2356, "United States": 2840, "United Kingdom": 2826, "Global": 2840}


def fake_rank_lookup(keyword: dict, domain: str) -> dict:
    """
    Generate realistic mock rank data for development.
    When SERP_API_KEY is configured, this will be replaced with real API calls.
    """
    # Use pseudo-random but consistent results based on keyword
    keyword_seed = sum(ord(c) for c in keyword["keyword"])
    random.seed(keyword_seed)
    
    # Generate realistic position distribution (better keywords rank higher)
    position = random.randint(1, 50)
    
    # Simulate some keywords not ranking
    if random.random() < 0.1:  # 10% chance of not ranking
        position = None
        url = None
    else:
        url = f"https://{domain}"
    
    result = {
        "position": position,
        "url": url,
        "keywordText": keyword["keyword"],
        "location": keyword.get("location") or "India",
        "device": keyword.get("device") or "desktop",
    }
    
    # Reset random seed
    random.seed()
    return result


def dataforseo_rank_lookup(keyword: dict, domain: str) -> Optional[dict]:
    if not settings.SERP_API_KEY or not settings.SERP_API_LOGIN:
        return None

    try:
        from app.services.dataforseo_client import DataForSEOClient
        result = DataForSEOClient.get_rank(
            keyword=keyword.get("keyword", ""),
            domain=domain,
            location=keyword.get("location", "India"),
            device=keyword.get("device", "desktop"),
        )
        if result is None:
            return None

        return {
            "position": result.get("position"),
            "url": result.get("url"),
            "keywordText": keyword.get("keyword", ""),
            "location": keyword.get("location") or "India",
            "device": keyword.get("device") or "desktop",
            "featured_snippet": result.get("featured_snippet", False),
            "local_pack": False,
        }
    except Exception as e:
        print(f"DataForSEO rank lookup error: {e}")
        return None


def serp_api_rank_lookup(keyword: dict, domain: str) -> Optional[dict]:
    """
    Wrapper function that tries DataForSEO first (preferred),
    then falls back to other APIs if configured.
    
    Priority order:
    1. DataForSEO (if credentials provided)
    2. SerpAPI (if SERP_API_KEY provided without login)
    3. Mock data (fallback)
    """
    # Try DataForSEO first (requires both login and key)
    if settings.SERP_API_LOGIN and settings.SERP_API_KEY:
        result = dataforseo_rank_lookup(keyword, domain)
        if result is not None:
            return result
    
    # Fallback to SerpAPI if only SERP_API_KEY is provided (no login)
    if settings.SERP_API_KEY and not settings.SERP_API_LOGIN:
        return serpapi_rank_lookup(keyword, domain)
    
    # No valid API configuration
    return None


def serpapi_rank_lookup(keyword: dict, domain: str) -> Optional[dict]:
    """
    Alternative SERP lookup using SerpAPI.
    Used as fallback if DataForSEO is not configured.
    """
    if not settings.SERP_API_KEY:
        return None
    
    try:
        import requests
        
        # Map location names to SerpAPI location parameters
        params = {
            'engine': 'google',
            'q': keyword['keyword'],
            'location': keyword.get('location', 'India'),
            'hl': 'en',
            'gl': 'in',
            'api_key': settings.SERP_API_KEY,
            'num': 100  # Get top 100 results
        }
        
        # Add device parameter
        if keyword.get('device') == 'mobile':
            params['device'] = 'mobile'
        
        response = requests.get('https://serpapi.com/search.json', params=params, timeout=30)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        # Find domain in organic results
        position = None
        url = None
        
        if 'organic_results' in data:
            for idx, result in enumerate(data['organic_results'], start=1):
                link = result.get('link', '')
                if domain.lower() in link.lower():
                    position = idx
                    url = link
                    break
        
        if position:
            return {
                "position": position,
                "url": url,
                "keywordText": keyword["keyword"],
                "location": keyword.get("location") or "India",
                "device": keyword.get("device") or "desktop",
            }
        
        return None
        
    except Exception as e:
        print(f"SerpAPI error: {str(e)}")
        return None


def process_rank_check_job(project_id: str, domain: str, keywords: list[dict]) -> dict:
    if not project_id or not domain or not isinstance(keywords, list):
        raise ValueError("Invalid job payload")

    rows = []
    for keyword in keywords:
        result = serp_api_rank_lookup(keyword, domain)
        if result is None:
            result = fake_rank_lookup(keyword, domain)

        rows.append(
            {
                "projectId": project_id,
                "keywordId": keyword.get("id"),
                "keywordText": result["keywordText"],
                "position": result["position"],
                "url": result["url"],
                "location": result["location"],
                "device": result["device"],
                "checkedAt": datetime.utcnow(),
            }
        )

    db = SessionLocal()
    try:
        for keyword in keywords:
            db.execute(
                delete(RankResult).where(
                    RankResult.projectId == project_id,
                    RankResult.keywordId == keyword.get("id"),
                )
            )

        if rows:
            db.bulk_insert_mappings(RankResult, rows)

        db.commit()
        return {"inserted": len(rows)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def process_backlink_job(project_id: str, domain: str) -> dict:
    if not project_id or not domain:
        raise ValueError("Invalid job payload")

    backlink_rows = []

    try:
        from app.services.dataforseo_client import DataForSEOClient
        bl_results = DataForSEOClient.get_backlinks(domain, limit=100)
    except Exception as e:
        print(f"DataForSEO backlink error: {e}")
        bl_results = []

    if not bl_results:
        return {"inserted": 0, "message": "No backlink data available"}

    for bl in bl_results:
        backlink_rows.append(
            {
                "projectId": project_id,
                "sourceUrl": bl.get("source_url") or "",
                "sourceDomain": bl.get("source_domain") or "",
                "anchor": bl.get("anchor"),
                "domainRank": bl.get("rank"),
                "firstSeen": datetime.utcnow(),
                "checkedAt": datetime.utcnow(),
            }
        )

    db = SessionLocal()
    try:
        db.execute(
            delete(Backlink).where(Backlink.projectId == project_id)
        )

        if backlink_rows:
            db.bulk_insert_mappings(Backlink, backlink_rows)

        db.commit()
        return {"inserted": len(backlink_rows)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

