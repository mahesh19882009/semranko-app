import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User, Project, TrackedKeyword, RankResult
from app.db.session import SessionLocal
from app.services.dataforseo_client import DataForSEOClient
from app.services.team_service import get_team_owner_id

logger = logging.getLogger(__name__)


def _get_user_domains(db: Session, user_id: str) -> list[str]:
    projects = db.scalars(select(Project.domain).where(Project.userId == user_id)).all()
    return [d.lower() for d in projects if d]


def _find_best_position(serp_data: Optional[dict], domains: list[str]) -> Optional[int]:
    if not serp_data or not domains:
        return None

    organic_items = serp_data.get("organic_items") or []
    best: Optional[int] = None

    for item in organic_items:
        item_domain = (item.get("domain") or "").lower()
        item_url = (item.get("url") or "").lower()
        if any(domain in item_domain or domain in item_url for domain in domains):
            position = item.get("rank_group")
            if isinstance(position, int):
                if best is None or position < best:
                    best = position

    return best


def run_monday_tracker() -> dict:
    db = SessionLocal()
    try:
        users = db.scalars(
            select(User).where(
                User.subscriptionStatus.in_(["active", "trialing"]),
                User.creditBalance >= 0,
            )
        ).all()

        if not users:
            logger.info("Monday tracker: no active users found")
            return {"scanned_users": 0, "updated_keywords": 0}

        user_map = {user.id: user for user in users}
        tracked_rows = db.scalars(
            select(TrackedKeyword).where(
                TrackedKeyword.userId.in_(list(user_map.keys())),
                TrackedKeyword.isActive.is_(True),
            )
        ).all()

        if not tracked_rows:
            logger.info("Monday tracker: no active tracked keywords found")
            return {"scanned_users": len(users), "updated_keywords": 0}

        by_location = defaultdict(list)
        for row in tracked_rows:
            by_location[row.location or "India"].append(row)

        total_updated = 0
        now = datetime.utcnow()

        for location, rows in by_location.items():
            keywords_payload = []
            row_map = {}

            for row in rows:
                keywords_payload.append({"keyword": row.keyword, "location": row.location or "India", "device": row.device or "desktop"})
                row_map[row.keyword] = row

            aio_keywords = {row.keyword for row in rows if row.trackAio}
            non_aio_keywords = [row.keyword for row in rows if not row.trackAio]

            serp_map: dict[str, dict] = {}

            if non_aio_keywords:
                non_aio_payload = [kw for kw in keywords_payload if kw["keyword"] in set(non_aio_keywords)]
                if non_aio_payload:
                    result = DataForSEOClient.get_serp_data_batch(non_aio_payload, location, result_type="regular")
                    serp_map.update(result)

            if aio_keywords:
                aio_payload = [kw for kw in keywords_payload if kw["keyword"] in aio_keywords]
                if aio_payload:
                    result = DataForSEOClient.get_serp_data_batch(aio_payload, location, result_type="advanced", aio_keyword_texts=aio_keywords)
                    serp_map.update(result)

            for row in rows:
                serp_data = serp_map.get(row.keyword)
                domains = _get_user_domains(db, row.userId)
                position = _find_best_position(serp_data, domains)

                if position is not None:
                    row.lastPosition = position
                    row.lastCheckedAt = now
                    db.add(row)
                    total_updated += 1

                    history = RankResult(
                        projectId=user_map[row.userId].projects[0].id if user_map[row.userId].projects else "",
                        keywordText=row.keyword,
                        position=position,
                        device=row.device or "desktop",
                        location=row.location or "India",
                        checkedAt=now,
                        keywordId=row.id,
                    )
                    db.add(history)

        db.commit()
        logger.info("Monday tracker completed: users=%d updated_keywords=%d", len(users), total_updated)
        return {"scanned_users": len(users), "updated_keywords": total_updated}

    except Exception as exc:
        db.rollback()
        logger.exception("Monday tracker failed: %s", exc)
        raise
    finally:
        db.close()
