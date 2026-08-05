from apscheduler.schedulers.background import BackgroundScheduler

from app.db.session import SessionLocal
from app.services.ranking_service import queue_weekly_tracking_for_all_projects
from app.workers.monday_tracker import run_monday_tracker

scheduler = BackgroundScheduler()


def run_weekly_job() -> None:
    db = SessionLocal()
    try:
        result = queue_weekly_tracking_for_all_projects(db)
        print("Weekly tracking job completed:", result)
    except Exception as exc:
        print("Weekly tracking job failed:", str(exc))
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
        scheduler.add_job(
            run_weekly_job,
            trigger="cron",
            day_of_week="mon",
            hour=1,
            minute=0,
            id="weekly-monday-job",
            replace_existing=True,
        )
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
