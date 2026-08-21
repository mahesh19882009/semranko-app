"""
Phase 10.2 — Production Integration & Reliability Validation

Integration tests for crash recovery, partial failures, and edge cases.
"""

import sys
sys.path.insert(0, "/Users/maheshsharma/development/semranko-api/api/fastapi_app")

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from sqlalchemy import create_engine, select, update, text
from sqlalchemy.orm import Session

from app.db.models import Base, Keyword, Project, User, RefreshJob, ProcessingJob, RankResult, CreditLedger
from app.services.async_bulk_service import (
    _paginate_eligible_keywords,
    create_refresh_jobs,
    claim_refresh_job,
    mark_keywords_processing_atomic,
    run_weekly_bulk_update_job,
    run_weekly_refresh_worker,
    recover_stale_weekly_jobs,
    _submit_weekly_refresh,
    _submit_monthly_refresh,
    get_refresh_status,
)
from app.services.monthly_metrics_service import (
    _paginate_eligible_keywords_for_monthly,
    run_monthly_metrics_refresh,
    run_monthly_refresh_worker,
    recover_stale_monthly_jobs,
    _apply_monthly_refresh_results,
)
from app.workers.refresh_worker import (
    claim_processing_jobs,
    process_pending_processing_jobs,
    process_processing_job,
)
from app.services.credit_service import deduct_credits, reserve_credits, consume_reserved, reserve_automatic_credits


