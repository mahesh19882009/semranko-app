"""
Webhook Credit Retry Service

Retries failed credit deductions from webhook processing.
Ensures no successful DFS result is permanently applied without corresponding credits.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import PendingWebhookCredit, User
from app.services.credit_service import deduct_credits
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def retry_pending_webhook_credits(db: Session, batch_size: int = 100) -> dict:
    """
    Retry failed webhook credit deductions.
    
    Returns dict with:
        retried: number of pending charges attempted
        succeeded: number successfully charged
        failed: number that failed again
        skipped: number skipped (max attempts reached or user not found)
    """
    pending = db.scalars(
        select(PendingWebhookCredit)
        .where(PendingWebhookCredit.status == "pending")
        .where(PendingWebhookCredit.attempts < PendingWebhookCredit.maxAttempts)
        .order_by(PendingWebhookCredit.createdAt.asc())
        .limit(batch_size)
    ).all()

    if not pending:
        return {"retried": 0, "succeeded": 0, "failed": 0, "skipped": 0}

    succeeded = 0
    failed = 0
    skipped = 0

    for charge in pending:
        user = db.scalar(select(User).where(User.id == charge.userId))
        if not user:
            charge.status = "failed"
            charge.lastError = "User not found"
            charge.attempts += 1
            db.add(charge)
            skipped += 1
            continue

        try:
            deduct_credits(
                db=db,
                user_id=charge.userId,
                amount=charge.amount,
                action_type="charge",
                description=charge.description or "Webhook credit retry",
                project_id=charge.projectId,
                keyword_id=charge.keywordId,
                task_id=charge.taskId,
            )
            charge.status = "completed"
            charge.attempts += 1
            db.add(charge)
            succeeded += 1
        except Exception as exc:
            charge.status = "pending"
            charge.attempts += 1
            charge.lastError = str(exc)[:500]
            db.add(charge)
            failed += 1

    db.commit()
    return {
        "retried": len(pending),
        "succeeded": succeeded,
        "failed": failed,
        "skipped": skipped,
    }


def run_webhook_credit_retry_job() -> dict:
    """Entry point for scheduled retry job."""
    db = SessionLocal()
    try:
        result = retry_pending_webhook_credits(db)
        logger.info("Webhook credit retry completed: %s", result)
        return result
    except Exception as exc:
        logger.exception("Webhook credit retry job failed: %s", exc)
        return {"retried": 0, "succeeded": 0, "failed": 0, "skipped": 0, "error": str(exc)}
    finally:
        db.close()
