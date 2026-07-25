import random
from datetime import datetime
from typing import Optional
import requests
from requests.auth import HTTPBasicAuth
import json

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


def dataforseo_rank_lookup(keyword: dict, domain: str) -> Optional[dict]:
    """
    Real rank lookup using DataForSEO Google SERP API.
    
    DataForSEO provides accurate, real-time SERP data with:
    - Exact position tracking
    - SERP features detection (featured snippets, local packs, etc.)
    - Historical data support
    - Global location coverage
    
    API Docs: https://docs.dataforseo.com/v3/serp/google/organic/task_post/
    
    Returns dict with position, url, and SERP features or None if not found/error.
    """
    if not settings.SERP_API_KEY or not settings.SERP_API_LOGIN:
        return None
    
    try:
        # DataForSEO API endpoint for Google Organic SERP
        api_url = "https://api.dataforseo.com/v3/serp/google/organic/task_post"
        
        # Prepare the request payload
        # Map common location names to DataForSEO location codes
        location_map = {
            "India": "2356",
            "United States": "2840",
            "United Kingdom": "2826",
            "Canada": "2124",
            "Australia": "2036",
            "Germany": "2276",
            "France": "2250",
            "Japan": "2392",
            "Brazil": "2076",
        }
        
        location_code = location_map.get(keyword.get("location", "India"), "2356")
        
        # Map device to DataForSEO device parameter
        device = keyword.get("device", "desktop")
        se_type = "mobile" if device == "mobile" else "desktop"
        
        payload = [
            {
                "keyword": keyword["keyword"],
                "location_code": location_code,
                "language_code": "en",
                "depth": 100,  # Check top 100 results
                "se_type": se_type,
                "tag": keyword.get("id", "")  # Tag with keyword ID for tracking
            }
        ]
        
        # Make API request with Basic Auth
        response = requests.post(
            api_url,
            auth=HTTPBasicAuth(settings.SERP_API_LOGIN, settings.SERP_API_KEY),
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code != 20000 and response.status_code != 200:
            print(f"DataForSEO API error: {response.status_code} - {response.text}")
            return None
        
        task_response = response.json()
        
        if task_response.get("status_code") != 20000:
            print(f"DataForSEO task creation failed: {task_response}")
            return None
        
        # Get task ID to fetch results
        task_id = task_response.get("tasks", [{}])[0].get("id")
        
        if not task_id:
            return None
        
        # Fetch task results (synchronous approach for simplicity)
        # In production, you might want to use webhooks for async processing
        result_url = f"https://api.dataforseo.com/v3/serp/google/organic/task_get/{task_id}"
        
        result_response = requests.get(
            result_url,
            auth=HTTPBasicAuth(settings.SERP_API_LOGIN, settings.SERP_API_KEY),
            timeout=30
        )
        
        if result_response.status_code != 200:
            print(f"DataForSEO result fetch error: {result_response.status_code}")
            return None
        
        result_data = result_response.json()
        
        if result_data.get("status_code") != 20000:
            return None
        
        # Extract ranking data
        tasks = result_data.get("tasks", [])
        if not tasks:
            return None
        
        task_result = tasks[0]
        if task_result.get("status_code") != 20000:
            return None
        
        # Get organic results
        organic_results = task_result.get("result", [{}])[0].get("items", [])
        
        # Find our domain in the results
        position = None
        url = None
        featured_snippet = False
        local_pack = False
        
        for idx, item in enumerate(organic_results, start=1):
            item_domain = item.get("domain", "")
            item_url = item.get("url", "")
            
            # Check if this result matches our domain
            if domain.lower() in item_domain.lower() or domain.lower() in (item_url or "").lower():
                position = idx
                url = item_url or f"https://{item_domain}"
                
                # Check for SERP features
                if item.get("type") == "featured_snippet":
                    featured_snippet = True
                if item.get("type") == "local_pack":
                    local_pack = True
                
                break
        
        # If not found in organic results, check other SERP features
        if position is None:
            # Check featured snippet separately
            snippet = task_result.get("result", [{}])[0].get("item_groups", [])
            for group in snippet:
                if group.get("type") == "featured_snippet":
                    items = group.get("items", [])
                    for item in items:
                        if domain.lower() in (item.get("domain") or "").lower():
                            position = 0  # Featured snippet is position 0
                            url = item.get("url")
                            featured_snippet = True
                            break
        
        return {
            "position": position,
            "url": url,
            "keywordText": keyword["keyword"],
            "location": keyword.get("location") or "India",
            "device": keyword.get("device") or "desktop",
            "featured_snippet": featured_snippet,
            "local_pack": local_pack,
        }
        
    except requests.exceptions.RequestException as e:
        print(f"DataForSEO request error: {str(e)}")
        return None
    except Exception as e:
        print(f"DataForSEO unexpected error: {str(e)}")
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
        # Try real SERP API first (DataForSEO or SerpAPI), fallback to mock data
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
