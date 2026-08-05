import random
from datetime import datetime
from typing import Optional
import requests
from sqlalchemy import delete, select
from app.db.models import RankResult, CompetitorRank, AIOTracking, TrackedKeyword
from app.db.session import SessionLocal
from app.core.config import get_settings

settings = get_settings()
LOCATION_CODES = {"India": 2356, "United States": 2840, "United Kingdom": 2826, "Global": 2840}


def process_rank_check_job(project_id: str, domain: str, keywords: list[dict]) -> dict:
    if not project_id or not domain or not isinstance(keywords, list):
        raise ValueError("Invalid job payload")

    from app.services.dataforseo_client import DataForSEOClient

    db = SessionLocal()
    try:
        keyword_texts = [kw.get("keyword", "") for kw in keywords if kw.get("keyword")]
        aio_keyword_texts = set(
            row.keyword
            for row in db.scalars(
                select(TrackedKeyword).where(
                    TrackedKeyword.userId.in_(
                        select(Project.userId).where(Project.id == project_id)
                    ),
                    TrackedKeyword.isActive == True,
                    TrackedKeyword.trackAio == True,
                    TrackedKeyword.keyword.in_(keyword_texts),
                )
            ).all()
        )
    except Exception:
        aio_keyword_texts = set()
    finally:
        db.close()

    rank_map = DataForSEOClient.get_rank_batch(keywords, domain, aio_keyword_texts=aio_keyword_texts)

    rows = []
    for keyword in keywords:
        keyword_text = keyword.get("keyword", "")
        rank_info = rank_map.get(keyword_text)
        result = {
            "keywordText": keyword_text,
            "location": keyword.get("location") or "India",
            "device": keyword.get("device") or "desktop",
        }
        if rank_info:
            result["position"] = rank_info.get("position")
            result["url"] = rank_info.get("url")
        else:
            result["position"] = None
            result["url"] = None

        rows.append(
            {
                "projectId": project_id,
                "keywordId": keyword.get("id"),
                "keywordText": result["keywordText"],
                "position": result["position"],
                "url": result["url"],
                "location": result["location"],
                "device": result["device"],
                "checkedAt": datetime.utcnow(),
            }
        )

    db = SessionLocal()
    try:
        for keyword in keywords:
            db.execute(
                delete(RankResult).where(
                    RankResult.projectId == project_id,
                    RankResult.keywordId == keyword.get("id"),
                )
            )

        if rows:
            db.bulk_insert_mappings(RankResult, rows)

        db.commit()
        return {"inserted": len(rows)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def process_labs_metrics_job(project_id: str, keywords: list[dict]) -> dict:
    if not project_id or not isinstance(keywords, list):
        raise ValueError("Invalid Labs metrics job payload")

    from app.services.dataforseo_client import DataForSEOClient

    keyword_texts = [kw.get("keyword", "") for kw in keywords if kw.get("keyword")]
    if not keyword_texts:
        return {"updated": 0}

    batch_data = DataForSEOClient.get_keyword_data_batch(keyword_texts, "India", force_refresh=True)

    db = SessionLocal()
    try:
        updated = 0
        for kw in keywords:
            keyword_text = kw.get("keyword", "")
            data = batch_data.get(keyword_text)
            if not data:
                continue

            keyword_id = kw.get("id")
            if not keyword_id:
                continue

            from app.db.models import Keyword
            keyword_obj = db.scalar(select(Keyword).where(Keyword.id == keyword_id, Keyword.projectId == project_id))
            if not keyword_obj:
                continue

            keyword_obj.volume = data.get("volume")
            keyword_obj.kd = data.get("difficulty")
            keyword_obj.cpc = data.get("cpc")
            keyword_obj.competition = data.get("competition")
            keyword_obj.backlinks = data.get("backlinks")
            keyword_obj.referring_domains = data.get("referring_domains")
            keyword_obj.intent = data.get("intent")
            updated += 1

        db.commit()
        return {"updated": updated}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def process_competitor_rank_job(project_id: str, domain: str, competitor_ids: list[str], keywords: list[dict]) -> dict:
    if not project_id or not domain or not competitor_id or not isinstance(keywords, list):
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
                        rank = item.get("rank_group")
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


def process_aio_tracking_job(project_id: str, keywords: list[dict]) -> dict:
    if not project_id or not isinstance(keywords, list):
        raise ValueError("Invalid AIO job payload")

    from app.services.dataforseo_client import DataForSEOClient

    db = SessionLocal()
    try:
        location = keywords[0].get("location", "India") if keywords else "India"
        serp_map = DataForSEOClient.get_serp_data_batch(keywords, location)
        tracked = 0

        for keyword in keywords:
            keyword_text = keyword.get("keyword", "")
            serp_data = serp_map.get(keyword_text)
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
                    AIOTracking.keywordText == keyword_text,
                )
            )
            if existing:
                existing.hasAIOverview = has_ai_overview
                existing.aiOverviewText = ai_overview_text
                existing.citedDomains = cited_domains or None
                from datetime import datetime as dt
                existing.checkedAt = dt.utcnow()
            else:
                db.add(
                    AIOTracking(
                        projectId=project_id,
                        keywordText=keyword_text,
                        hasAIOverview=has_ai_overview,
                        aiOverviewText=ai_overview_text,
                        citedDomains=cited_domains or None,
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

