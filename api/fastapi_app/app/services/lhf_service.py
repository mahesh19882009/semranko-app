from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from app.db.models import Keyword, RankResult, Project


def calculate_lhf_score(rank: int, difficulty: int, position_change: int = 0) -> int:
    """
    Calculate Low Hanging Fruit score (0-100)
    Higher score = easier to improve
    
    Factors:
    - Current position (closer to top 10 = higher score)
    - Difficulty (lower = higher score)
    - Recent position change (positive momentum = higher score)
    """
    # Position factor: 11-20 gets highest score
    if rank <= 10:
        position_factor = 30
    elif rank <= 20:
        position_factor = 70
    elif rank <= 30:
        position_factor = 50
    elif rank <= 50:
        position_factor = 30
    else:
        position_factor = 10
    
    # Difficulty factor: lower difficulty = higher score
    difficulty_factor = max(0, 100 - difficulty)
    
    # Momentum factor: positive change = bonus
    momentum_factor = min(position_change * 2, 20) if position_change > 0 else 0
    
    # Weighted score
    score = (position_factor * 0.5) + (difficulty_factor * 0.4) + (momentum_factor * 0.1)
    
    return int(min(score, 100))


def get_position_change(db: Session, keyword: str, project_id: str) -> int:
    """
    Calculate position change between latest and previous rank check
    """
    try:
        # Get latest 2 rank results
        results = db.execute(
            select(RankResult)
            .where(RankResult.keywordText == keyword)
            .where(RankResult.projectId == project_id)
            .where(RankResult.position.isnot(None))
            .order_by(RankResult.checkedAt.desc())
            .limit(2)
        ).scalars().all()
        
        if len(results) >= 2:
            latest = results[0].position
            previous = results[1].position
            return previous - latest  # Positive = improved
    except Exception as e:
        print(f"Error calculating position change: {e}")
    
    return 0


def get_low_hanging_fruits(db: Session, project_id: str, limit: int = 20) -> List[Dict]:
    """
    Get low hanging fruit opportunities for a project
    Focuses on keywords ranking 11-50 with improvement potential
    """
    lhf_list = []
    
    try:
        # Get latest rank results for the project
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
            .where(RankResult.position.isnot(None))
            .where(RankResult.position > 10)
            .where(RankResult.position <= 50)
        ).scalars().all()
        
        for rank in latest_ranks:
            # Calculate position change
            position_change = get_position_change(db, rank.keywordText, project_id)
            
            # Calculate difficulty (reuse logic from keyword research)
            difficulty = calculate_keyword_difficulty(rank.keywordText, rank.position)
            
            # Calculate LHF score
            lhf_score = calculate_lhf_score(rank.position, difficulty, position_change)
            
            # Only include if it's a good opportunity
            if lhf_score >= 40:
                lhf_list.append({
                    "keyword": rank.keywordText,
                    "currentPosition": rank.position,
                    "previousPosition": rank.position - position_change if position_change != 0 else None,
                    "positionChange": position_change,
                    "difficulty": difficulty,
                    "lhfScore": lhf_score,
                    "url": rank.url,
                    "category": categorize_lhf(lhf_score, rank.position)
                })
        
        # Sort by LHF score (highest first)
        lhf_list.sort(key=lambda x: x["lhfScore"], reverse=True)
        
    except Exception as e:
        print(f"Error getting low hanging fruits: {e}")
    
    return lhf_list[:limit]


def calculate_keyword_difficulty(keyword: str, current_position: int) -> int:
    """
    Simple difficulty calculation based on position and keyword characteristics
    """
    difficulty = 50  # Default
    
    # Adjust based on current position
    if current_position <= 15:
        difficulty = 30
    elif current_position <= 25:
        difficulty = 45
    elif current_position <= 35:
        difficulty = 55
    else:
        difficulty = 65
    
    # Adjust based on keyword length
    word_count = len(keyword.split())
    if word_count >= 4:
        difficulty = max(difficulty - 15, 20)
    elif word_count >= 3:
        difficulty = max(difficulty - 10, 30)
    
    return difficulty


def categorize_lhf(score: int, position: int) -> str:
    """
    Categorize the low hanging fruit opportunity
    """
    if score >= 70:
        return "Quick Win"
    elif score >= 50:
        return "High Potential"
    elif position <= 20:
        return "Near Top 10"
    else:
        return "Opportunity"


def get_lhf_summary(db: Session, project_id: str) -> Dict:
    """
    Get summary statistics for low hanging fruits
    """
    try:
        lhf_items = get_low_hanging_fruits(db, project_id, limit=100)
        
        quick_wins = len([x for x in lhf_items if x["category"] == "Quick Win"])
        high_potential = len([x for x in lhf_items if x["category"] == "High Potential"])
        total_opportunities = len(lhf_items)
        
        avg_score = sum(x["lhfScore"] for x in lhf_items) / total_opportunities if total_opportunities > 0 else 0
        
        return {
            "totalOpportunities": total_opportunities,
            "quickWins": quick_wins,
            "highPotential": high_potential,
            "averageLHFScore": round(avg_score, 1),
            "topOpportunity": lhf_items[0] if lhf_items else None
        }
    except Exception as e:
        print(f"Error getting LHF summary: {e}")
        return {
            "totalOpportunities": 0,
            "quickWins": 0,
            "highPotential": 0,
            "averageLHFScore": 0,
            "topOpportunity": None
        }
