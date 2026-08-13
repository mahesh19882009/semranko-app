import logging
import math
import re
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.models import Keyword, Project
from app.services.cache_service import increment_usage
from app.services.credit_service import deduct_credits, refund_credits, reserve_credits, consume_reserved
from app.services.plan_service import ensure_keyword_limit, get_user_plan_limits_by_id, count_user_keywords
from app.services.dataforseo_client import DataForSEOClient
from app.core.config import get_settings
from app.core.errors import ApiError
from app.services.feature_usage_service import (
    ensure_feature_available,
    reserve_feature_usage,
    finalize_feature_usage,
    release_feature_usage,
)

logger = logging.getLogger(__name__)
settings = get_settings()


def _is_cache_data_valid(data: dict) -> bool:
    if not data:
        return False
    core_fields = ["volume", "kd", "cpc", "position", "intent"]
    non_null_count = sum(1 for field in core_fields if data.get(field) is not None)
    return non_null_count >= 2


def research_keyword(db: Session, user_id: str, keyword: str, location_code: int = 2840) -> dict:
    from app.services.keyword_research_cache_service import query_research_cache, save_research_cache

    usage = ensure_feature_available(db, user_id, "keyword_research")
    cached_ideas = query_research_cache(db, user_id, keyword, location_code)
    if cached_ideas is not None:
        logger.info("Returning cached keyword research for '%s' (location=%s)", keyword, location_code)
        normalized = [_normalize_idea(i) for i in cached_ideas]
        response = _build_research_response(keyword, normalized, credits_charged=0)
        response["cached"] = True
        response["usage"] = usage
        return response

    cost = settings.plan_config.credit_costs.get("keyword_research", 20)
    usage_reference, usage = reserve_feature_usage(
        db, user_id, "keyword_research", 1,
        reference=f"research-usage:{user_id}:{keyword}:{location_code}:{datetime.utcnow().timestamp()}",
    )
    reference = f"research:{user_id}:{keyword}:{location_code}:{datetime.utcnow().timestamp()}"
    try:
        reserve_credits(
            db,
            user_id,
            float(cost),
            "reservation",
            f"Keyword research: {keyword}",
            reference=reference,
        )
    except Exception as exc:
        release_feature_usage(db, usage_reference)
        raise ApiError(402, f"Insufficient credits for keyword research. Required: {cost}")

    try:
        ideas = DataForSEOClient.get_keyword_ideas_api(keyword, location_code, limit=50)
        save_research_cache(db, user_id, keyword, location_code, ideas or [])

        consume_reserved(
            db,
            user_id,
            reference,
            float(cost),
            action_type="charge",
            description=f"Keyword research: {keyword}",
        )

        usage = finalize_feature_usage(db, usage_reference, 1)
        db.commit()
        response = _build_research_response(keyword, ideas or [], credits_charged=1)
        response["cached"] = False
        response["usage"] = usage
        return response
    except Exception as exc:
        db.rollback()
        try:
            refund_reserved(db, user_id, reference, float(cost), description=f"Refund: keyword research failed for {keyword}")
            db.commit()
        except Exception:
            db.rollback()
        try:
            release_feature_usage(db, usage_reference)
        except Exception:
            db.rollback()
        raise


def _normalize_idea(idea: dict) -> dict:
    idea = dict(idea)
    if "search_volume" in idea and "volume" not in idea:
        idea["volume"] = idea.pop("search_volume")
    if "keyword_difficulty" in idea and "difficulty" not in idea:
        idea["difficulty"] = idea.pop("keyword_difficulty")
    return idea


def _build_research_response(seed_keyword: str, ideas: list[dict], credits_charged: int) -> dict:
    seed_lower = seed_keyword.lower().strip()
    seed_metrics = {
        "volume": None,
        "kd": None,
        "cpc": None,
        "intent": None,
        "competition": None,
    }
    for idea in ideas:
        if idea.get("keyword", "").lower().strip() == seed_lower:
            seed_metrics = {
                "volume": idea.get("volume"),
                "kd": idea.get("difficulty"),
                "cpc": idea.get("cpc"),
                "intent": idea.get("intent"),
                "competition": None,
            }
            break

    return {
        "seed": seed_keyword,
        "ideas": ideas,
        "suggestions": ideas,
        **seed_metrics,
        "credits_charged": credits_charged,
    }


