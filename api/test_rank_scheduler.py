"""Zero-cost scheduler registration and calendar-boundary checks."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, Keyword, Project, User
from app.jobs import rank_scheduler
from app.services.async_bulk_service import _paginate_eligible_keywords
from app.services.monthly_metrics_service import _paginate_eligible_keywords_for_monthly


def test_scheduler_registers_expected_jobs_and_starts_once():
    scheduler_mock = MagicMock()
    scheduler_mock.running = False

    with patch.object(rank_scheduler, "scheduler", scheduler_mock):
        rank_scheduler.start_scheduler()

    registered = {
        call.kwargs["id"]: call.kwargs
        for call in scheduler_mock.add_job.call_args_list
    }
    assert set(registered) == {
        "sunday-night-bulk-job",
        "monday-position-tracker",
        "monthly-credit-refresh",
        "monthly-metrics-refresh",
        "webhook-credit-retry",
        "user-tracking-recovery",
    }
    assert registered["sunday-night-bulk-job"]["day_of_week"] == "sun"
    assert registered["sunday-night-bulk-job"]["hour"] == 23
    assert registered["sunday-night-bulk-job"]["minute"] == 0
    assert registered["sunday-night-bulk-job"]["trigger"] == "cron"
    assert registered["monthly-metrics-refresh"]["day_of_week"] == "sun"
    assert registered["monthly-metrics-refresh"]["hour"] == 1
    assert registered["monthly-metrics-refresh"]["minute"] == 0
    assert registered["monthly-metrics-refresh"]["trigger"] == "cron"
    assert registered["sunday-night-bulk-job"]["misfire_grace_time"] == (
        rank_scheduler.SCHEDULED_REFRESH_MISFIRE_GRACE_SECONDS
    )
    assert registered["monthly-metrics-refresh"]["misfire_grace_time"] == (
        rank_scheduler.SCHEDULED_REFRESH_MISFIRE_GRACE_SECONDS
    )
    assert "misfire_grace_time" not in registered["webhook-credit-retry"]
    assert "misfire_grace_time" not in registered["user-tracking-recovery"]
    assert all(item["replace_existing"] is True for item in registered.values())
    scheduler_mock.start.assert_called_once_with()


def test_scheduler_defaults_keep_single_instance_and_coalesced_execution():
    assert rank_scheduler.scheduler._job_defaults["misfire_grace_time"] == 1
    assert rank_scheduler.scheduler._job_defaults["max_instances"] == 1
    assert rank_scheduler.scheduler._job_defaults["coalesce"] is True


def test_last_sunday_guard_handles_month_and_year_boundaries():
    assert rank_scheduler.is_last_sunday_of_month(datetime(2026, 2, 22)) is True
    assert rank_scheduler.is_last_sunday_of_month(datetime(2026, 2, 15)) is False
    assert rank_scheduler.is_last_sunday_of_month(datetime(2026, 3, 29)) is True
    assert rank_scheduler.is_last_sunday_of_month(datetime(2026, 12, 27)) is True
    assert rank_scheduler.is_last_sunday_of_month(datetime(2027, 1, 31)) is True


def test_monthly_guard_uses_scheduler_timezone_and_does_not_open_db_when_false():
    with patch.object(rank_scheduler, "is_last_sunday_of_month", return_value=False), \
         patch.object(rank_scheduler, "SessionLocal") as session_local:
        rank_scheduler.run_last_sunday_monthly_metrics_job()

    session_local.assert_not_called()


def test_scheduler_shutdown_is_safe_when_not_running():
    scheduler_mock = MagicMock()
    scheduler_mock.running = False

    with patch.object(rank_scheduler, "scheduler", scheduler_mock):
        rank_scheduler.stop_scheduler()

    scheduler_mock.shutdown.assert_not_called()


def _shared_keyword_db(refresh_frequency):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    for index in (1, 2):
        user = User(
            id=f"scheduler-u{index}",
            name=f"Scheduler User {index}",
            email=f"scheduler-{index}@example.com",
            passwordHash="hash",
            selectedPlan="starter",
            subscriptionStatus="active",
            refreshFrequency=refresh_frequency,
            creditBalance=100,
            automaticCreditBalance=100,
        )
        project = Project(
            id=f"scheduler-p{index}",
            name=f"Scheduler Project {index}",
            domain=f"example-{index}.com",
            userId=user.id,
        )
        keyword = Keyword(
            id=f"scheduler-k{index}",
            projectId=project.id,
            userId=user.id,
            keyword="shared scheduled keyword",
            location="India",
            isActive=True,
        )
        db.add_all([user, project, keyword])
    db.commit()
    return engine, db


def test_weekly_collection_deduplicates_across_page_boundaries():
    engine, db = _shared_keyword_db("weekly")
    try:
        with patch("app.services.async_bulk_service.REFRESH_JOB_BATCH_SIZE", 1):
            batches = _paginate_eligible_keywords(db, job_type="weekly")
        entries = [entry for batch in batches for entry in batch]
        assert [(entry["keyword"], entry["location"]) for entry in entries] == [
            ("shared scheduled keyword", "India")
        ]
        assert {row["keyword_id"] for row in entries[0]["eligible_rows"]} == {
            "scheduler-k1", "scheduler-k2"
        }
    finally:
        db.close()
        engine.dispose()


def test_monthly_collection_deduplicates_across_page_boundaries():
    engine, db = _shared_keyword_db("monthly")
    try:
        batches = _paginate_eligible_keywords_for_monthly(db, batch_size=1)
        entries = [entry for batch in batches for entry in batch]
        assert [(entry["keyword"], entry["location"]) for entry in entries] == [
            ("shared scheduled keyword", "India")
        ]
        assert {row["keyword_id"] for row in entries[0]["eligible_rows"]} == {
            "scheduler-k1", "scheduler-k2"
        }
    finally:
        db.close()
        engine.dispose()
