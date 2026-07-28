from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.db.models import Project, Keyword, RankResult, User
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def get_agency_dashboard_data(db: Session, user_id: str) -> Dict:
    """
    Get aggregated dashboard data for agency view (all projects)
    """
    try:
        # Get all projects for user
        projects = db.execute(
            select(Project)
            .where(Project.userId == user_id)
        ).scalars().all()
        
        if not projects:
            return {
                "totalProjects": 0,
                "totalKeywords": 0,
                "averageRank": 0,
                "topPerformers": [],
                "recentActivity": [],
                "projectBreakdown": []
            }
        
        project_ids = [p.id for p in projects]
        
        # Total keywords across all projects
        total_keywords = db.execute(
            select(func.count()).select_from(Keyword).where(Keyword.projectId.in_(project_ids))
        ).scalar() or 0
        
        # Get latest rank results for average calculation
        subquery = select(
            RankResult.keywordText,
            func.max(RankResult.checkedAt).label('latest_check')
        ).where(
            RankResult.projectId.in_(project_ids)
        ).group_by(RankResult.keywordText).subquery()
        
        latest_ranks = db.execute(
            select(RankResult)
            .where(RankResult.projectId.in_(project_ids))
            .where(RankResult.keywordText == subquery.c.keywordText)
            .where(RankResult.checkedAt == subquery.c.latest_check)
            .where(RankResult.position.isnot(None))
        ).scalars().all()
        
        # Calculate average rank
        if latest_ranks:
            avg_rank = sum(r.position for r in latest_ranks) / len(latest_ranks)
        else:
            avg_rank = 0
        
        # Project breakdown
        project_breakdown = []
        for project in projects:
            kw_count = db.execute(
                select(func.count()).select_from(Keyword).where(Keyword.projectId == project.id)
            ).scalar() or 0
            
            # Get average rank for this project
            project_ranks = db.execute(
                select(RankResult)
                .where(RankResult.projectId == project.id)
                .where(RankResult.keywordText == subquery.c.keywordText)
                .where(RankResult.checkedAt == subquery.c.latest_check)
                .where(RankResult.position.isnot(None))
            ).scalars().all()
            
            project_avg = sum(r.position for r in project_ranks) / len(project_ranks) if project_ranks else 0
            
            project_breakdown.append({
                "projectId": project.id,
                "projectName": project.name,
                "domain": project.domain,
                "keywordCount": kw_count,
                "averageRank": round(project_avg, 1),
                "createdAt": project.createdAt.isoformat()
            })
        
        # Sort by keyword count
        project_breakdown.sort(key=lambda x: x["keywordCount"], reverse=True)
        
        # Top performers (projects with best average rank)
        top_performers = sorted(project_breakdown, key=lambda x: x["averageRank"])[:5]
        
        # Recent activity (latest rank checks)
        recent_activity = db.execute(
            select(RankResult, Project)
            .join(Project, RankResult.projectId == Project.id)
            .where(Project.userId == user_id)
            .order_by(RankResult.checkedAt.desc())
            .limit(10)
        ).all()
        
        activity_list = [
            {
                "projectName": project.name,
                "keyword": rank.keywordText,
                "position": rank.position,
                "checkedAt": rank.checkedAt.isoformat()
            }
            for rank, project in recent_activity
        ]
        
        return {
            "totalProjects": len(projects),
            "totalKeywords": total_keywords,
            "averageRank": round(avg_rank, 1),
            "topPerformers": top_performers,
            "recentActivity": activity_list,
            "projectBreakdown": project_breakdown
        }
        
    except Exception as e:
        logger.error(f"Error getting agency dashboard data: {e}")
        return {
            "totalProjects": 0,
            "totalKeywords": 0,
            "averageRank": 0,
            "topPerformers": [],
            "recentActivity": [],
            "projectBreakdown": []
        }


def get_project_comparison(db: Session, user_id: str) -> List[Dict]:
    """
    Get comparison data across all projects
    """
    try:
        projects = db.execute(
            select(Project)
            .where(Project.userId == user_id)
        ).scalars().all()
        
        comparison = []
        
        for project in projects:
            # Get keyword count
            kw_count = db.execute(
                select(func.count()).select_from(Keyword).where(Keyword.projectId == project.id)
            ).scalar() or 0
            
            # Get positions in top 10
            subquery = select(
                RankResult.keywordText,
                func.max(RankResult.checkedAt).label('latest_check')
            ).where(
                RankResult.projectId == project.id
            ).group_by(RankResult.keywordText).subquery()
            
            top_10_count = db.execute(
                select(func.count())
                .select_from(RankResult)
                .where(RankResult.projectId == project.id)
                .where(RankResult.keywordText == subquery.c.keywordText)
                .where(RankResult.checkedAt == subquery.c.latest_check)
                .where(RankResult.position <= 10)
            ).scalar() or 0
            
            # Get positions improved (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            improved_count = db.execute(
                select(func.count())
                .select_from(RankResult)
                .where(RankResult.projectId == project.id)
                .where(RankResult.checkedAt >= thirty_days_ago)
                .where(RankResult.position <= 10)
            ).scalar() or 0
            
            comparison.append({
                "projectId": project.id,
                "projectName": project.name,
                "domain": project.domain,
                "keywordCount": kw_count,
                "top10Count": top_10_count,
                "improvedCount": improved_count,
                "top10Percentage": round((top_10_count / kw_count * 100) if kw_count > 0 else 0, 1)
            })
        
        # Sort by top 10 percentage
        comparison.sort(key=lambda x: x["top10Percentage"], reverse=True)
        
        return comparison
        
    except Exception as e:
        logger.error(f"Error getting project comparison: {e}")
        return []


def calculate_roi_metrics(db: Session, user_id: str) -> Dict:
    """
    Calculate ROI metrics for agency dashboard
    """
    try:
        projects = db.execute(
            select(Project)
            .where(Project.userId == user_id)
        ).scalars().all()
        
        total_keywords = 0
        total_top_10 = 0
        total_top_3 = 0
        
        for project in projects:
            # Get keyword count
            kw_count = db.execute(
                select(func.count()).select_from(Keyword).where(Keyword.projectId == project.id)
            ).scalar() or 0
            
            total_keywords += kw_count
            
            # Get latest ranks
            subquery = select(
                RankResult.keywordText,
                func.max(RankResult.checkedAt).label('latest_check')
            ).where(
                RankResult.projectId == project.id
            ).group_by(RankResult.keywordText).subquery()
            
            ranks = db.execute(
                select(RankResult)
                .where(RankResult.projectId == project.id)
                .where(RankResult.keywordText == subquery.c.keywordText)
                .where(RankResult.checkedAt == subquery.c.latest_check)
                .where(RankResult.position.isnot(None))
            ).scalars().all()
            
            for rank in ranks:
                if rank.position <= 10:
                    total_top_10 += 1
                if rank.position <= 3:
                    total_top_3 += 1
        
        return {
            "totalKeywords": total_keywords,
            "totalTop10": total_top_10,
            "totalTop3": total_top_3,
            "top10Percentage": round((total_top_10 / total_keywords * 100) if total_keywords > 0 else 0, 1),
            "top3Percentage": round((total_top_3 / total_keywords * 100) if total_keywords > 0 else 0, 1),
            "projectCount": len(projects)
        }
        
    except Exception as e:
        logger.error(f"Error calculating ROI metrics: {e}")
        return {
            "totalKeywords": 0,
            "totalTop10": 0,
            "totalTop3": 0,
            "top10Percentage": 0,
            "top3Percentage": 0,
            "projectCount": 0
        }