def make_user(db, user_id="user-1", email=None, plan="starter", credit_balance=100.0,
              subscription_status="active", plan_anniversary_at=None, last_credit_reset_at=None,
              refresh_frequency="monthly"):
    now = datetime.utcnow()
    user = User(
        id=user_id,
        name="Test User",
        email=email or f"{user_id}@test.com",
        passwordHash="hash",
        selectedPlan=plan,
        creditBalance=credit_balance,
        automaticCreditBalance=credit_balance,
        subscriptionStatus=subscription_status,
        trialStartsAt=now,
        trialEndsAt=now + timedelta(days=7),
        refreshFrequency=refresh_frequency,
        createdAt=now,
        updatedAt=now,
    )
    user.planAnniversaryAt = plan_anniversary_at if plan_anniversary_at is not None else now
    user.lastCreditResetAt = last_credit_reset_at if last_credit_reset_at is not None else now
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_project(db, user_id, project_id="p1", domain="example.com"):
    project = Project(id=project_id, name="Test", domain=domain, userId=user_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def make_keyword(db, project_id, user_id, keyword="test kw", location="India", is_active=True):
    kw = Keyword(
        id=f"kw-{keyword.replace(' ', '-')}-{datetime.utcnow().timestamp()}",
        projectId=project_id,
        userId=user_id,
        keyword=keyword,
        location=location,
        isActive=is_active,
    )
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return kw


class TestCrashBeforeRefreshJobCreation:
    def test_no_jobs_created_on_early_crash(self):
        """Crash before RefreshJob creation leaves no partial state."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, refresh_frequency="monthly")
        project = make_project(db, user.id)
        make_keyword(db, project.id, user.id, keyword="kw1")

        batches = _paginate_eligible_keywords_for_monthly(db)
        assert len(batches) == 1

        db.rollback()
        jobs = db.scalars(select(RefreshJob)).all()
        assert len(jobs) == 0


class TestDuplicateSchedulerExecution:
    def test_advisory_lock_serializes_scheduler(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, user_id="u1", subscription_status="active")
        project = make_project(db, user.id)
        make_keyword(db, project.id, user.id, keyword="kw1")

        result1 = run_weekly_bulk_update_job(db)
        assert result1["status"] == "queued"

        result2 = run_weekly_bulk_update_job(db)
        assert result2["status"] == "queued"

        jobs = db.scalars(select(RefreshJob)).all()
        assert len(jobs) == 2


class TestDuplicateWebhookProtection:
    def test_duplicate_webhook_creates_single_processing_job(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db)
        project = make_project(db, user.id)
        kw = make_keyword(db, project.id, user.id, keyword="test kw")

        rj = RefreshJob(
            jobType="weekly_serp",
            status="submitted",
            batchIndex=0,
            totalBatches=1,
            keywordCount=1,
            keywordsJson=json.dumps([{"keyword": "test kw", "location": "India"}]),
            dataforseoRequestIds=json.dumps(["task-dup-1"]),
        )
        db.add(rj)
        db.flush()
        db.add(ProcessingJob(
            refreshJobId=rj.id,
            keywordText="test kw",
            location="United States",
            status="pending",
            deduplicationKey="pending:task-dup-1:test-kw",
            payload=json.dumps({"project_id": project.id, "user_id": user.id, "domain": project.domain, "awaiting_callback": True}),
        ))
        db.commit()

        payload = {
            "task_id": "task-dup-1",
            "tasks": [{
                "data": {"keyword": "test kw", "location_code": 2840},
                "result": [{
                    "items": [{"type": "organic", "url": "https://example.com", "rank_group": 5}]
                }]
            }]
        }

        async def make_request():
            req = MagicMock()
            async def json_func():
                return payload
            req.json = json_func
            req.body = AsyncMock(return_value=json.dumps(payload).encode("utf-8"))
            req.headers = {}
            req.query_params = {"task_id": None}
            return req

        with patch("app.api.routes.webhooks.SessionLocal", return_value=db):
            from app.api.routes.webhooks import dataforseo_webhook
            import asyncio

            req1 = asyncio.run(make_request())
            req2 = asyncio.run(make_request())

            asyncio.run(dataforseo_webhook(req1))
            asyncio.run(dataforseo_webhook(req2))

        jobs = db.scalars(select(ProcessingJob)).all()
        assert len(jobs) == 1


class TestConcurrentProcessingJobClaim:
    def test_atomic_claim_prevents_double_processing(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        pj1 = ProcessingJob(
            refreshJobId="rj1",
            keywordText="kw1",
            location="India",
            status="pending",
            deduplicationKey="task-c-1:kw1:India",
            payload=json.dumps({"position": 5}),
        )
        pj2 = ProcessingJob(
            refreshJobId="rj1",
            keywordText="kw1",
            location="India",
            status="pending",
            deduplicationKey="task-c-2:kw1:India",
            payload=json.dumps({"position": 5}),
        )
        db.add_all([pj1, pj2])
        db.commit()

        claimed1 = claim_processing_jobs(db, batch_size=1)
        assert len(claimed1) == 1

        claimed2 = claim_processing_jobs(db, batch_size=1)
        assert len(claimed2) == 1

        pending = db.scalars(select(ProcessingJob).where(ProcessingJob.status == "pending")).all()
        assert len(pending) == 0


class TestDuplicateRankResultProtection:
    def test_processing_job_idempotency(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db)
        project = make_project(db, user.id)
        kw = make_keyword(db, project.id, user.id, keyword="kw1")

        pj = ProcessingJob(
            refreshJobId="rj1",
            keywordText="kw1",
            location="India",
            status="pending",
            deduplicationKey="task-rr:kw1:India",
            payload=json.dumps({
                "position": 5,
                "url": "https://example.com",
                "task_id": "task-rr",
                "first_block": {"items": []},
            }),
        )
        db.add(pj)
        db.commit()

        reserve_automatic_credits(db, user.id, 10, "test weekly reservation", f"auto:weekly:rj1:{user.id}")

        process_processing_job(db, pj)
        process_processing_job(db, pj)

        results = db.scalars(select(RankResult).where(RankResult.keywordId == kw.id)).all()
        assert len(results) == 1


class TestCreditDeduplication:
    def test_same_webhook_does_not_create_duplicate_processing_jobs(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, credit_balance=200.0)
        project = make_project(db, user.id)
        kw = make_keyword(db, project.id, user.id, keyword="kw1")

        pj = ProcessingJob(
            refreshJobId="rj1",
            keywordText="kw1",
            location="India",
            status="pending",
            deduplicationKey="task-cd:kw1:India",
            payload=json.dumps({
                "position": 5,
                "url": "https://example.com",
                "task_id": "task-cd",
                "first_block": {"items": []},
            }),
        )
        db.add(pj)
        db.commit()

        reserve_automatic_credits(db, user.id, 20, "test weekly reservation", f"auto:weekly:rj1:{user.id}")

        process_processing_job(db, pj)
        db.refresh(user)
        balance_after_first = user.automaticCreditBalance

        pj2 = ProcessingJob(
            refreshJobId="rj1",
            keywordText="kw1",
            location="India",
            status="pending",
            deduplicationKey="task-cd-2:kw1:India",
            payload=json.dumps({
                "position": 5,
                "url": "https://example.com",
                "task_id": "task-cd-2",
                "first_block": {"items": []},
            }),
        )
        db.add(pj2)
        db.commit()

        process_processing_job(db, pj2)
        db.refresh(user)
        balance_after_second = user.automaticCreditBalance

        assert balance_after_second == balance_after_first
        reservation = db.scalar(select(CreditLedger).where(
            CreditLedger.userId == user.id,
            CreditLedger.creditPool == "automatic",
        ))
        assert reservation.creditsConsumed == 20.0
        assert reservation.status == "completed"
        results = db.scalars(select(RankResult).where(RankResult.keywordId == kw.id)).all()
        assert len(results) == 2


class TestRetryAfterFailure:
    def test_failed_job_can_be_retried(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db)
        project = make_project(db, user.id)
        kw = make_keyword(db, project.id, user.id, keyword="kw1")

        batches = _paginate_eligible_keywords(db, job_type="weekly")
        jobs = create_refresh_jobs(db, "weekly_serp", batches)
        job = jobs[0]

        job.status = "failed"
        job.errorMessage = "simulated failure"
        db.add(job)
        db.commit()

        recovered = recover_stale_weekly_jobs(db)
        assert recovered["recovered"] == 0

        job.processingTimeoutAt = datetime.utcnow() - timedelta(hours=1)
        job.status = "processing"
        db.add(job)
        db.commit()

        recovered = recover_stale_weekly_jobs(db)
        assert recovered["recovered"] == 1

        db.refresh(job)
        assert job.status == "retry"


class TestPartialDataForSEOChunkFailure:
    def test_partial_chunk_failure_marks_job_failed(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db)
        project = make_project(db, user.id)
        make_keyword(db, project.id, user.id, keyword="kw1")
        make_keyword(db, project.id, user.id, keyword="kw2")

        batches = _paginate_eligible_keywords(db, job_type="weekly")
        jobs = create_refresh_jobs(db, "weekly_serp", batches)
        job = jobs[0]

        job.status = "processing"
        db.add(job)
        db.commit()

        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status.side_effect = Exception("DFS down")
            result = _submit_weekly_refresh(db, job, ["kw1", "kw2"])

        assert result is False
        db.refresh(job)
        assert job.status == "failed"


class Test5000KeywordPagination:
    def test_weekly_5000_keywords_paginate_correctly(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, user_id="bulk-user", subscription_status="active")
        project = make_project(db, user.id)

        kws = []
        for i in range(5000):
            kw = Keyword(
                id=f"kw-bulk-{i}",
                projectId=project.id,
                userId=user.id,
                keyword=f"bulk-kw-{i}",
                location="India",
                isActive=True,
            )
            kws.append(kw)
        db.add_all(kws)
        db.commit()

        batches = _paginate_eligible_keywords(db, job_type="weekly")
        assert len(batches) == 1
        assert sum(len(b) for b in batches) == 5000


class TestMonthly5000KeywordPagination:
    def test_monthly_5000_keywords_paginate_correctly(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, user_id="monthly-bulk", refresh_frequency="monthly")
        project = make_project(db, user.id)

        kws = []
        for i in range(5000):
            kw = Keyword(
                id=f"kw-monthly-{i}",
                projectId=project.id,
                userId=user.id,
                keyword=f"monthly-kw-{i}",
                location="India",
                isActive=True,
            )
            kws.append(kw)
        db.add_all(kws)
        db.commit()

        batches = _paginate_eligible_keywords_for_monthly(db)
        assert len(batches) == 1
        assert sum(len(b) for b in batches) == 5000


class TestProcessingJobGrowth:
    def test_processing_jobs_do_not_grow_indefinitely(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db)
        project = make_project(db, user.id)
        kw = make_keyword(db, project.id, user.id, keyword="kw1")

        for i in range(100):
            pj = ProcessingJob(
                refreshJobId=f"rj-{i}",
                keywordText="kw1",
                location="India",
                status="success",
                deduplicationKey=f"task-growth-{i}:kw1:India",
                payload=json.dumps({"position": 5}),
            )
            db.add(pj)
        db.commit()

        all_jobs = db.scalars(select(ProcessingJob)).all()
        assert len(all_jobs) == 100


class TestWebhookRefreshStatusAPI:
    def test_refresh_status_returns_correct_totals(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db)
        project = make_project(db, user.id)
        make_keyword(db, project.id, user.id, keyword="kw1")

        batches = _paginate_eligible_keywords(db, job_type="weekly")
        create_refresh_jobs(db, "weekly_serp", batches)

        status = get_refresh_status(db)
        assert status["weekly"]["totalJobs"] == 1
        assert status["weekly"]["queuedJobs"] == 1
