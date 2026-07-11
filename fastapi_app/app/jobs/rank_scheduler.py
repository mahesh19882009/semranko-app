from apscheduler.schedulers.background import BackgroundScheduler

from app.db.session import SessionLocal
from app.services.ranking_service import queue_rank_checks_for_all_projects

scheduler = BackgroundScheduler()


def scheduled_rank_queue_job() -> None:
    db = SessionLocal()
    try:
        result = queue_rank_checks_for_all_projects(db)
        print("Scheduled rank queue job completed:", result)
    except Exception as exc:
        print("Scheduled rank queue job failed:", str(exc))
    finally:
        db.close()


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.add_job(
            scheduled_rank_queue_job,
            trigger="interval",
            minutes=2,
            id="daily-rank-queue-job",
            replace_existing=True,
        )
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()