import logging
from sqlalchemy import select, func, desc, over
from sqlalchemy.orm import Session
from app.db.models import Keyword, RankResult, KeywordMetricsHistory
from app.core.errors import ApiError

logger = logging.getLogger(__name__)


def get_enriched_keywords(db: Session, user_id: str, project_id: str) -> list[dict]:
    keywords = db.scalars(
        select(Keyword).where(Keyword.projectId == project_id)
    ).all()

    keyword_ids = [kw.id for kw in keywords if kw.id]

    latest_ranks = {}
    if keyword_ids:
        latest_rank_subq = (
            select(
                RankResult.keywordId,
                RankResult.position,
                RankResult.url,
                RankResult.checkedAt,
                func.row_number().over(partition_by=RankResult.keywordId, order_by=RankResult.checkedAt.desc()).label('rn')
            )
            .where(RankResult.projectId == project_id)
            .where(RankResult.keywordId.in_(keyword_ids))
            .subquery()
        )
        latest_rank_rows = db.execute(
            select(latest_rank_subq).where(latest_rank_subq.c.rn == 1)
        ).fetchall()
        for row in latest_rank_rows:
            latest_ranks[row.keywordId] = {
                "position": row.position,
                "url": row.url,
                "checkedAt": row.checkedAt.isoformat() if row.checkedAt else None,
            }

    previous_metrics = {}
    if keyword_ids:
        latest_metrics_subq = (
            select(
                KeywordMetricsHistory.keywordId,
                KeywordMetricsHistory.volume,
                KeywordMetricsHistory.kd,
                KeywordMetricsHistory.cpc,
                KeywordMetricsHistory.competition,
                KeywordMetricsHistory.backlinks,
                KeywordMetricsHistory.referring_domains,
                KeywordMetricsHistory.intent,
                func.row_number().over(partition_by=KeywordMetricsHistory.keywordId, order_by=KeywordMetricsHistory.refreshedAt.desc()).label('rn')
            )
            .where(KeywordMetricsHistory.projectId == project_id)
            .where(KeywordMetricsHistory.keywordId.in_(keyword_ids))
            .subquery()
        )
        latest_metrics_rows = db.execute(
            select(latest_metrics_subq).where(latest_metrics_subq.c.rn == 1)
        ).fetchall()
        for row in latest_metrics_rows:
            previous_metrics[row.keywordId] = {
                "volume": row.volume,
                "kd": row.kd,
                "cpc": row.cpc,
                "competition": row.competition,
                "backlinks": row.backlinks,
                "referring_domains": row.referring_domains,
                "intent": row.intent,
            }

    results = []
    for kw in keywords:
        rank_info = latest_ranks.get(kw.id, {})
        has_ai_overview = kw.ai_badge == "AIO"

        prev_metrics = previous_metrics.get(kw.id, {})
        changes = {}
        for field in ["volume", "kd", "cpc", "competition", "backlinks", "referring_domains"]:
            curr = getattr(kw, field, None)
            prev = prev_metrics.get(field)
            if curr is not None and prev is not None:
                diff = round(float(curr) - float(prev), 2)
                if field in ("volume", "kd", "backlinks", "referring_domains"):
                    direction = "up" if diff > 0 else ("down" if diff < 0 else "same")
                    is_positive = diff > 0
                elif field == "cpc":
                    direction = "up" if diff > 0 else ("down" if diff < 0 else "same")
                    is_positive = diff > 0
                elif field == "competition":
                    direction = "up" if diff > 0 else ("down" if diff < 0 else "same")
                    is_positive = diff > 0
                else:
                    direction = "same"
                    is_positive = False
                changes[field] = {
                    "previous": prev,
                    "current": curr,
                    "difference": diff,
                    "direction": direction,
                    "isPositive": is_positive,
                }

        position_change = None
        if kw.position is not None and rank_info.get("position") is not None:
            pos_diff = round(float(kw.position) - float(rank_info["position"]), 1)
            position_change = {
                "previous": rank_info["position"],
                "current": kw.position,
                "difference": pos_diff,
                "direction": "up" if pos_diff < 0 else ("down" if pos_diff > 0 else "same"),
                "isPositive": pos_diff < 0,
            }

        results.append({
            "id": kw.id,
            "keyword": kw.keyword,
            "location": kw.location or "India",
            "device": kw.device or "desktop",
            "volume": kw.volume,
            "kd": kw.kd,
            "cpc": kw.cpc,
            "competition": kw.competition,
            "backlinks": kw.backlinks,
            "domains": kw.referring_domains,
            "intent": kw.intent,
            "position": kw.position,
            "url": rank_info.get("url"),
            "check_url": kw.check_url,
            "rankCheckedAt": rank_info.get("checkedAt"),
            "ai": "AIO" if has_ai_overview else "Off",
            "hasAIOverview": has_ai_overview,
            "ai_description": kw.ai_description,
            "visibility": kw.visibility,
            "is_active": kw.isActive,
            "deletedAt": kw.deletedAt.isoformat() if kw.deletedAt else None,
            "createdAt": kw.createdAt.isoformat() if getattr(kw, "createdAt", None) else None,
            "changes": changes,
            "positionChange": position_change,
        })

    return results
