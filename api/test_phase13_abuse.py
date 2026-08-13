"""
Phase 13 — Profitability, Abuse Protection & Financial Safety Tests

Tests for:
- Bulk keyword billing (20 credits)
- Monthly refresh multi-user billing
- Manual refresh rate limiting
- Manual refresh cooldown
- Manual refresh daily limit
- DFS cost ceiling
- Orphaned retry job recovery
- Keyword count consistency
- OTP session_id storage
"""

import sys
sys.path.insert(0, "/Users/maheshsharma/development/rankcare-api/api/fastapi_app")

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select, func, or_
from sqlalchemy.orm import Session

from app.db.models import Base, Keyword, Project, User, RefreshJob, CreditLedger, ProcessingJob, DataForSEOCost
from app.services.keyword_service import add_keyword, add_keywords_bulk, delete_keyword, count_user_keywords
from app.services.plan_service import count_user_active_keywords
from app.services.keyword_update_service import refresh_keyword_data
from app.services.credit_service import deduct_credits, reserve_credits, consume_reserved, refund_reserved, reserve_automatic_credits
from app.services.otp_service import send_otp, verify_otp, _normalize_mobile
from app.services.dataforseo_client import check_dfs_cost_ceiling
from app.services.plan_service import ensure_keyword_limit
from app.core.errors import ApiError
from app.core.config import get_settings


def make_user(db, user_id="user-1", email=None, plan="starter", credit_balance=100.0,
              subscription_status="active", refresh_frequency="monthly", is_verified=True, mobile_verified=False):
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
        isVerified=is_verified,
        mobileVerified=mobile_verified,
    )
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


class TestBulkKeywordBilling:
    def test_bulk_add_charges_bulk_cost(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, plan="starter", credit_balance=1000.0)
        project = make_project(db, user.id)

        with patch("app.services.keyword_service.DataForSEOClient.fetch_dashboard_data") as mock_fetch:
            mock_fetch.return_value = [
                {"keyword": "bulk kw1", "volume": 100, "kd": 10, "cpc": 1.0, "competition": 0.5, "backlinks": 10, "referring_domains": 5, "intent": "informational"},
                {"keyword": "bulk kw2", "volume": 100, "kd": 10, "cpc": 1.0, "competition": 0.5, "backlinks": 10, "referring_domains": 5, "intent": "informational"},
            ]
            result = add_keywords_bulk(db, user.id, project.id, ["bulk kw1", "bulk kw2"], location="India")
            assert result["added"] == 2

        db.refresh(user)
        assert user.creditBalance == 1000.0 - (2 * 20)

    def test_single_add_charges_single_cost(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, plan="starter", credit_balance=1000.0)
        project = make_project(db, user.id)

        with patch("app.services.keyword_service.DataForSEOClient.fetch_dashboard_data") as mock_fetch:
            mock_fetch.return_value = [{"keyword": "single kw", "volume": 100, "kd": 10, "cpc": 1.0, "competition": 0.5, "backlinks": 10, "referring_domains": 5, "intent": "informational"}]
            result = add_keyword(db, user.id, project.id, {"keyword": "single kw", "location": "India"})
            assert result["keyword"] == "single kw"

        db.refresh(user)
        assert user.creditBalance == 1000.0 - 20


