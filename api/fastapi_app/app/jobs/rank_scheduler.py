from apscheduler.schedulers.background import BackgroundScheduler

from app.db.session import SessionLocal
from app.services.ranking_service import queue_weekly_tracking_for_all_projects
from app.services.async_bulk_service import run_weekly_bulk_update_job
from app.workers.monday_tracker import run_monday_tracker

scheduler = BackgroundScheduler()


def run_weekly_job() -> None:
    """Legacy weekly job - runs on Monday morning."""
    db = SessionLocal()
    try:
        result = queue_weekly_tracking_for_all_projects(db)
        print("Weekly tracking job completed:", result)
    except Exception as exc:
        print("Weekly tracking job failed:", str(exc))
    finally:
        db.close()


def run_sunday_night_bulk_job() -> None:
    """New Sunday night bulk async job for optimized rank tracking."""
    db = SessionLocal()
    try:
        result = run_weekly_bulk_update_job(db)
        print("Sunday night bulk job completed:", result)
    except Exception as exc:
        print("Sunday night bulk job failed:", str(exc))
    finally:
        db.close()


def run_monday_position_tracker() -> None:
    try:
        result = run_monday_tracker()
        print("Monday position tracker completed:", result)
    except Exception as exc:
        print("Monday position tracker failed:", str(exc))


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
        # Legacy Monday morning job (1 AM Monday) - can be removed after testing
        scheduler.add_job(
            run_weekly_job,
            trigger="cron",
            day_of_week="mon",
            hour=1,
            minute=0,
            id="weekly-monday-job",
            replace_existing=True,
        )
        # Monday position tracker (2 AM Monday)
        scheduler.add_job(
            run_monday_position_tracker,
            trigger="cron",
            day_of_week="mon",
            hour=2,
            minute=0,
            id="monday-position-tracker",
            replace_existing=True,
        )
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
