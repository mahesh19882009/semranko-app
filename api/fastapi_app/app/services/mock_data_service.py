"""
Mock Data Service for RankWatch Clone
Generates realistic SEO data without requiring DataForSEO API
All data is deterministic based on project/keyword IDs for consistency
"""
import random
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, delete
from app.db.models import Keyword, Project, RankResult, Competitor, Backlink
from app.utils.serializers import model_to_dict


class MockDataGenerator:
    """Generates mock SEO data for development without external APIs"""
    
    # Base positions for deterministic randomness
    BASE_POSITIONS = [1, 3, 5, 7, 10, 12, 15, 18, 20, 25, 30, 35, 40, 50, 60, 75, 90]
    
    # Sample domains for backlinks
    SAMPLE_DOMAINS = [
        "blog.example.com", "news.example.com", "tech.example.com",
        "review.example.com", "directory.example.com", "forum.example.com"
    ]
    
    # Sample anchor texts
    SAMPLE_ANCHORS = [
        "best seo tools", "rank tracking", "keyword research",
        "seo software", "rank checker", "seo analytics"
    ]
    
    @classmethod
    def _seed_from_string(cls, string: str) -> int:
        """Generate deterministic seed from string"""
        return sum(ord(c) for c in string)
    
    @classmethod
    def _deterministic_random(cls, seed: int, max_val: int) -> int:
        """Generate deterministic random number"""
        random.seed(seed)
        return random.randint(0, max_val)
    
    @classmethod
    def generate_mock_rank(cls, keyword: str, domain: str, date: datetime = None) -> dict:
        """Generate mock ranking data for a keyword"""
        if date is None:
            date = datetime.utcnow()
        
        seed = cls._seed_from_string(f"{keyword}_{domain}_{date.strftime('%Y-%m-%d')}")
        base_position = cls.BASE_POSITIONS[seed % len(cls.BASE_POSITIONS)]
        
        # Add some daily variation
        day_variation = cls._deterministic_random(seed + 1, 5) - 2
        position = max(1, min(100, base_position + day_variation))
        
        # Sometimes not found (position 101+)
        if cls._deterministic_random(seed + 2, 10) == 0:
            position = 101
        
        return {
            "keyword": keyword,
            "domain": domain,
            "position": position if position <= 100 else None,
            "url": f"https://{domain}/page-{seed % 10}",
            "device": "desktop",
            "location": "India",
            "checkedAt": date.isoformat()
        }
    
    @classmethod
    def generate_mock_rank_history(cls, keyword: str, domain: str, days: int = 30) -> List[dict]:
        """Generate historical ranking data for a keyword"""
        history = []
        base_date = datetime.utcnow()
        
        for i in range(days):
            date = base_date - timedelta(days=days - i)
            rank_data = cls.generate_mock_rank(keyword, domain, date)
            history.append(rank_data)
        
        return history
    
    @classmethod
    def generate_mock_competitor_rank(cls, competitor_domain: str, keyword: str, date: datetime = None) -> dict:
        """Generate mock competitor ranking data"""
        if date is None:
            date = datetime.utcnow()
        
        seed = cls._seed_from_string(f"{competitor_domain}_{keyword}_{date.strftime('%Y-%m-%d')}")
        base_position = cls.BASE_POSITIONS[(seed + 5) % len(cls.BASE_POSITIONS)]
        
        # Competitors often rank higher
        position = max(1, base_position - 3)
        
        return {
            "keyword": keyword,
            "domain": competitor_domain,
            "position": position,
            "url": f"https://{competitor_domain}/page",
            "device": "desktop",
            "location": "India",
            "checkedAt": date.isoformat()
        }
    
    @classmethod
    def generate_mock_backlinks(cls, domain: str, count: int = 50) -> List[dict]:
        """Generate mock backlink data"""
        backlinks = []
        seed = cls._seed_from_string(domain)
        
        for i in range(count):
            source_domain = cls.SAMPLE_DOMAINS[(seed + i) % len(cls.SAMPLE_DOMAINS)]
            anchor = cls.SAMPLE_ANCHORS[(seed + i + 3) % len(cls.SAMPLE_ANCHORS)]
            domain_rank = 30 + cls._deterministic_random(seed + i * 7, 50)
            
            backlinks.append({
                "sourceUrl": f"https://{source_domain}/article-{i}",
                "sourceDomain": source_domain,
                "anchor": anchor,
                "domainRank": domain_rank,
                "firstSeen": (datetime.utcnow() - timedelta(days=random.randint(1, 365))).isoformat()
            })
        
        return backlinks
    
    @classmethod
    def generate_mock_serp_features(cls, keyword: str, domain: str) -> dict:
        """Generate mock SERP feature data (featured snippets, etc.)"""
        seed = cls._seed_from_string(keyword)
        
        return {
            "keyword": keyword,
            "hasFeaturedSnippet": cls._deterministic_random(seed, 10) == 0,
            "hasLocalPack": cls._deterministic_random(seed + 1, 15) == 0,
            "hasPeopleAlsoAsk": cls._deterministic_random(seed + 2, 5) == 0,
            "hasRelatedSearches": cls._deterministic_random(seed + 3, 3) == 0,
        }


