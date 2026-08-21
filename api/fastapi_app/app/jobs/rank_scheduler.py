from apscheduler.schedulers.background import BackgroundScheduler
from calendar import monthrange
from datetime import datetime, timedelta

from sqlalchemy import select, func, text

from app.db.session import SessionLocal
from app.services.async_bulk_service import (
    run_weekly_bulk_update_job,
    run_weekly_refresh_worker,
    recover_stale_weekly_jobs,
    get_refresh_status,
)
from app.services.plan_service import reset_due_credits_for_all_users
from app.services.monthly_metrics_service import (
    run_monthly_metrics_refresh,
    run_monthly_refresh_worker,
    recover_stale_monthly_jobs,
)
from app.services.webhook_credit_retry_service import run_webhook_credit_retry_job
from app.services.async_tracking_service import (
    recover_missed_callback_results,
    recover_stale_user_tracking_jobs,
)
from app.workers.refresh_worker import (
    recover_stale_processing_jobs,
    processing_job_ready_clause,
    PROCESSING_BATCH_SIZE,
)
from app.db.models import ProcessingJob
from app.queues.rank_check_queue import get_rank_check_queue
from app.workers.monday_tracker import run_monday_tracker
import logging

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def is_last_sunday_of_month(dt=None) -> bool:
    """Return True if the given datetime is the last Sunday of its month."""
    if dt is None:
        dt = datetime.now(scheduler.timezone)
    year = dt.year
    month = dt.month
    last_day = monthrange(year, month)[1]
    last_date = datetime(year, month, last_day)
    weekday = last_date.weekday()  # Monday=0 ... Sunday=6
    days_since_sunday = (weekday + 1) % 7
    last_sunday = last_date - timedelta(days=days_since_sunday)
    return dt.date() == last_sunday.date()


def run_weekly_job() -> None:
    """Legacy weekly job - runs on Monday morning."""
    db = SessionLocal()
    try:
        result = queue_weekly_tracking_for_all_projects(db)
        logger.info("Weekly tracking job completed: %s", result)
    except Exception as exc:
        logger.error("Weekly tracking job failed: %s", exc)
    finally:
        db.close()


def run_sunday_night_bulk_job() -> None:
    """Sunday night bulk async job for optimized rank tracking."""
    db = SessionLocal()
    try:
        if db.bind.dialect.name == "postgresql":
            acquired = db.execute(
                select(func.pg_try_advisory_xact_lock(hashtext('weekly_refresh_job')))
            ).scalar()
            if not acquired:
                logger.warning("Weekly refresh job already running, skipping")
                return
        
        collection_result = run_weekly_bulk_update_job(db)
        worker_result = run_weekly_refresh_worker(db)
        recovery_result = recover_stale_weekly_jobs(db)
        
        logger.info(
            "Sunday night bulk job completed: "
            "collection=%s, worker=%s, recovery=%s",
            collection_result, worker_result, recovery_result
        )
    except Exception as exc:
        logger.error("Sunday night bulk job failed: %s", exc)
    finally:
        db.close()


def run_monday_position_tracker() -> None:
    try:
        result = run_monday_tracker()
        logger.info("Monday position tracker completed: %s", result)
    except Exception as exc:
        logger.error("Monday position tracker failed: %s", exc)


def run_monthly_credit_refresh() -> None:
    """Daily job to reset monthly credits for users whose anniversary has passed."""
    db = SessionLocal()
    try:
        result = reset_due_credits_for_all_users(db)
        logger.info("Monthly credit refresh completed: %s", result)
    except Exception as exc:
        logger.error("Monthly credit refresh failed: %s", exc)
    finally:
        db.close()


def run_scheduler_monthly_metrics_refresh() -> None:
    """Monthly job to refresh keyword metrics (volume, kd, cpc, etc.) for all active users."""
    db = SessionLocal()
    try:
        result = run_monthly_metrics_refresh(db)
        logger.info("Monthly metrics refresh completed: %s", result)
    except Exception as exc:
        logger.error("Monthly metrics refresh failed: %s", exc)
    finally:
        db.close()


