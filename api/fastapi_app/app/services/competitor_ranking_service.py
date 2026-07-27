"""
Competitor Ranking Tracking Service
Tracks competitor keyword rankings and provides comparison data
"""
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.errors import ApiError
from app.db.models import Competitor, Project, Keyword, RankResult, CompetitorRank
from app.services.mock_data_service import MockDataGenerator
from app.utils.serializers import model_to_dict


def track_competitor_rankings(
    db: Session, 
    user_id: str, 
    project_id: str,
    use_mock: bool = True
) -> dict:
    """
    Track rankings for all competitors in a project
    Uses mock data if use_mock=True, otherwise would call DataForSEO
    """
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        raise ApiError(404, "Project not found")
    
    competitors = db.scalars(
        select(Competitor).where(Competitor.projectId == project_id)
    ).all()
    
    if not competitors:
        raise ApiError(400, "No competitors found for this project")
    
    keywords = db.scalars(
        select(Keyword).where(Keyword.projectId == project_id)
    ).all()
    
    if not keywords:
        raise ApiError(400, "No keywords found for this project")
    
    tracked_count = 0
    
    for competitor in competitors:
        for keyword in keywords:
            if use_mock:
                mock_data = MockDataGenerator.generate_mock_competitor_rank(
                    competitor.domain, 
                    keyword.keyword
                )
                
                competitor_rank = CompetitorRank(
                    projectId=project_id,
                    competitorId=competitor.id,
                    keywordText=mock_data["keyword"],
                    position=mock_data["position"],
                )
                db.add(competitor_rank)
                tracked_count += 1
            else:
                pass
    
    db.commit()
    
    return {
        "tracked": True,
        "competitors_count": len(competitors),
        "keywords_count": len(keywords),
        "total_rankings_tracked": tracked_count
    }


def get_competitor_rank_comparison(
    db: Session, 
    user_id: str, 
    project_id: str,
    keyword_id: Optional[str] = None
) -> List[dict]:
    """
    Get ranking comparison between your domain and competitors
    """
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        raise ApiError(404, "Project not found")
    
    competitors = db.scalars(
        select(Competitor).where(Competitor.projectId == project_id)
    ).all()
    
    your_rankings = db.scalars(
        select(RankResult)
        .where(RankResult.projectId == project_id)
        .order_by(desc(RankResult.checkedAt))
    ).all()
    
    your_rank_map = {}
    for rank in your_rankings:
        if rank.keywordText not in your_rank_map:
            your_rank_map[rank.keywordText] = rank.position
    
    competitor_rank_rows = db.scalars(
        select(CompetitorRank)
        .where(CompetitorRank.projectId == project_id)
        .order_by(desc(CompetitorRank.checkedAt))
    ).all()
    
    comp_rank_map = {}
    for cr in competitor_rank_rows:
        if cr.competitorId not in comp_rank_map:
            comp_rank_map[cr.competitorId] = {}
        if cr.keywordText not in comp_rank_map[cr.competitorId]:
            comp_rank_map[cr.competitorId][cr.keywordText] = cr.position
    
    comparison = []
    
    for competitor in competitors:
        competitor_ranks = []
        comp_keyword_map = comp_rank_map.get(competitor.id, {})
        
        for keyword_text, your_position in your_rank_map.items():
            competitor_position = comp_keyword_map.get(keyword_text)
            competitor_ranks.append({
                "keyword": keyword_text,
                "your_position": your_position,
                "competitor_position": competitor_position,
                "gap": competitor_position - your_position if your_position and competitor_position else None
            })
        
        if competitor_ranks:
            shared_keywords = len([r for r in competitor_ranks if r["your_position"] and r["competitor_position"]])
            avg_gap = sum(r["gap"] for r in competitor_ranks if r["gap"] is not None) / shared_keywords if shared_keywords > 0 else 0
            
            comparison.append({
                "competitor_id": competitor.id,
                "competitor_name": competitor.name,
                "competitor_domain": competitor.domain,
                "shared_keywords": shared_keywords,
                "average_gap": round(avg_gap, 1),
                "rankings": competitor_ranks[:10]
            })
    
    return comparison


def get_keyword_opportunity_analysis(
    db: Session, 
    user_id: str, 
    project_id: str
) -> List[dict]:
    """
    Analyze keyword opportunities - keywords where competitors outrank you
    """
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        raise ApiError(404, "Project not found")
    
    competitors = db.scalars(
        select(Competitor).where(Competitor.projectId == project_id)
    ).all()
    
    your_rankings = db.scalars(
        select(RankResult)
        .where(RankResult.projectId == project_id)
        .order_by(desc(RankResult.checkedAt))
    ).all()
    
    your_rank_map = {}
    for rank in your_rankings:
        if rank.keywordText not in your_rank_map:
            your_rank_map[rank.keywordText] = rank.position
    
    competitor_rank_rows = db.scalars(
        select(CompetitorRank)
        .where(CompetitorRank.projectId == project_id)
        .order_by(desc(CompetitorRank.checkedAt))
    ).all()
    
    comp_rank_map = {}
    for cr in competitor_rank_rows:
        if cr.competitorId not in comp_rank_map:
            comp_rank_map[cr.competitorId] = {}
        if cr.keywordText not in comp_rank_map[cr.competitorId]:
            comp_rank_map[cr.competitorId][cr.keywordText] = cr.position
    
    opportunities = []
    
    for keyword_text, your_position in your_rank_map.items():
        if not your_position or your_position > 20:
            continue
        
        competitor_positions = []
        for competitor in competitors:
            comp_pos = comp_rank_map.get(competitor.id, {}).get(keyword_text)
            if comp_pos and comp_pos < your_position:
                competitor_positions.append({
                    "competitor": competitor.name,
                    "position": comp_pos
                })
        
        if competitor_positions:
            opportunities.append({
                "keyword": keyword_text,
                "your_position": your_position,
                "competitors_outranking": competitor_positions,
                "opportunity_score": len(competitor_positions) * 10
            })
    
    opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)
    
    return opportunities[:20]


def get_competitor_rank_history(
    db: Session, 
    user_id: str, 
    project_id: str,
    competitor_id: str,
    days: int = 30
) -> List[dict]:
    """
    Get historical ranking data for a specific competitor
    """
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        raise ApiError(404, "Project not found")
    
    competitor = db.scalar(
        select(Competitor).where(
            Competitor.id == competitor_id, 
            Competitor.projectId == project_id
        )
    )
    if not competitor:
        raise ApiError(404, "Competitor not found")
    
    keywords = db.scalars(
        select(Keyword).where(Keyword.projectId == project_id)
    ).all()
    
    history = []
    
    for keyword in keywords[:10]:
        keyword_history = {
            "keyword": keyword.keyword,
            "positions": []
        }
        
        rank_rows = db.scalars(
            select(CompetitorRank)
            .where(
                CompetitorRank.projectId == project_id,
                CompetitorRank.competitorId == competitor_id,
                CompetitorRank.keywordText == keyword.keyword,
            )
            .order_by(CompetitorRank.checkedAt)
        ).all()
        
        for rank_row in rank_rows:
            keyword_history["positions"].append({
                "date": rank_row.checkedAt.strftime("%Y-%m-%d"),
                "position": rank_row.position
            })
        
        history.append(keyword_history)
    
    return history
