"""Regression coverage for exact scheduled-refresh row identity."""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import (
    Base,
    Keyword,
    KeywordMetricsHistory,
    ProcessingJob,
    Project,
    RefreshJob,
    User,
)
from app.services.async_bulk_service import (
    run_weekly_bulk_update_job,
    run_weekly_refresh_worker,
)
from app.services.monthly_metrics_service import (
    _apply_monthly_refresh_results,
    _paginate_eligible_keywords_for_monthly,
    run_monthly_metrics_refresh,
    run_monthly_refresh_worker,
)


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def _duplicate_rows(db, *, refresh_frequency):
    rows = []
    for index in ("a", "b"):
        user = User(
            id=f"identity-user-{index}",
            name=f"Identity User {index}",
            email=f"identity-{index}@example.com",
            passwordHash="hash",
            selectedPlan="starter",
            subscriptionStatus="active",
            refreshFrequency=refresh_frequency,
            creditBalance=100,
            automaticCreditBalance=100,
        )
        project = Project(
            id=f"identity-project-{index}",
            name=f"Identity Project {index}",
            domain=f"identity-{index}.example.com",
            userId=user.id,
        )
        keyword = Keyword(
            id=f"identity-keyword-{index}",
            projectId=project.id,
            userId=user.id,
            keyword="same scheduled keyword",
            location="India",
            isActive=True,
            volume=10 if index == "a" else 20,
            lastWeeklyRefreshAt=(
                None if index == "a" else datetime.utcnow() - timedelta(days=1)
            ),
            lastMonthlyMetricsRefreshAt=(
                None if index == "a" else datetime.utcnow() - timedelta(days=1)
            ),
        )
        db.add_all([user, project, keyword])
        rows.append((user, project, keyword))
    db.commit()
    return rows


def _provider_response():
    response = MagicMock()
    response.headers = {"Content-Type": "application/json"}
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "tasks": [{
            "id": "mock-scheduled-task",
            "data": {"keyword": "same scheduled keyword"},
            "result": [{
                "items": [{
                    "keyword": "same scheduled keyword",
                    "keyword_properties": {"keyword_difficulty": 33},
                    "keyword_info": {
                        "search_volume": 99,
                        "cpc": 1.5,
                        "competition": 0.4,
                    },
                    "avg_backlinks_info": {
                        "backlinks": 12,
                        "referring_domains": 4,
                    },
                    "search_intent_info": {"main_intent": "commercial"},
                }],
            }],
        }],
    }
    return response


def test_weekly_submission_keeps_only_due_row_identity():
    engine, db = _db()
    try:
        rows = _duplicate_rows(db, refresh_frequency="weekly")
        result = run_weekly_bulk_update_job(db)
        job = db.get(RefreshJob, result["job_ids"][0])

        with patch("app.services.async_bulk_service._build_postback_url", return_value="https://example.test/callback"), \
             patch("app.services.dataforseo_client._get_cached_serp", return_value=None), \
             patch("app.services.async_bulk_service.requests.post", return_value=_provider_response()):
            worker_result = run_weekly_refresh_worker(db)

        assert worker_result["processed"] == 1
        children = db.scalars(
            select(ProcessingJob).where(ProcessingJob.refreshJobId == job.id)
        ).all()
        assert len(children) == 1
        payload = json.loads(children[0].payload)
        assert payload["keyword_id"] == rows[0][2].id
        assert rows[1][2].weeklyRefreshStatus is None
        assert rows[0][0].automaticCreditBalance == 90
        assert rows[1][0].automaticCreditBalance == 100
    finally:
        db.close()
        engine.dispose()


def test_monthly_application_keeps_only_due_row_identity():
    engine, db = _db()
    try:
        rows = _duplicate_rows(db, refresh_frequency="monthly")
        result = run_monthly_metrics_refresh(db)

        with patch("app.services.dataforseo_client._get_cached_kw_metrics", return_value=None), \
             patch("app.services.dataforseo_client._set_cached_kw_metrics"), \
             patch("app.services.async_bulk_service.requests.post", return_value=_provider_response()):
            worker_result = run_monthly_refresh_worker(db)

        assert worker_result["processed"] == 1
        due = db.get(Keyword, rows[0][2].id)
        cooling_down = db.get(Keyword, rows[1][2].id)
        assert due.volume == 99
        assert cooling_down.volume == 20
        assert db.scalar(
            select(KeywordMetricsHistory).where(
                KeywordMetricsHistory.keywordId == due.id
            )
        ) is not None
        assert db.scalar(
            select(KeywordMetricsHistory).where(
                KeywordMetricsHistory.keywordId == cooling_down.id
            )
        ) is None
        assert rows[0][0].automaticCreditBalance == 90
        assert rows[1][0].automaticCreditBalance == 100
    finally:
        db.close()
        engine.dispose()


def test_monthly_identity_metadata_aggregates_duplicate_rows_across_pages():
    engine, db = _db()
    try:
        rows = _duplicate_rows(db, refresh_frequency="monthly")
        rows[1][2].lastMonthlyMetricsRefreshAt = None
        db.commit()
        batches = _paginate_eligible_keywords_for_monthly(db, batch_size=1)
        assert len(batches) == 1
        assert len(batches[0]) == 1
        assert len(batches[0][0]["eligible_rows"]) == 2
    finally:
        db.close()
        engine.dispose()


def test_monthly_identity_application_is_idempotent():
    engine, db = _db()
    try:
        rows = _duplicate_rows(db, refresh_frequency="monthly")
        result = run_monthly_metrics_refresh(db)

        with patch("app.services.dataforseo_client._get_cached_kw_metrics", return_value=None), \
             patch("app.services.dataforseo_client._set_cached_kw_metrics"), \
             patch("app.services.async_bulk_service.requests.post", return_value=_provider_response()):
            run_monthly_refresh_worker(db)

        job = db.get(RefreshJob, result["job_ids"][0])
        history_before = db.scalars(
            select(KeywordMetricsHistory).where(
                KeywordMetricsHistory.keywordId == rows[0][2].id
            )
        ).all()
        balance_before = db.get(User, rows[0][0].id).automaticCreditBalance
        _apply_monthly_refresh_results(db, job)
        history_after = db.scalars(
            select(KeywordMetricsHistory).where(
                KeywordMetricsHistory.keywordId == rows[0][2].id
            )
        ).all()
        assert len(history_before) == len(history_after) == 1
        assert db.get(User, rows[0][0].id).automaticCreditBalance == balance_before
    finally:
        db.close()
        engine.dispose()
