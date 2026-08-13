import random
from datetime import datetime
from typing import Optional
import requests
from sqlalchemy import delete, select
from app.db.models import RankResult, CompetitorRank, TrackedKeyword, Keyword
from app.db.session import SessionLocal
from app.core.config import get_settings

settings = get_settings()
LOCATION_CODES = {"India": 2356, "United States": 2840, "United Kingdom": 2826, "Global": 2840}


def dfs_visibility(position: Optional[int]) -> float:
    if position is None or position > 100:
        return 0.0
    if 1 <= position <= 10:
        return round(1.0 - (position - 1) * 0.1, 2)
    if 11 <= position <= 20:
        return 0.05
    return 0.0


def process_rank_check_job(project_id: str, domain: str, keywords: list[dict], user_id: str | None = None, reference: str | None = None) -> dict:
    if not project_id or not domain or not isinstance(keywords, list):
        raise ValueError("Invalid job payload")

    from app.services.dataforseo_client import DataForSEOClient
    from app.services.credit_service import consume_reserved, refund_reserved

    db = SessionLocal()
    try:
        keyword_texts = [kw.get("keyword", "") for kw in keywords if kw.get("keyword")]
        aio_keyword_texts = set()
        if user_id:
            try:
                aio_keyword_texts = set(
                    row.keyword
                    for row in db.scalars(
                        select(TrackedKeyword).where(
                            TrackedKeyword.userId == user_id,
                            TrackedKeyword.isActive == True,
                            TrackedKeyword.trackAio == True,
                            TrackedKeyword.keyword.in_(keyword_texts),
                        )
                    ).all()
                )
            except Exception:
                aio_keyword_texts = set()
    except Exception:
        aio_keyword_texts = set()
    finally:
        db.close()

    refresh_cost = 10
    try:
        rank_map = DataForSEOClient.get_rank_batch(keywords, domain, aio_keyword_texts=aio_keyword_texts)
    except Exception as exc:
        if user_id and reference:
            try:
                refund_reserved(db, user_id, reference, float(len(keywords) * refresh_cost), description=f"Refund: rank check failed for project {project_id}", project_id=project_id)
            except Exception:
                pass
        raise

    rows = []
    keyword_visibility_map = {}
    for keyword in keywords:
        keyword_text = keyword.get("keyword", "")
        rank_info = rank_map.get(keyword_text)
        position = rank_info.get("position") if rank_info else None
        url = rank_info.get("url") if rank_info else None
        etv = rank_info.get("etv") if rank_info else None
        visibility = dfs_visibility(position)

        rows.append(
            {
                "projectId": project_id,
                "keywordId": keyword.get("id"),
                "keywordText": keyword_text,
                "position": position,
                "url": url,
                "location": keyword.get("location") or "India",
                "device": keyword.get("device") or "desktop",
                "etv": etv,
                "checkedAt": datetime.utcnow(),
            }
        )

        if keyword.get("id"):
            keyword_visibility_map[keyword.get("id")] = visibility

    db = SessionLocal()
    try:
        if rows:
            db.bulk_insert_mappings(RankResult, rows)

        if keyword_visibility_map:
            keyword_ids = list(keyword_visibility_map.keys())
            keyword_objs = db.scalars(
                select(Keyword).where(Keyword.id.in_(keyword_ids), Keyword.projectId == project_id)
            ).all()
            for kw_obj in keyword_objs:
                kw_obj.visibility = keyword_visibility_map.get(kw_obj.id)
                kw_obj.updatedAt = datetime.utcnow()

        db.commit()
        return {"inserted": len(rows)}

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    if user_id and reference:
        try:
            consume_reserved(
                db,
                user_id,
                reference,
                float(len(keywords) * refresh_cost),
                action_type="charge",
                description=f"Rank check: {len(keywords)} keyword(s) for project {project_id}",
                project_id=project_id,
            )
        except Exception as exc:
            logger.error(f"Failed to consume reserved credits for rank check: {exc}")


def process_competitor_rank_job(project_id: str, domain: str, competitor_ids: list[str], keywords: list[dict]) -> dict:
    if not project_id or not domain or not competitor_ids or not isinstance(keywords, list):
        raise ValueError("Invalid competitor job payload")

    from app.services.dataforseo_client import DataForSEOClient

    db = SessionLocal()
    try:
        from app.db.models import Competitor
        competitors = db.scalars(
            select(Competitor).where(Competitor.id.in_(competitor_ids), Competitor.projectId == project_id)
        ).all()
        if not competitors:
            return {"tracked": 0}

        location = keywords[0].get("location", "India") if keywords else "India"
        serp_map = DataForSEOClient.get_serp_data_batch(keywords, location)
        tracked = 0

        for competitor in competitors:
            target_domain = competitor.domain.lower()
            for keyword in keywords:
                keyword_text = keyword.get("keyword", "")
                serp_data = serp_map.get(keyword_text)
                if not serp_data:
                    continue

                rank = None
                url = None

                for item in serp_data.get("items", []):
                    if item.get("type") != "organic":
                        continue
                    item_domain = (item.get("domain") or "").lower()
                    item_url = item.get("url") or ""
                    if target_domain in item_domain or target_domain in item_url:
                        rank = item.get("rank_group") or item.get("rank_absolute")
                        url = item_url
                        break

                if rank is None:
                    for group_item in serp_data.get("featured_snippet", {}).get("items", []):
                        item_domain = (group_item.get("domain") or "").lower()
                        item_url = group_item.get("url") or ""
                        if target_domain in item_domain or target_domain in item_url:
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
                        from datetime import datetime as dt
                        existing.checkedAt = dt.utcnow()
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

        db.commit()
        return {"tracked": tracked}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