def populate_mock_rank_results(db: Session, project_id: str, days: int = 30) -> int:
    """Populate mock rank results for a project's keywords"""
    project = db.scalar(select(Project).where(Project.id == project_id))
    if not project:
        return 0
    
    keywords = db.scalars(select(Keyword).where(Keyword.projectId == project_id)).all()
    if not keywords:
        return 0
    
    created_count = 0
    base_date = datetime.utcnow()
    
    for keyword in keywords:
        # Generate historical data
        for day_offset in range(days):
            check_date = base_date - timedelta(days=days - day_offset)
            
            # Check if rank result already exists for this date
            existing = db.scalar(
                select(RankResult).where(
                    RankResult.projectId == project_id,
                    RankResult.keywordText == keyword.keyword,
                    RankResult.checkedAt >= check_date.replace(hour=0, minute=0, second=0),
                    RankResult.checkedAt < check_date.replace(hour=23, minute=59, second=59)
                )
            )
            
            if existing:
                continue
            
            mock_data = MockDataGenerator.generate_mock_rank(
                keyword.keyword, 
                project.domain, 
                check_date
            )
            
            rank_result = RankResult(
                projectId=project_id,
                keywordText=mock_data["keyword"],
                position=mock_data["position"],
                url=mock_data["url"],
                device=mock_data["device"],
                location=mock_data["location"],
                checkedAt=check_date,
                keywordId=keyword.id
            )
            
            db.add(rank_result)
            created_count += 1
    
    db.commit()
    return created_count


def populate_mock_backlinks(db: Session, project_id: str, count: int = 50) -> int:
    """Populate mock backlinks for a project"""
    project = db.scalar(select(Project).where(Project.id == project_id))
    if not project:
        return 0
    
    db.execute(delete(Backlink).where(Backlink.projectId == project_id))
    
    mock_backlinks = MockDataGenerator.generate_mock_backlinks(project.domain, count)
    
    for bl_data in mock_backlinks:
        backlink = Backlink(
            projectId=project_id,
            sourceUrl=bl_data["sourceUrl"],
            sourceDomain=bl_data["sourceDomain"],
            anchor=bl_data["anchor"],
            domainRank=bl_data["domainRank"],
            firstSeen=datetime.fromisoformat(bl_data["firstSeen"]),
            checkedAt=datetime.utcnow()
        )
        db.add(backlink)
    
    db.commit()
    return len(mock_backlinks)


def get_mock_competitor_comparison(db: Session, project_id: str) -> List[dict]:
    """Generate mock competitor ranking comparison data"""
    project = db.scalar(select(Project).where(Project.id == project_id))
    if not project:
        return []
    
    competitors = db.scalars(select(Competitor).where(Competitor.projectId == project_id)).all()
    keywords = db.scalars(select(Keyword).where(Keyword.projectId == project_id)).all()
    
    comparison = []
    
    for competitor in competitors:
        shared_keywords = 0
        overlap_positions = []
        
        for keyword in keywords[:10]:  # Limit to 10 keywords for performance
            your_rank = MockDataGenerator.generate_mock_rank(keyword.keyword, project.domain)
            comp_rank = MockDataGenerator.generate_mock_competitor_rank(competitor.domain, keyword.keyword)
            
            if your_rank.get("position") and comp_rank.get("position"):
                shared_keywords += 1
                overlap_positions.append({
                    "keyword": keyword.keyword,
                    "yourPosition": your_rank["position"],
                    "competitorPosition": comp_rank["position"],
                    "gap": comp_rank["position"] - your_rank["position"]
                })
        
        if shared_keywords > 0:
            avg_gap = sum(p["gap"] for p in overlap_positions) / len(overlap_positions)
            overlap_pct = int((shared_keywords / min(len(keywords), 10)) * 100)
            
            comparison.append({
                "competitorId": competitor.id,
                "competitorDomain": competitor.domain,
                "competitorName": competitor.name,
                "sharedKeywords": shared_keywords,
                "overlapPercentage": overlap_pct,
                "averageGap": round(avg_gap, 1),
                "positions": overlap_positions[:5]  # Top 5 positions
            })
    
    return comparison
