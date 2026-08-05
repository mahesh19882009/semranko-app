import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import Competitor, CompetitorRank, Keyword, Project, RankResult, User
from app.services.dataforseo_client import DataForSEOClient
from app.services.plan_service import ensure_aio_tracking_limit, get_user_plan_limits
from app.services.cache_service import get_cached, set_cached
from app.core.errors import ApiError

logger = logging.getLogger(__name__)


def track_competitor_rankings(db: Session, user_id: str, project_id: str) -> dict:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    competitors = db.scalars(select(Competitor).where(Competitor.projectId == project_id)).all()
    keywords = db.scalars(select(Keyword).where(Keyword.projectId == project_id)).all()

    if not competitors or not keywords:
        return {"tracked": 0}

    location = keywords[0].location or "India"
    tracked = 0

    keywords_to_fetch = []
    for competitor in competitors:
        for keyword in keywords:
            cached = get_cached("competitor_rank", (project_id, competitor.id, keyword.keyword))
            if cached:
                tracked += 1
                continue
            keywords_to_fetch.append({"competitor": competitor, "keyword": keyword})

    if keywords_to_fetch:
        unique_keywords = []
        seen = set()
        for item in keywords_to_fetch:
            kw_text = item["keyword"].keyword
            if kw_text not in seen:
                seen.add(kw_text)
                unique_keywords.append({"keyword": kw_text, "location": location, "device": item["keyword"].device or "desktop"})

        serp_map = DataForSEOClient.get_serp_data_batch(unique_keywords, location)

        for item in keywords_to_fetch:
            competitor = item["competitor"]
            keyword = item["keyword"]
            keyword_text = keyword.keyword
            serp_data = serp_map.get(keyword_text)
            if not serp_data:
                continue

            domain = competitor.domain.lower()
            rank = None
            url = None

            for idx, item in enumerate(serp_data.get("items", []), start=1):
                if item.get("type") != "organic":
                    continue
                item_domain = (item.get("domain") or "").lower()
                item_url = item.get("url") or ""
                if domain in item_domain or domain in item_url:
                    rank = idx
                    url = item_url
                    break

            if rank is None:
                for group_item in serp_data.get("featured_snippet", {}).get("items", []):
                    item_domain = (group_item.get("domain") or "").lower()
                    item_url = group_item.get("url") or ""
                    if domain in item_domain or domain in item_url:
                        rank = 0
                        url = item_url
                        break

            if rank is not None:
                existing = db.scalar(
                    select(CompetitorRank).where(
                        CompetitorRank.projectId == project_id,
                        CompetitorRank.competitorId == competitor.id,
                        CompetitorRank.keywordText == keyword_text,
                    )
                )
                if existing:
                    existing.position = rank
                    existing.url = url
                    existing.checkedAt = datetime.utcnow()
                else:
                    db.add(
                        CompetitorRank(
                            projectId=project_id,
                            competitorId=competitor.id,
                            keywordText=keyword_text,
                            position=rank,
                            url=url,
                        )
                    )
                tracked += 1
                set_cached("competitor_rank", (project_id, competitor.id, keyword_text), {"position": rank, "url": url}, ttl_seconds=24 * 60 * 60)

    db.commit()
    return {"tracked": tracked}


def get_competitor_comparison(db: Session, user_id: str, project_id: str) -> list[dict]:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    competitors = db.scalars(select(Competitor).where(Competitor.projectId == project_id).limit(3)).all()
    if not competitors:
        return []

    keywords = db.scalars(select(Keyword).where(Keyword.projectId == project_id)).all()
    if not keywords:
        return []

    latest_user_ranks = {}
    for kw in keywords:
        rank = db.scalar(
            select(RankResult.position, RankResult.url)
            .where(RankResult.projectId == project_id, RankResult.keywordText == kw.keyword)
            .order_by(RankResult.checkedAt.desc())
            .limit(1)
        )
        latest_user_ranks[kw.keyword] = {"position": rank[0] if rank else None, "url": rank[1] if rank else None}

    competitor_ranks = {}
    for competitor in competitors:
        competitor_ranks[competitor.id] = {}
        for kw in keywords:
            rank = db.scalar(
                select(CompetitorRank.position, CompetitorRank.url)
                .where(
                    CompetitorRank.projectId == project_id,
                    CompetitorRank.competitorId == competitor.id,
                    CompetitorRank.keywordText == kw.keyword,
                )
                .order_by(CompetitorRank.checkedAt.desc())
                .limit(1)
            )
            competitor_ranks[competitor.id][kw.keyword] = {"position": rank[0] if rank else None, "url": rank[1] if rank else None}

    results = []
    for kw in keywords:
        row = {
            "keyword": kw.keyword,
            "user_position": latest_user_ranks.get(kw.keyword, {}).get("position"),
            "user_url": latest_user_ranks.get(kw.keyword, {}).get("url"),
        }
        for idx, competitor in enumerate(competitors, start=1):
            row[f"competitor_{idx}_name"] = competitor.name
            row[f"competitor_{idx}_position"] = competitor_ranks.get(competitor.id, {}).get(kw.keyword, {}).get("position")
            row[f"competitor_{idx}_url"] = competitor_ranks.get(competitor.id, {}).get(kw.keyword, {}).get("url")
        results.append(row)

    return results