class TestMonthlyRefreshMultiUserBilling:
    def test_monthly_refresh_charges_all_users(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user1 = make_user(db, user_id="user-m1", email="m1@test.com", plan="starter", credit_balance=100.0)
        user2 = make_user(db, user_id="user-m2", email="m2@test.com", plan="starter", credit_balance=100.0)
        project1 = make_project(db, user1.id, project_id="p-m1")
        project2 = make_project(db, user2.id, project_id="p-m2")
        make_keyword(db, project1.id, user1.id, keyword="shared kw", location="India")
        make_keyword(db, project2.id, user2.id, keyword="shared kw", location="India")

        from app.services.monthly_metrics_service import _apply_monthly_refresh_results
        job = RefreshJob(
            id="job-multi",
            jobType="monthly_metrics",
            status="success",
            keywordsJson=json.dumps([{"keyword": "shared kw", "location": "India"}]),
            resultSummary=json.dumps({
                "results": {"shared kw": {"volume": 1000, "kd": 20, "cpc": 2.0, "competition": 0.8, "backlinks": 50, "referring_domains": 10, "intent": "commercial"}},
            }),
        )
        db.add(job)
        db.commit()

        reserve_automatic_credits(db, user1.id, 10, "monthly test reservation", f"auto:monthly:{job.id}:{user1.id}")
        reserve_automatic_credits(db, user2.id, 10, "monthly test reservation", f"auto:monthly:{job.id}:{user2.id}")

        _apply_monthly_refresh_results(db, job)

        db.refresh(user1)
        db.refresh(user2)
        assert user1.creditBalance == 100.0
        assert user2.creditBalance == 100.0
        assert user1.automaticCreditBalance == 90.0
        assert user2.automaticCreditBalance == 90.0


class TestManualRefreshAbuse:
    def test_manual_refresh_cooldown(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, credit_balance=1000.0)
        project = make_project(db, user.id)
        kw = make_keyword(db, project.id, user.id, keyword="cooldown kw")
        kw.lastWeeklyRefreshAt = datetime.utcnow() - timedelta(minutes=30)
        db.add(kw)
        db.commit()

        result = refresh_keyword_data(db, user.id, project.id, keyword_ids=[kw.id])
        assert result["success"] is True
        assert result["skipped"] == 1

    def test_legacy_daily_ledger_rows_do_not_define_billing_cycle_allowance(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, credit_balance=1000.0)
        project = make_project(db, user.id)
        kw = make_keyword(db, project.id, user.id, keyword="daily limit kw")

        for i in range(50):
            ledger = CreditLedger(
                userId=user.id,
                ownerId=user.id,
                amount=-10.0,
                actionType="charge",
                description=f"Keyword refresh: 1 keyword(s) for project {project.id}",
                timestamp=datetime.utcnow() - timedelta(hours=1),
            )
            db.add(ledger)
        db.commit()

        with patch("app.services.keyword_update_service.DataForSEOClient.fetch_dashboard_data") as fetch:
            fetch.return_value = [{"keyword": kw.keyword, "position": 5, "volume": 100}]
            result = refresh_keyword_data(db, user.id, project.id, keyword_ids=[kw.id])
        assert result["success"] is True
        assert result["updated"] == 1
        assert result["usage"]["used"] == 1

    def test_manual_refresh_rate_limit(self):
        from app.core.rate_limiter import MemoryRateLimiter

        limiter = MemoryRateLimiter()
        key = "refresh_project_keywords:127.0.0.1"
        for _ in range(10):
            assert limiter.is_allowed(key, 10, 60) is True
        assert limiter.is_allowed(key, 10, 60) is False


class TestDFSCostCeiling:
    def test_dfs_ceiling_blocks_call(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, plan="starter", credit_balance=1000.0)

        cost = DataForSEOCost(
            userId=user.id,
            taskType="weekly_serp",
            endpoint="/serp/google/organic/task_post",
            costCredits=0,
            costUsd=24.0,
        )
        db.add(cost)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            check_dfs_cost_ceiling(db, user.id, 2.0)
        assert exc_info.value.status_code == 403

    def test_dfs_ceiling_allows_call_under_limit(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, plan="starter", credit_balance=1000.0)

        cost = DataForSEOCost(
            userId=user.id,
            taskType="weekly_serp",
            endpoint="/serp/google/organic/task_post",
            costCredits=0,
            costUsd=10.0,
        )
        db.add(cost)
        db.commit()

        check_dfs_cost_ceiling(db, user.id, 5.0)


class TestOrphanedRetryRecovery:
    def test_retry_jobs_are_claimed_by_worker(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        refresh_job = RefreshJob(id="rj-retry", jobType="weekly_serp", status="queued")
        db.add(refresh_job)
        db.commit()

        job = ProcessingJob(
            id="proc-retry",
            refreshJobId="rj-retry",
            keywordText="test kw",
            location="India",
            deduplicationKey="proc-retry:test kw:India",
            status="retry",
            retryCount=0,
            maxRetries=3,
            payload=json.dumps({"test": True}),
        )
        db.add(job)
        db.commit()

        from app.workers.refresh_worker import claim_processing_jobs
        claimed = claim_processing_jobs(db, batch_size=10)
        assert len(claimed) == 1
        assert claimed[0].id == "proc-retry"

    def test_failed_jobs_not_claimed(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        refresh_job = RefreshJob(id="rj-failed", jobType="weekly_serp", status="queued")
        db.add(refresh_job)
        db.commit()

        job = ProcessingJob(
            id="proc-failed",
            refreshJobId="rj-failed",
            keywordText="test kw",
            location="India",
            deduplicationKey="proc-failed:test kw:India",
            status="failed",
            retryCount=3,
            maxRetries=3,
            payload=json.dumps({"test": True}),
        )
        db.add(job)
        db.commit()

        from app.workers.refresh_worker import claim_processing_jobs
        claimed = claim_processing_jobs(db, batch_size=10)
        assert len(claimed) == 0


class TestKeywordCountConsistency:
    def test_count_user_keywords_matches_limit_enforcement(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, plan="free_trial")
        project = make_project(db, user.id)

        for i in range(5):
            kw = Keyword(
                id=f"kw-consistency-{i}",
                projectId=project.id,
                userId=user.id,
                keyword=f"consistency kw {i}",
                location="India",
                isActive=True,
            )
            db.add(kw)
        db.commit()

        count1 = count_user_keywords(db, user.id)
        count2 = db.scalar(
            select(func.count())
            .select_from(Keyword)
            .join(Project, Keyword.projectId == Project.id)
            .where(Project.userId == user.id)
            .where(or_(Keyword.isActive == True, Keyword.deletedAt.is_(None)))
        ) or 0

        assert count1 == count2


class TestOTPSessionStorage:
    def test_send_otp_stores_session_id_not_otp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, is_verified=True, mobile_verified=False)

        with patch("app.services.otp_service.requests.get") as mock_get:
            with patch("app.services.otp_service.settings") as mock_settings:
                mock_settings.TWOFACTOR_API_KEY = "test-api-key"
                mock_response = MagicMock()
                mock_response.json.return_value = {"Status": "Success", "SessionId": "session-123", "OTP": "654321"}
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response

                result = send_otp(db, user.id, "+919876543210")
                assert result["session_id"] == "session-123"

        db.refresh(user)
        assert user.mobileVerificationOtp == "session-123"
        assert "654321" not in str(user.mobileVerificationOtp)
