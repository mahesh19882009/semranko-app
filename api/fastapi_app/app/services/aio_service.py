import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import AIOTracking, Keyword, Project, User
from app.services.dataforseo_client import DataForSEOClient
from app.services.cache_service import get_cached, set_cached
from app.core.errors import ApiError

logger = logging.getLogger(__name__)


def track_aio_for_project(db: Session, user_id: str, project_id: str) -> dict:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    keywords = db.scalars(select(Keyword).where(Keyword.projectId == project_id)).all()
    if not keywords:
        return {"tracked": 0}

    location = keywords[0].location or "India"
    tracked = 0

    keywords_to_fetch = []
    for keyword in keywords:
        cached = get_cached("aio_tracking", (project_id, keyword.keyword))
        if cached:
            tracked += 1
            continue

        keywords_to_fetch.append(keyword)

    if keywords_to_fetch:
        serp_map = DataForSEOClient.get_serp_data_batch(
            [{"keyword": kw.keyword, "location": location, "device": kw.device or "desktop"} for kw in keywords_to_fetch],
            location,
            result_type="advanced",
        )

        for keyword in keywords_to_fetch:
            serp_data = serp_map.get(keyword.keyword)
            if not serp_data:
                continue

            has_ai_overview = bool(serp_data.get("ai_overview"))
            ai_overview_text = None
            cited_domains = {}

            if serp_data.get("ai_overview"):
                ai_item = serp_data["ai_overview"]
                ai_overview_text = ai_item.get("description") or ai_item.get("text") or ai_item.get("content")
                cited_domains = serp_data.get("cited_domains", {})

            existing = db.scalar(
                select(AIOTracking).where(
                    AIOTracking.projectId == project_id,
                    AIOTracking.keywordText == keyword.keyword,
                )
            )
            if existing:
                existing.hasAIOverview = has_ai_overview
                existing.aiOverviewText = ai_overview_text
                existing.citedDomains = cited_domains or None
                existing.checkedAt = datetime.utcnow()
            else:
                db.add(
                    AIOTracking(
                        projectId=project_id,
                        keywordText=keyword.keyword,
                        hasAIOverview=has_ai_overview,
                        aiOverviewText=ai_overview_text,
                        citedDomains=cited_domains or None,
                    )
                )
            tracked += 1
            set_cached("aio_tracking", (project_id, keyword.keyword), {"hasAIOverview": has_ai_overview, "cited_domains": cited_domains}, ttl_seconds=24 * 60 * 60)

    db.commit()
    return {"tracked": tracked}


def get_aio_dashboard(db: Session, user_id: str, project_id: str) -> dict:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    tracks = db.scalars(select(AIOTracking).where(AIOTracking.projectId == project_id)).all()
    keywords_with_aio = [t for t in tracks if t.hasAIOverview]
    keywords_without_aio = [t for t in tracks if not t.hasAIOverview]

    return {
        "totalKeywords": len(tracks),
        "withAIOverview": len(keywords_with_aio),
        "withoutAIOverview": len(keywords_without_aio),
        "keywords": [
            {
                "keyword": t.keywordText,
                "hasAIOverview": t.hasAIOverview,
                "aiOverviewText": t.aiOverviewText,
                "citedDomains": t.citedDomains,
                "checkedAt": t.checkedAt.isoformat() if t.checkedAt else None,
            }
            for t in tracks
        ],
    }


def get_citation_share_of_voice(db: Session, user_id: str, project_id: str) -> list[dict]:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    tracks = db.scalars(select(AIOTracking).where(AIOTracking.projectId == project_id, AIOTracking.hasAIOverview == True)).all()
    domain_counts = {}
    for track in tracks:
        cited = track.citedDomains or {}
        for domain, count in cited.items():
            domain_counts[domain] = domain_counts.get(domain, 0) + count

    total = sum(domain_counts.values()) or 1
    results = []
    for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
        results.append({"domain": domain, "count": count, "percentage": round((count / total) * 100, 2)})
    return results