def _apply_day_one_tracking_bulk(db: Session, user_id: str, created: list[Keyword], location_code: int, domain: str) -> None:
    if not created:
        return

    try:
        keywords_to_fetch = [kw.keyword for kw in created]
        total_cost = 0.0
        reference = None

        if keywords_to_fetch:
            from app.db.models import TrackedKeyword
            aio_keyword_texts = set(
                row.keyword
                for row in db.scalars(
                    select(TrackedKeyword).where(
                        TrackedKeyword.userId == user_id,
                        TrackedKeyword.isActive == True,
                        TrackedKeyword.trackAio == True,
                        TrackedKeyword.keyword.in_(keywords_to_fetch),
                    )
                ).all()
            )

            cost_per_keyword = settings.plan_config.credit_costs.get("bulk_add_keyword", 20)
            total_cost = float(len(keywords_to_fetch) * cost_per_keyword)
            reference = f"bulkdayone:{user_id}:{domain}:{datetime.utcnow().timestamp()}"
            try:
                reserve_credits(
                    db,
                    user_id,
                    total_cost,
                    "reservation",
                    f"Bulk day-one tracking reservation: {len(keywords_to_fetch)} keyword(s)",
                    reference=reference,
                )
            except Exception as exc:
                logger.error(f"Bulk day-one tracking credit reservation failed: {exc}")
                raise ApiError(402, f"Insufficient credits for bulk day-one tracking. Required: {total_cost}")

            rows = DataForSEOClient.fetch_dashboard_data(
                keywords_to_fetch,
                domain,
                location_code=location_code,
                language_code="en",
                aio_keyword_texts=aio_keyword_texts,
            )
            row_map = {row.get("keyword", "").lower().strip(): row for row in rows}

            fetched_ok_count = 0
            for kw in created:
                row = row_map.get(kw.keyword.lower().strip())
                if row and _is_cache_data_valid(row):
                    kw.volume = row.get("volume")
                    kw.kd = row.get("kd")
                    kw.cpc = row.get("cpc")
                    kw.intent = row.get("intent")
                    kw.position = row.get("position")
                    kw.ai_badge = row.get("ai_badge")
                    ai_description = row.get("ai_description")
                    if isinstance(ai_description, str):
                        ai_description = re.sub(r'\.{3}\s*Read more$', '', ai_description.strip()) or None
                    kw.ai_description = ai_description
                    fetched_ok_count += 1

            consumed_cost = float(fetched_ok_count * cost_per_keyword)
            if fetched_ok_count > 0:
                consume_reserved(
                    db,
                    user_id,
                    reference,
                    consumed_cost,
                    action_type="charge",
                    description=f"Day-one tracking: {fetched_ok_count} keyword(s)",
                )

            refund_amount = total_cost - consumed_cost
            if refund_amount > 0:
                try:
                    refund_reserved(
                        db,
                        user_id,
                        reference,
                        refund_amount,
                        description=f"Refund: {len(keywords_to_fetch) - fetched_ok_count} keyword(s) failed day-one tracking",
                    )
                except Exception as refund_exc:
                    logger.error(f"Failed to refund reserved credits for bulk day-one tracking: {refund_exc}")

        db.commit()
    except ApiError:
        raise
    except Exception as exc:
        db.rollback()
        logger.error(f"Day-one tracking failed for batch: {exc}")
        raise


def add_keywords_to_project(db: Session, user_id: str, project_id: str, keywords: list[str], location_code: int = 2840, location: str = "India") -> list[Keyword]:
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        raise ValueError("Project not found")

    ensure_keyword_limit(db, user_id)

    limits = get_user_plan_limits_by_id(db, user_id)
    keyword_limit = limits.get("keywordLimit", 0)
    current_count = count_user_keywords(db, user_id)
    if keyword_limit > 0 and current_count + len(keywords) > keyword_limit:
        raise ValueError(f"Keyword limit reached. Your current plan allows {keyword_limit} keywords. You can only add {keyword_limit - current_count} more.")

    created = []
    for kw in keywords:
        keyword = Keyword(
            projectId=project_id,
            userId=user_id,
            keyword=kw,
            location=location,
            isActive=True,
            volume=0,
            kd=0,
            cpc=0.0,
            competition=0.0,
            backlinks=0.0,
            referring_domains=0.0,
            intent="—",
            position=0,
            ai_badge="—",
        )
        db.add(keyword)
        created.append(keyword)

    db.commit()
    for kw in created:
        db.refresh(kw)

    _apply_day_one_tracking_bulk(db, user_id, created, location_code, project.domain)

    for kw in created:
        db.refresh(kw)
    return created
