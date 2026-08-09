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


def ensure_aio_tracking(db: Session, project_id: str, keyword_text: str, ai_badge: str | None) -> None:
    if not ai_badge:
        return
    existing = db.scalar(
        select(AIOTracking).where(
            AIOTracking.projectId == project_id,
            AIOTracking.keywordText == keyword_text,
        )
    )
    if not existing:
        db.add(
            AIOTracking(
                projectId=project_id,
                keywordText=keyword_text,
                hasAIOverview=True,
            )
        )


def track_aio_for_project(db: Session, user_id: str, project_id: str) -> dict:
    project = db.scalar(select(Project).where(Project.id == project_id))
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
            ai_overview_title = None
            ai_overview_markdown = None
            references = None
            images = None
            ai_overview_type = None
            cited_domains = {}

            if serp_data.get("ai_overview"):
                ai_item = serp_data["ai_overview"]
                ai_overview_text = ai_item.get("description") or ai_item.get("text") or ai_item.get("content")
                ai_overview_title = ai_item.get("title")
                ai_overview_markdown = ai_item.get("markdown")
                references = ai_item.get("references") or ai_item.get("ai_overview_reference") or None
                images = ai_item.get("images") or None
                ai_overview_type = ai_item.get("type") or "ai_overview"
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
                existing.aiOverviewTitle = ai_overview_title
                existing.aiOverviewMarkdown = ai_overview_markdown
                existing.references = references
                existing.images = images
                existing.aiOverviewType = ai_overview_type
                existing.citedDomains = cited_domains or None
                existing.checkedAt = datetime.utcnow()
            else:
                db.add(
                    AIOTracking(
                        projectId=project_id,
                        keywordText=keyword.keyword,
                        hasAIOverview=has_ai_overview,
                        aiOverviewText=ai_overview_text,
                        aiOverviewTitle=ai_overview_title,
                        aiOverviewMarkdown=ai_overview_markdown,
                        references=references,
                        images=images,
                        aiOverviewType=ai_overview_type,
                        citedDomains=cited_domains or None,
                    )
                )
            tracked += 1
            set_cached("aio_tracking", (project_id, keyword.keyword), {"hasAIOverview": has_ai_overview, "cited_domains": cited_domains}, ttl_seconds=24 * 60 * 60)

    db.commit()
    return {"tracked": tracked}


def get_aio_dashboard(db: Session, user_id: str, project_id: str) -> dict:
    project = db.scalar(select(Project).where(Project.id == project_id))
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
    project = db.scalar(select(Project).where(Project.id == project_id))
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


def get_aio_detail(db: Session, user_id: str, project_id: str, keyword_text: str) -> dict | None:
    track = db.scalar(
        select(AIOTracking).where(
            AIOTracking.projectId == project_id,
            AIOTracking.keywordText == keyword_text,
        )
    )
    if not track:
        keyword = db.scalar(
            select(Keyword).where(
                Keyword.projectId == project_id,
                Keyword.keyword == keyword_text,
            )
        )
        if keyword and keyword.hasAIOverview:
            return {
                "keyword": keyword.keyword,
                "hasAIOverview": keyword.hasAIOverview,
                "aiOverviewText": None,
                "aiOverviewTitle": None,
                "aiOverviewMarkdown": None,
                "references": None,
                "images": None,
                "aiOverviewType": None,
                "citedDomains": None,
                "checkedAt": keyword.updatedAt.isoformat() if keyword.updatedAt else None,
            }
        return None

    return {
        "keyword": track.keywordText,
        "hasAIOverview": track.hasAIOverview,
        "aiOverviewText": track.aiOverviewText,
        "aiOverviewTitle": track.aiOverviewTitle,
        "aiOverviewMarkdown": track.aiOverviewMarkdown,
        "references": track.references,
        "images": track.images,
        "aiOverviewType": track.aiOverviewType,
        "citedDomains": track.citedDomains,
        "checkedAt": track.checkedAt.isoformat() if track.checkedAt else None,
    }