def run_last_sunday_monthly_metrics_job() -> None:
    """Run monthly metrics only on the last Sunday of the month."""
    if not is_last_sunday_of_month():
        return
    db = SessionLocal()
    try:
        if db.bind.dialect.name == "postgresql":
            acquired = db.execute(
                select(func.pg_try_advisory_xact_lock(hashtext('monthly_refresh_job')))
            ).scalar()
            if not acquired:
                logger.warning("Monthly refresh job already running, skipping")
                return
        
        collection_result = run_monthly_metrics_refresh(db)
        worker_result = run_monthly_refresh_worker(db)
        recovery_result = recover_stale_monthly_jobs(db)
        
        logger.info(
            "Last-Sunday monthly metrics refresh completed: "
            "collection=%s, worker=%s, recovery=%s",
            collection_result, worker_result, recovery_result
        )
    except Exception as exc:
        logger.error("Last-Sunday monthly metrics refresh failed: %s", exc)
    finally:
        db.close()


def run_user_tracking_recovery_job() -> None:
    """Recover durable user-tracking work after missed callbacks or worker/Redis restarts."""
    db = SessionLocal()
    try:
        missed_callback_recovery = recover_missed_callback_results(db)
        callback_recovery = recover_stale_user_tracking_jobs(db)
        worker_recovery = recover_stale_processing_jobs(db)
        ready_count = db.scalar(
            select(func.count())
            .select_from(ProcessingJob)
            .where(ProcessingJob.status.in_(["pending", "retry"]))
            .where(processing_job_ready_clause(db.get_bind().dialect.name))
        ) or 0

        recovery_batches = (
            (ready_count + PROCESSING_BATCH_SIZE - 1) // PROCESSING_BATCH_SIZE
            if ready_count
            else 0
        )
        additional_batches = max(
            0,
            recovery_batches - missed_callback_recovery["queue_enqueues"],
        )
        if additional_batches:
            queue = get_rank_check_queue()
            for _ in range(additional_batches):
                queue.enqueue(
                    "app.workers.tasks.process_refresh_jobs",
                    job_timeout="600",
                )

        logger.info(
            "User tracking recovery completed: task_get=%s callbacks=%s workers=%s ready=%s",
            missed_callback_recovery,
            callback_recovery,
            worker_recovery,
            ready_count,
        )
    except Exception as exc:
        logger.error("User tracking recovery failed: %s", exc)
    finally:
        db.close()


def start_scheduler() -> None:
    if not scheduler.running:
        # Sunday night bulk async job (11 PM Sunday)
        scheduler.add_job(
            run_sunday_night_bulk_job,
            trigger="cron",
            day_of_week="sun",
            hour=23,
            minute=0,
            id="sunday-night-bulk-job",
            replace_existing=True,
        )
        # Monday competitor tracker (2 AM Monday)
        scheduler.add_job(
            run_monday_position_tracker,
            trigger="cron",
            day_of_week="mon",
            hour=2,
            minute=0,
            id="monday-position-tracker",
            replace_existing=True,
        )
        # Monthly credit refresh (3 AM daily)
        scheduler.add_job(
            run_monthly_credit_refresh,
            trigger="cron",
            hour=3,
            minute=0,
            id="monthly-credit-refresh",
            replace_existing=True,
        )
        # Monthly keyword metrics refresh (1 AM on last Sunday of month)
        scheduler.add_job(
            run_last_sunday_monthly_metrics_job,
            trigger="cron",
            day_of_week="sun",
            hour=1,
            minute=0,
            id="monthly-metrics-refresh",
            replace_existing=True,
        )
        # Webhook credit retry (every 30 minutes)
        scheduler.add_job(
            run_webhook_credit_retry_job,
            trigger="interval",
            minutes=30,
            id="webhook-credit-retry",
            replace_existing=True,
        )
        scheduler.add_job(
            run_user_tracking_recovery_job,
            trigger="interval",
            minutes=5,
            id="user-tracking-recovery",
            replace_existing=True,
        )
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
