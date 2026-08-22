import logging
from sqlalchemy import select, func, desc, over
from sqlalchemy.orm import Session
from app.db.models import Keyword, Project, RankResult, KeywordMetricsHistory
from app.core.errors import ApiError
from app.services.location_catalog import location_label

logger = logging.getLogger(__name__)


def _calculate_visibility(position: int | None) -> float:
    if position is None or position > 100:
        return 0.0
    if 1 <= position <= 10:
        return round(1.0 - (position - 1) * 0.1, 2)
    if 11 <= position <= 20:
        return 0.05
    return 0.0


def get_enriched_keywords(db: Session, user_id: str, project_id: str) -> list[dict]:
    project = db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.userId == user_id,
        )
    )
    if not project:
        raise ApiError(404, "Project not found")

    project_location = location_label(project.location)

    keywords = db.scalars(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.userId == user_id,
        )
    ).all()

    keyword_ids = [kw.id for kw in keywords if kw.id]

    rank_history = {}
    if keyword_ids:
        rank_history_subq = (
            select(
                RankResult.keywordId,
                RankResult.position,
                RankResult.url,
                RankResult.checkedAt,
                func.row_number().over(
                    partition_by=RankResult.keywordId,
                    order_by=(RankResult.checkedAt.desc(), RankResult.id.desc()),
                ).label('rn'),
            )
            .where(RankResult.projectId == project_id)
            .where(RankResult.keywordId.in_(keyword_ids))
            .subquery()
        )
        rank_history_rows = db.execute(
            select(rank_history_subq).where(rank_history_subq.c.rn <= 2)
        ).fetchall()
        for row in rank_history_rows:
            rank_history.setdefault(row.keywordId, {})[row.rn] = {
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
        has_ai_overview = kw.ai_badge == "AIO"

        prev_metrics = previous_metrics.get(kw.id, {})
        changes = {}
        for field in ["volume", "kd", "cpc", "competition", "backlinks", "referring_domains"]:
            curr = getattr(kw, field, None)
            prev = prev_metrics.get(field)
            if curr is not None and prev is not None:
                diff = round(float(curr) - float(prev), 2)
                if field == "kd":
                    direction = "up" if diff > 0 else ("down" if diff < 0 else "same")
                    is_positive = diff < 0
                elif field in ("volume", "backlinks", "referring_domains"):
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

        rank_history_info = rank_history.get(kw.id, {})
        rank_info = rank_history_info.get(1, {})
        previous_rank_info = rank_history_info.get(2, {})

        position_change = None
        previous_position = previous_rank_info.get("position")
        if (
            kw.position is not None
            and kw.position > 0
            and previous_position is not None
            and previous_position > 0
        ):
            pos_diff = round(float(kw.position) - float(previous_position), 1)
            if pos_diff != 0:
                position_change = {
                    "previous": previous_position,
                    "current": kw.position,
                    "difference": pos_diff,
                    "direction": "up" if pos_diff < 0 else "down",
                    "isPositive": pos_diff < 0,
                }

        effective_rank = kw.position if kw.position is not None else kw.localPackPosition
        visibility = _calculate_visibility(effective_rank)

        visibility_change = None
        if previous_position is not None and previous_position > 0:
            previous_visibility = _calculate_visibility(previous_position)
            visibility_diff = round(visibility - previous_visibility, 2)
            if visibility_diff != 0:
                visibility_change = {
                    "previous": previous_visibility,
                    "current": visibility,
                    "difference": visibility_diff,
                    "direction": "up" if visibility_diff > 0 else "down",
                    "isPositive": visibility_diff > 0,
                }

        results.append({
            "id": kw.id,
            "keyword": kw.keyword,
            "location": location_label(kw.location, project_location),
            "locationCode": kw.locationCode,
            "device": kw.device or "desktop",
            "volume": kw.volume,
            "kd": kw.kd,
            "cpc": kw.cpc,
            "competition": kw.competition,
            "backlinks": kw.backlinks,
            "domains": kw.referring_domains,
            "intent": kw.intent,
            "position": kw.position,
            "localPackPosition": kw.localPackPosition,
            "localPackUrl": kw.localPackUrl,
            "url": rank_info.get("url"),
            "check_url": kw.check_url,
            "rankCheckedAt": rank_info.get("checkedAt"),
            "ai": "AIO" if has_ai_overview else "Off",
            "hasAIOverview": has_ai_overview,
            "ai_description": kw.ai_description,
            "visibility": visibility,
            "is_active": kw.isActive,
            "deletedAt": kw.deletedAt.isoformat() if kw.deletedAt else None,
            "createdAt": kw.createdAt.isoformat() if getattr(kw, "createdAt", None) else None,
            "changes": changes,
            "positionChange": position_change,
            "visibilityChange": visibility_change,
        })

    return results
