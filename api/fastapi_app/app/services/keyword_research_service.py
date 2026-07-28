import httpx
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.db.models import Keyword, RankResult, Project
from app.core.config import get_settings

settings = get_settings()


async def get_keyword_suggestions(seed_keyword: str) -> List[Dict]:
    """
    Get keyword suggestions using Google Autocomplete API (free)
    """
    suggestions = []
    
    try:
        # Google Autocomplete API (free, no API key needed)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://suggestqueries.google.com/complete/search",
                params={
                    "client": "firefox",
                    "q": seed_keyword,
                    "hl": "en"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1:
                    for suggestion in data[1]:
                        suggestions.append({
                            "keyword": suggestion,
                            "source": "google_autocomplete"
                        })
    except Exception as e:
        print(f"Error fetching keyword suggestions: {e}")
    
    return suggestions


def calculate_keyword_difficulty(db: Session, keyword: str, project_id: str) -> int:
    """
    Calculate keyword difficulty based on existing rank data
    Returns a score from 0-100 (higher = more difficult)
    """
    difficulty = 50  # Default medium difficulty
    
    try:
        # Check if we have rank data for this keyword
        rank_result = db.execute(
            select(RankResult)
            .where(RankResult.keywordText == keyword)
            .where(RankResult.projectId == project_id)
            .order_by(RankResult.checkedAt.desc())
            .limit(1)
        ).scalar_one_or_none()
        
        if rank_result and rank_result.position:
            position = rank_result.position
            
            # Lower difficulty if already ranking well
            if position <= 10:
                difficulty = 20
            elif position <= 20:
                difficulty = 35
            elif position <= 50:
                difficulty = 50
            elif position <= 100:
                difficulty = 65
            else:
                difficulty = 80
        
        # Adjust based on keyword length (longer keywords usually easier)
        word_count = len(keyword.split())
        if word_count >= 4:
            difficulty = max(difficulty - 15, 10)
        elif word_count >= 3:
            difficulty = max(difficulty - 10, 20)
        
    except Exception as e:
        print(f"Error calculating keyword difficulty: {e}")
    
    return difficulty


def get_related_keywords(db: Session, keyword: str, project_id: str, limit: int = 10) -> List[Dict]:
    """
    Get related keywords from existing project keywords
    """
    related = []
    
    try:
        # Find keywords with similar words in the same project
        words = set(keyword.lower().split())
        
        project_keywords = db.execute(
            select(Keyword)
            .where(Keyword.projectId == project_id)
            .limit(100)
        ).scalars().all()
        
        for kw in project_keywords:
            if kw.keyword.lower() != keyword.lower():
                kw_words = set(kw.keyword.lower().split())
                # Check if they share at least one word
                if words.intersection(kw_words):
                    related.append({
                        "keyword": kw.keyword,
                        "source": "project_keywords"
                    })
                    
                    if len(related) >= limit:
                        break
    except Exception as e:
        print(f"Error getting related keywords: {e}")
    
    return related


def estimate_search_volume(keyword: str) -> int:
    """
    Estimate search volume (mock data for now)
    In production, integrate with a free keyword API
    """
    # Simple heuristic based on keyword length and common words
    word_count = len(keyword.split())
    
    # Shorter keywords generally have higher volume
    base_volume = 10000 if word_count <= 2 else 5000
    base_volume = base_volume if word_count <= 3 else 2000
    base_volume = base_volume if word_count <= 4 else 500
    
    # Add some randomness for variety
    import random
    volume = base_volume + random.randint(-500, 2000)
    
    return max(volume, 100)


async def research_keyword(db: Session, keyword: str, project_id: str) -> Dict:
    """
    Main function to research a keyword - returns comprehensive data
    """
    # Get suggestions
    suggestions = await get_keyword_suggestions(keyword)
    
    # Calculate difficulty
    difficulty = calculate_keyword_difficulty(db, keyword, project_id)
    
    # Get related keywords
    related = get_related_keywords(db, keyword, project_id)
    
    # Estimate search volume
    volume = estimate_search_volume(keyword)
    
    return {
        "keyword": keyword,
        "difficulty": difficulty,
        "searchVolume": volume,
        "suggestions": suggestions[:10],
        "relatedKeywords": related[:5],
        "opportunityScore": calculate_opportunity_score(difficulty, volume)
    }


def calculate_opportunity_score(difficulty: int, volume: int) -> int:
    """
    Calculate opportunity score (0-100)
    Higher score = better opportunity
    """
    # Lower difficulty and higher volume = higher opportunity
    difficulty_factor = (100 - difficulty) / 100  # 0-1
    volume_factor = min(volume / 10000, 1)  # 0-1
    
    opportunity = (difficulty_factor * 0.6 + volume_factor * 0.4) * 100
    return int(opportunity)


def get_keyword_opportunities(db: Session, project_id: str, limit: int = 20) -> List[Dict]:
    """
    Get keyword opportunities for a project
    """
    opportunities = []
    
    try:
        # Get keywords with recent rank data
        subquery = select(
            RankResult.keywordText,
            func.max(RankResult.checkedAt).label('latest_check')
        ).where(
            RankResult.projectId == project_id
        ).group_by(RankResult.keywordText).subquery()
        
        latest_ranks = db.execute(
            select(RankResult)
            .where(RankResult.projectId == project_id)
            .where(RankResult.keywordText == subquery.c.keywordText)
            .where(RankResult.checkedAt == subquery.c.latest_check)
        ).scalars().all()
        
        for rank in latest_ranks:
            if rank.position and rank.position > 10 and rank.position <= 50:
                difficulty = calculate_keyword_difficulty(db, rank.keywordText, project_id)
                volume = estimate_search_volume(rank.keywordText)
                opportunity_score = calculate_opportunity_score(difficulty, volume)
                
                opportunities.append({
                    "keyword": rank.keywordText,
                    "currentPosition": rank.position,
                    "difficulty": difficulty,
                    "searchVolume": volume,
                    "opportunityScore": opportunity_score,
                    "url": rank.url
                })
        
        # Sort by opportunity score
        opportunities.sort(key=lambda x: x["opportunityScore"], reverse=True)
        
    except Exception as e:
        print(f"Error getting keyword opportunities: {e}")
    
    return opportunities[:limit]
