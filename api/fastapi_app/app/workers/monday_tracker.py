import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models import User, Project, Keyword, KeywordCache, CreditLedger
from app.db.session import SessionLocal
from app.services.dataforseo_dashboard import DataForSeoDashboardHelper
from app.services.team_service import get_team_owner_id
from app.services.credit_service import deduct_credits, refund_credits
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


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
        active_subscription_statuses = ["active", "trialing"]
        keywords = db.scalars(
            select(Keyword)
        ).all()

        if not keywords:
            logger.info("Monday tracker: no keywords found")
            return {"scanned_users": 0, "updated_keywords": 0}

        # Get user IDs through Project relationship
        project_ids = {kw.projectId for kw in keywords}
        projects = db.scalars(
            select(Project).where(Project.id.in_(list(project_ids)))
        ).all()
        project_to_user = {p.id: p.userId for p in projects}
        
        user_ids = {project_to_user.get(kw.projectId) for kw in keywords if kw.projectId in project_to_user}
        users = db.scalars(
            select(User).where(
                User.id.in_(list(user_ids)),
                User.subscriptionStatus.in_(active_subscription_statuses),
            )
        ).all()
        active_user_ids = {u.id for u in users}

        active_keywords_filtered = [kw for kw in keywords if project_to_user.get(kw.projectId) in active_user_ids]
        skipped_keywords = [kw for kw in keywords if project_to_user.get(kw.projectId) not in active_user_ids]

        if not active_keywords_filtered:
            db.commit()
            logger.info("Monday tracker: no active users with valid subscriptions")
            return {"scanned_users": 0, "updated_keywords": 0}

        user_keyword_groups = defaultdict(list)
        for kw in active_keywords_filtered:
            user_id = project_to_user.get(kw.projectId)
            if user_id:
                user_keyword_groups[user_id].append(kw)

        total_deducted = 0
        users_with_insufficient_credits = set()
        deducted_users = {}

        for user_id, kws in user_keyword_groups.items():
            active_count = len(kws)
            owner_id = get_team_owner_id(db, user_id)
            user = db.scalar(select(User).where(User.id == user_id))

            if not user:
                continue

            current_balance = float(getattr(user, "creditBalance", 0.0) or 0.0)
            required = active_count * 15

            if current_balance < required:
                users_with_insufficient_credits.add(user_id)
                continue

            deduct_credits(
                db,
                owner_id,
                float(required),
                "WEEKLY_REFRESH",
                f"Monday weekly refresh: {active_count} active keyword(s)",
            )
            total_deducted += required
            deducted_users[user_id] = {
                "owner_id": owner_id,
                "amount": float(required),
            }

        db.commit()

        unique_active_keywords = sorted({kw.keyword.lower().strip() for kw in active_keywords_filtered if kw.keyword})

        if not unique_active_keywords:
            logger.info("Monday tracker: no unique active keywords to process")
            return {
                "scanned_users": len(active_user_ids),
                "updated_keywords": 0,
                "total_deducted": total_deducted,
            }

        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        cache_rows = db.scalars(
            select(KeywordCache).where(KeywordCache.keyword.in_(unique_active_keywords))
        ).all()

        fresh_cache = {}
        stale_or_missing = []

        for row in cache_rows:
            if row.updatedAt and row.updatedAt >= seven_days_ago:
                fresh_cache[row.keyword] = row
            else:
                stale_or_missing.append(row.keyword)

        for kw in unique_active_keywords:
            if kw not in fresh_cache:
                stale_or_missing.append(kw)

        stale_and_missing_demanded_keywords = sorted(set(stale_or_missing))

        if not stale_and_missing_demanded_keywords:
            logger.info("Monday tracker: all active keywords are fresh in cache")
            return {
                "scanned_users": len(active_user_ids),
                "updated_keywords": 0,
                "total_deducted": total_deducted,
            }

        helper = DataForSeoDashboardHelper(
            settings.effective_serp_login,
            settings.effective_serp_key,
        )

        target_domain = _get_user_domains(db, list(active_user_ids)[0])[0] if _get_user_domains(db, list(active_user_ids)[0]) else None
        if not target_domain:
            target_domain = "example.com"

        try:
            fresh_data = helper.fetch_cheapest_dashboard_data(
                stale_and_missing_demanded_keywords,
                target_domain,
                location_code=2840,
            )
        except Exception as exc:
            db.rollback()
            logger.error(f"Monday tracker DataForSEO failed, refunding {len(deducted_users)} users: {exc}")
            for refund_user_id, refund_info in deducted_users.items():
                try:
                    refund_credits(
                        db,
                        refund_info["owner_id"],
                        refund_info["amount"],
                        f"Refund: Monday weekly refresh failed for user {refund_user_id}",
                    )
                except Exception as refund_exc:
                    logger.error(f"Failed to refund user {refund_user_id}: {refund_exc}")
            db.commit()
            raise

        upsert_count = 0
        if fresh_data:
            for row in fresh_data:
                keyword_text = row.get("Keyword")
                if not keyword_text:
                    continue

                cache_entry = db.scalar(
                    select(KeywordCache).where(KeywordCache.keyword == keyword_text)
                )

                volume = int(row.get("Search Volume")) if str(row.get("Search Volume", "—")).replace('.', '', 1).isdigit() else None
                kd = int(row.get("KD")) if str(row.get("KD", "—")).replace('.', '', 1).isdigit() else None
                cpc = float(row.get("CPC")) if str(row.get("CPC", "—")).replace('.', '', 1).isdigit() else None
                competition = float(row.get("Competition")) if str(row.get("Competition", "—")).replace('.', '', 1).isdigit() else None
                backlinks = float(row.get("Backlinks")) if str(row.get("Backlinks", "—")).replace('.', '', 1).isdigit() else None
                referring_domains = float(row.get("Domains")) if str(row.get("Domains", "—")).replace('.', '', 1).isdigit() else None
                position = int(row.get("Position")) if str(row.get("Position", "—")).replace('.', '', 1).isdigit() else None
                ai_badge = row.get("AI") if row.get("AI") == "AIO" else None
                intent = row.get("Intent") if row.get("Intent") not in ["—", None] else None

                if cache_entry:
                    cache_entry.volume = volume
                    cache_entry.kd = kd
                    cache_entry.intent = intent
                    cache_entry.cpc = cpc
                    cache_entry.competition = competition
                    cache_entry.backlinks = backlinks
                    cache_entry.referring_domains = referring_domains
                    cache_entry.position = position
                    cache_entry.ai_badge = ai_badge
                    cache_entry.updatedAt = datetime.utcnow()
                else:
                    cache_entry = KeywordCache(
                        keyword=keyword_text,
                        location="India",
                        volume=volume,
                        kd=kd,
                        intent=intent,
                        cpc=cpc,
                        competition=competition,
                        backlinks=backlinks,
                        referring_domains=referring_domains,
                        position=position,
                        ai_badge=ai_badge,
                        updatedAt=datetime.utcnow(),
                    )
                    db.add(cache_entry)

                keyword_row = db.scalar(
                    select(Keyword).where(Keyword.keyword == keyword_text)
                )
                if keyword_row:
                    keyword_row.volume = volume
                    keyword_row.kd = kd
                    keyword_row.cpc = cpc
                    keyword_row.competition = competition
                    keyword_row.backlinks = backlinks
                    keyword_row.referring_domains = referring_domains
                    keyword_row.intent = intent
                    keyword_row.position = position
                    keyword_row.ai_badge = ai_badge
                    keyword_row.updatedAt = datetime.utcnow()

                upsert_count += 1

        db.commit()
        logger.info(
            "Monday tracker completed: users=%d unique_keywords=%d refreshed=%d deducted=%d",
            len(active_user_ids),
            len(unique_active_keywords),
            upsert_count,
            total_deducted,
        )
        return {
            "scanned_users": len(active_user_ids),
            "updated_keywords": upsert_count,
            "total_deducted": total_deducted,
        }

    except Exception as exc:
        db.rollback()
        logger.exception("Monday tracker failed: %s", exc)
        raise
    finally:
        db.close()
