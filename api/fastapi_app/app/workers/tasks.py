import random
from datetime import datetime
from typing import Optional

from sqlalchemy import delete

from app.db.models import RankResult
from app.db.session import SessionLocal
from app.core.config import get_settings

settings = get_settings()


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


def serp_api_rank_lookup(keyword: dict, domain: str) -> Optional[dict]:
    """
    Real SERP API lookup - currently a placeholder.
    When SERP_API_KEY is configured, implement actual API call here.
    
    Supported APIs:
    - SerpAPI (https://serpapi.com/)
    - DataForSEO (https://dataforseo.com/)
    - ValueSERP (https://valueserp.com/)
    """
    if not settings.SERP_API_KEY:
        return None
    
    # TODO: Implement actual SERP API call
    # Example for SerpAPI:
    # import requests
    # params = {
    #     'engine': 'google',
    #     'q': keyword['keyword'],
    #     'location': keyword.get('location', 'India'),
    #     'hl': 'en',
    #     'gl': 'in',
    #     'api_key': settings.SERP_API_KEY
    # }
    # response = requests.get('https://serpapi.com/search.json', params=params)
    # Parse response to find domain position
    
    return None


def process_rank_check_job(project_id: str, domain: str, keywords: list[dict]) -> dict:
    if not project_id or not domain or not isinstance(keywords, list):
        raise ValueError("Invalid job payload")

    rows = []
    for keyword in keywords:
        # Try real SERP API first, fallback to mock data
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
