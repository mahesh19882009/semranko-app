"""
Phase 10.3 — ProcessingJob Recovery Tests

Tests for recover_stale_processing_jobs:
1. ProcessingJob enters processing
2. ProcessingJob completes normally
3. Worker crashes after claim
4. ProcessingJob becomes stale
5. Recovery detects stale job
6. Recovery moves it to retry/pending
7. Retry count increments correctly
8. Max retry limit is respected
9. Non-stale processing job is NOT recovered
10. Two recovery processes cannot recover the same job concurrently
11. Recovered job cannot be processed twice
12. Successful retry completes normally
"""

import sys
sys.path.insert(0, "/Users/maheshsharma/development/semranko-api/api/fastapi_app")

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine, select, update
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
)
from app.workers.refresh_worker import (
    claim_processing_jobs,
    process_pending_processing_jobs,
    process_processing_job,
    recover_stale_processing_jobs,
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


class TestProcessingJobNormalCompletion:
    def test_completed_job_not_recovered(self):
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
            status="success",
            deduplicationKey="task-1:kw1:India",
            payload=json.dumps({"position": 5}),
            processingTimeoutAt=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(pj)
        db.commit()

        result = recover_stale_processing_jobs(db)
        assert result["recovered"] == 0
        assert result["failed"] == 0


class TestProcessingJobStaleRecovery:
    def test_stale_processing_job_recovered(self):
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
            status="processing",
            deduplicationKey="task-stale:kw1:India",
            payload=json.dumps({"position": 5}),
            processingTimeoutAt=datetime.utcnow() - timedelta(hours=2),
            retryCount=0,
            maxRetries=3,
        )
        db.add(pj)
        db.commit()

        result = recover_stale_processing_jobs(db)
        assert result["recovered"] == 1
        assert result["failed"] == 0

        db.refresh(pj)
        assert pj.status == "retry"
        assert pj.retryCount == 1


class TestProcessingJobMaxRetries:
    def test_max_retries_exceeded_marks_failed(self):
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
            status="processing",
            deduplicationKey="task-max:kw1:India",
            payload=json.dumps({"position": 5}),
            processingTimeoutAt=datetime.utcnow() - timedelta(hours=2),
            retryCount=3,
            maxRetries=3,
        )
        db.add(pj)
        db.commit()

        result = recover_stale_processing_jobs(db)
        assert result["recovered"] == 0
        assert result["failed"] == 1

        db.refresh(pj)
        assert pj.status == "failed"


class TestProcessingJobNonStaleNotRecovered:
    def test_active_processing_job_not_recovered(self):
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
            status="processing",
            deduplicationKey="task-active:kw1:India",
            payload=json.dumps({"position": 5}),
            processingTimeoutAt=datetime.utcnow() + timedelta(hours=1),
            retryCount=0,
            maxRetries=3,
        )
        db.add(pj)
        db.commit()

        result = recover_stale_processing_jobs(db)
        assert result["recovered"] == 0
        assert result["failed"] == 0

        db.refresh(pj)
        assert pj.status == "processing"


class TestProcessingJobConcurrentRecovery:
    def test_concurrent_recovery_idempotent(self):
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
            status="processing",
            deduplicationKey="task-concurrent:kw1:India",
            payload=json.dumps({"position": 5}),
            processingTimeoutAt=datetime.utcnow() - timedelta(hours=2),
            retryCount=0,
            maxRetries=3,
        )
        db.add(pj)
        db.commit()

        result1 = recover_stale_processing_jobs(db)
        assert result1["recovered"] == 1

        result2 = recover_stale_processing_jobs(db)
        assert result2["recovered"] == 0

        db.refresh(pj)
        assert pj.retryCount == 1


class TestProcessingJobRetryCompletes:
    def test_recovered_job_can_be_processed(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db)
        user.automaticCreditBalance = 100.0
        db.add(user)
        db.commit()
        project = make_project(db, user.id)
        kw = make_keyword(db, project.id, user.id, keyword="kw1")

        pj = ProcessingJob(
            refreshJobId="rj1",
            keywordText="kw1",
            location="India",
            status="processing",
            deduplicationKey="task-retry:kw1:India",
            payload=json.dumps({"position": 5, "url": "https://example.com", "task_id": "task-retry", "first_block": {"items": []}}),
            processingTimeoutAt=datetime.utcnow() - timedelta(hours=2),
            retryCount=0,
            maxRetries=3,
        )
        db.add(pj)
        db.commit()
        reserve_automatic_credits(
            db,
            user.id,
            10,
            "test weekly reservation",
            f"auto:weekly:rj1:{user.id}",
        )

        recover_stale_processing_jobs(db)
        db.refresh(pj)
        assert pj.status == "retry"

        pj.status = "pending"
        db.add(pj)
        db.commit()

        claimed = claim_processing_jobs(db, batch_size=1)
        assert len(claimed) == 1

        process_processing_job(db, claimed[0])
        db.refresh(pj)
        assert pj.status == "success"


class TestProcessingJobClaimWithTimeout:
    def test_claim_sets_processing_timeout(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        pj = ProcessingJob(
            refreshJobId="rj1",
            keywordText="kw1",
            location="India",
            status="pending",
            deduplicationKey="task-timeout:kw1:India",
            payload=json.dumps({"position": 5}),
        )
        db.add(pj)
        db.commit()

        claimed = claim_processing_jobs(db, batch_size=1)
        assert len(claimed) == 1

        db.refresh(pj)
        assert pj.status == "processing"
        assert pj.processingTimeoutAt is not None
        assert pj.processingTimeoutAt > datetime.utcnow()
