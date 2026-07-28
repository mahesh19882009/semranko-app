from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.db.models import SerpFeature, RankResult, Project


SERP_FEATURE_TYPES = [
    "featured_snippet",
    "local_pack",
    "sitelinks",
    "knowledge_panel",
    "image_pack",
    "video_pack",
    "people_also_ask",
    "related_searches",
    "top_stories",
]


def track_serp_feature(
    db: Session,
    project_id: str,
    keyword: str,
    feature_type: str,
    is_present: bool,
    position: Optional[int] = None,
    url: Optional[str] = None
) -> SerpFeature:
    """
    Track a SERP feature for a keyword
    """
    # Check if feature already exists
    existing = db.execute(
        select(SerpFeature)
        .where(SerpFeature.projectId == project_id)
        .where(SerpFeature.keywordText == keyword)
        .where(SerpFeature.featureType == feature_type)
    ).scalar_one_or_none()
    
    if existing:
        # Update existing record
        existing.isPresent = is_present
        existing.position = position
        existing.url = url
        db.add(existing)
        db.commit()
        return existing
    else:
        # Create new record
        feature = SerpFeature(
            projectId=project_id,
            keywordText=keyword,
            featureType=feature_type,
            isPresent=is_present,
            position=position,
            url=url
        )
        db.add(feature)
        db.commit()
        return feature


def get_serp_features_for_keyword(db: Session, project_id: str, keyword: str) -> List[Dict]:
    """
    Get all SERP features for a specific keyword
    """
    features = db.execute(
        select(SerpFeature)
        .where(SerpFeature.projectId == project_id)
        .where(SerpFeature.keywordText == keyword)
        .order_by(SerpFeature.checkedAt.desc())
    ).scalars().all()
    
    return [
        {
            "featureType": f.featureType,
            "isPresent": f.isPresent,
            "position": f.position,
            "url": f.url,
            "checkedAt": f.checkedAt.isoformat()
        }
        for f in features
    ]


def get_serp_features_summary(db: Session, project_id: str) -> Dict:
    """
    Get summary of SERP features for a project
    """
    try:
        # Count features by type
        feature_counts = db.execute(
            select(
                SerpFeature.featureType,
                func.count().label('count')
            )
            .where(SerpFeature.projectId == project_id)
            .where(SerpFeature.isPresent == True)
            .group_by(SerpFeature.featureType)
        ).all()
        
        summary = {
            "totalFeatures": sum(count for _, count in feature_counts),
            "byType": {feature_type: count for feature_type, count in feature_counts},
            "keywordsWithFeatures": 0
        }
        
        # Count unique keywords with features
        unique_keywords = db.execute(
            select(func.count(func.distinct(SerpFeature.keywordText)))
            .where(SerpFeature.projectId == project_id)
            .where(SerpFeature.isPresent == True)
        ).scalar()
        
        summary["keywordsWithFeatures"] = unique_keywords or 0
        
        return summary
    except Exception as e:
        print(f"Error getting SERP features summary: {e}")
        return {
            "totalFeatures": 0,
            "byType": {},
            "keywordsWithFeatures": 0
        }


def get_keywords_with_serp_features(db: Session, project_id: str, limit: int = 50) -> List[Dict]:
    """
    Get keywords that have SERP features
    """
    try:
        # Get keywords with features
        subquery = select(
            SerpFeature.keywordText,
            func.count().label('feature_count')
        ).where(
            SerpFeature.projectId == project_id
        ).where(
            SerpFeature.isPresent == True
        ).group_by(SerpFeature.keywordText).subquery()
        
        results = db.execute(
            select(SerpFeature.keywordText, subquery.c.feature_count)
            .where(SerpFeature.projectId == project_id)
            .where(SerpFeature.keywordText == subquery.c.keywordText)
            .distinct()
            .order_by(subquery.c.feature_count.desc())
            .limit(limit)
        ).all()
        
        return [
            {
                "keyword": keyword,
                "featureCount": count
            }
            for keyword, count in results
        ]
    except Exception as e:
        print(f"Error getting keywords with SERP features: {e}")
        return []


def mock_extract_serp_features_from_rank_result(rank_result: RankResult) -> List[Dict]:
    """
    Mock function to extract SERP features from rank result
    In production, this would parse actual SERP data from DataForSEO
    """
    features = []
    
    # Mock logic - in production, parse actual SERP HTML/JSON
    if rank_result.position and rank_result.position <= 3:
        # Top 3 positions might have sitelinks
        features.append({
            "featureType": "sitelinks",
            "isPresent": True,
            "position": rank_result.position,
            "url": rank_result.url
        })
    
    # Randomly assign featured snippets for demo
    import random
    if random.random() < 0.1:  # 10% chance
        features.append({
            "featureType": "featured_snippet",
            "isPresent": True,
            "position": 0,  # Featured snippet is position 0
            "url": rank_result.url
        })
    
    return features


def sync_serp_features_from_rank_results(db: Session, project_id: str) -> int:
    """
    Sync SERP features from latest rank results
    Returns number of features synced
    """
    try:
        # Get latest rank results
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
        
        synced_count = 0
        
        for rank in latest_ranks:
            # Extract features (mock for now)
            features = mock_extract_serp_features_from_rank_result(rank)
            
            for feature_data in features:
                track_serp_feature(
                    db,
                    project_id,
                    rank.keywordText,
                    feature_data["featureType"],
                    feature_data["isPresent"],
                    feature_data.get("position"),
                    feature_data.get("url")
                )
                synced_count += 1
        
        return synced_count
    except Exception as e:
        print(f"Error syncing SERP features: {e}")
        return 0
