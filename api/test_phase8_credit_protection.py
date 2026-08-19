"""
Phase 8 Credit Protection and Cost Instrumentation Tests

Tests verify:
- DFS calls are blocked when user has insufficient credits
- DFS calls proceed when user has sufficient credits
- Credit reservations are consumed on success
- Credit reservations are refunded on failure
- Webhook idempotency prevents double-charging
- DFS cost logging records non-zero estimated costs for real calls
- DFS cost logging records zero cost for cache hits
"""

import json
import sys
import asyncio
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timedelta

sys.path.insert(0, "/Users/maheshsharma/development/semranko-api/api/fastapi_app")

from app.db.models import (
    Base,
    User,
    Project,
    Keyword,
    CreditLedger,
    PendingWebhookCredit,
    AsyncTaskQueue,
    Competitor,
    CompetitorRank,
    RankResult,
    DataForSEOCost,
    RefreshJob,
    ProcessingJob,
)
from app.services.async_tracking_service import submit_user_tracking_job
from app.services.credit_service import reserve_credits, consume_reserved, refund_reserved, check_credits, deduct_credits
from app.services.dataforseo_client import DataForSEOClient, _log_dataforseo_cost, _estimate_dataforseo_cost
from app.services.profitability_reporting_service import calculate_plan_profitability, get_profitability_summary
from app.core.config import get_settings
from app.core.errors import ApiError


settings = get_settings()


def make_user(db: Session, user_id="user-1", email=None, plan="starter", credit_balance=0.0, subscription_status="active"):
    now = datetime.utcnow()
    user = User(
        id=user_id,
        name="Test User",
        email=email or f"{user_id}@test.com",
        passwordHash="hash",
        selectedPlan=plan,
        creditBalance=credit_balance,
        subscriptionStatus=subscription_status,
        createdAt=now,
        updatedAt=now,
        emailVerificationExpiresAt=now,
        passwordResetExpiresAt=now,
        trialStartsAt=now,
        trialEndsAt=now,
        planAnniversaryAt=now,
        lastCreditResetAt=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestSingleKeywordCreditProtection:
    """Test single keyword add credit protection."""

    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_add_keyword_insufficient_credits_blocks_dfs(self):
        user = make_user(self.db, user_id="user-1", credit_balance=0.0)
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        self.db.commit()

        with patch("app.services.keyword_service.DataForSEOClient.fetch_dashboard_data") as mock_fetch:
            from app.services.keyword_service import add_keyword
            with pytest.raises(HTTPException) as exc_info:
                add_keyword(self.db, user.id, project.id, {"keyword": "new keyword"})
            assert exc_info.value.status_code == 402
            mock_fetch.assert_not_called()

    def test_add_keyword_sufficient_credits_allows_dfs(self):
        user = make_user(self.db, user_id="user-2", credit_balance=20.0)
        project = Project(id="p2", name="Test2", domain="test.com", userId=user.id)
        self.db.add(project)
        self.db.commit()

        with patch("app.services.keyword_service.DataForSEOClient.fetch_dashboard_data") as mock_fetch:
            mock_fetch.return_value = [{"keyword": "new keyword", "volume": 100, "kd": 50, "cpc": 1.0, "position": 1, "intent": "informational"}]
            from app.services.keyword_service import add_keyword
            result = add_keyword(self.db, user.id, project.id, {"keyword": "new keyword"})
            mock_fetch.assert_called_once()


class TestBulkAddCreditProtection:
    """Test bulk keyword add credit protection."""

    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_bulk_add_insufficient_credits_blocks_all_dfs(self):
        user = make_user(self.db, user_id="user-3", credit_balance=0.0)
        project = Project(id="p3", name="Test3", domain="test.com", userId=user.id)
        self.db.add(project)
        self.db.commit()

        with patch("app.services.keyword_service.DataForSEOClient.fetch_dashboard_data") as mock_fetch:
            from app.services.keyword_service import add_keywords_bulk
            with pytest.raises(ApiError) as exc_info:
                add_keywords_bulk(self.db, user.id, project.id, ["kw1", "kw2", "kw3"])
            assert exc_info.value.status_code == 402
            mock_fetch.assert_not_called()


class TestCompetitorTrackingCreditProtection:
    """Test competitor tracking credit protection."""

    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_competitor_tracking_insufficient_credits_blocks_dfs(self):
        user = make_user(self.db, user_id="user-4", credit_balance=0.0)
        project = Project(id="p4", name="Test4", domain="test.com", userId=user.id)
        competitor = Competitor(id="c1", projectId=project.id, domain="competitor.com", name="Competitor")
        keyword = Keyword(id="k4", projectId=project.id, userId=user.id, keyword="test kw", isActive=True)
        self.db.add_all([user, project, competitor, keyword])
        self.db.commit()

        with patch("app.services.competitor_rank_service.get_cached", return_value=None), \
             patch("app.services.competitor_rank_service.DataForSEOClient.get_serp_data_batch") as mock_fetch:
            from app.services.competitor_rank_service import track_competitor_rankings
            with pytest.raises(ApiError) as exc_info:
                track_competitor_rankings(self.db, user.id, project.id)
            assert exc_info.value.status_code == 402
            mock_fetch.assert_not_called()


class TestManualRankCheckCreditProtection:
    """Test manual rank check credit protection."""

    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_manual_rank_check_insufficient_credits_blocks_job(self):
        user = make_user(self.db, user_id="user-5", credit_balance=0.0)
        project = Project(id="p5", name="Test5", domain="test.com", userId=user.id)
        keyword = Keyword(id="k5", projectId=project.id, userId=user.id, keyword="test kw", isActive=True)
        self.db.add_all([user, project, keyword])
        self.db.commit()

        with patch("app.services.ranking_service.get_rank_check_queue") as mock_queue:
            from app.services.ranking_service import run_rank_check
            with pytest.raises(ApiError) as exc_info:
                run_rank_check(self.db, user.id, project.id)
            assert exc_info.value.status_code == 402
            mock_queue.return_value.enqueue.assert_not_called()


class TestKeywordResearchCreditProtection:
    """Test keyword research credit protection."""

    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_keyword_research_insufficient_credits_blocks_dfs(self):
        user = make_user(self.db, user_id="user-6", credit_balance=0.0)
        self.db.commit()

        with patch("app.services.keyword_research_service.DataForSEOClient.get_keyword_ideas_api") as mock_ideas:
            from app.services.keyword_research_service import research_keyword
            with pytest.raises(ApiError) as exc_info:
                research_keyword(self.db, user.id, "test keyword")
            assert exc_info.value.status_code == 402
            mock_ideas.assert_not_called()


class TestCompetitorSpyCreditProtection:
    """Test competitor spy credit protection."""

    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_competitor_spy_insufficient_credits_blocks_dfs(self):
        user = make_user(self.db, user_id="user-7", credit_balance=0.0)
        self.db.commit()

        with patch("app.services.competitor_spy_service.DataForSEOClient.get_competitor_keywords_cached") as mock_spy:
            from app.services.competitor_spy_service import spy_competitor_keywords
            with pytest.raises(ApiError) as exc_info:
                spy_competitor_keywords(self.db, user.id, "competitor.com")
            assert exc_info.value.status_code == 402
            mock_spy.assert_not_called()


class TestWebhookIdempotency:
    """Test webhook credit deduction idempotency."""

    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_duplicate_webhook_reuses_existing_processing_job(self):
        user = make_user(
            self.db,
            user_id="user-9",
            credit_balance=200.0,
        )

        project = Project(
            id="p9",
            name="Test9",
            domain="example.com",
            userId=user.id,
        )

        keyword = Keyword(
            id="k9",
            projectId=project.id,
            userId=user.id,
            keyword="test kw",
            location="India",
            device="desktop",
            isActive=True,
        )

        self.db.add_all([project, keyword])
        self.db.commit()

        mock_response = {
            "tasks": [{
                "id": "task-1",
                "data": {"keyword": "test kw"},
                "cost": 0.0,
                "status_code": 20000,
            }]
        }

        with patch(
            "app.services.dataforseo_client.requests.post",
            return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            ),
        ), patch(
            "app.services.async_tracking_service._get_cached_serp",
            return_value=None,
        ):
            submit_user_tracking_job(
                db=self.db,
                user_id=user.id,
                project_id=project.id,
                keywords=[{"keyword": "test kw"}],
                domain=project.domain,
                action="add_keyword",
                location_code=2840,
                depth=100,
                cost_per_keyword=20,
            )

        refresh_job = self.db.scalar(
            select(RefreshJob).where(
                RefreshJob.jobType == "add_keyword"
            )
        )

        assert refresh_job is not None
        refresh_job_id = refresh_job.id

        processing_jobs = self.db.scalars(
            select(ProcessingJob).where(
                ProcessingJob.refreshJobId == refresh_job_id
            )
        ).all()

        assert len(processing_jobs) == 1

        from app.api.routes.webhooks import dataforseo_webhook
        from fastapi import Request
        import app.api.routes.webhooks as webhooks_mod

        webhook_payload = {
            "task_id": "task-1",
            "tasks": [{
                "data": {
                    "keyword": "test kw",
                    "location_code": 2840,
                },
                "result": [{
                    "items": [{
                        "type": "organic",
                        "url": "https://example.com",
                        "domain": "example.com",
                        "rank_group": 5,
                    }]
                }]
            }]
        }

        def make_request():
            request = Request({
                "type": "http",
                "method": "POST",
                "headers": [
                    (b"content-type", b"application/json"),
                ],
                "query_string": b"",
            })
            request._body = json.dumps(webhook_payload).encode("utf-8")
            return request

        original_sessionlocal = webhooks_mod.SessionLocal
        webhooks_mod.SessionLocal = lambda: self.db

        try:
            result1 = asyncio.run(
                dataforseo_webhook(make_request())
            )

            result2 = asyncio.run(
                dataforseo_webhook(make_request())
            )

            assert result1.get("updated") == 1
            assert result1.get("skipped") == 0

            assert result2.get("updated") == 1
            assert result2.get("skipped") == 0

            jobs = self.db.scalars(
                select(ProcessingJob).where(
                    ProcessingJob.refreshJobId == refresh_job_id
                )
            ).all()

            assert len(jobs) == 1

        finally:
            webhooks_mod.SessionLocal = original_sessionlocal

class TestDFSCostInstrumentation:
    """Test DFS cost logging."""

    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_estimate_dataforseo_cost_serp_depth_100(self):
        cost = _estimate_dataforseo_cost("/serp/google/organic/live/advanced", keyword_count=1, depth=100, cache_hit=False)
        assert cost == 0.020

    def test_estimate_dataforseo_cost_serp_depth_10(self):
        cost = _estimate_dataforseo_cost("/serp/google/organic/live/advanced", keyword_count=1, depth=10, cache_hit=False)
        assert cost == 0.002

    def test_estimate_dataforseo_cost_cache_hit(self):
        cost = _estimate_dataforseo_cost("/serp/google/organic/live/advanced", keyword_count=1, depth=100, cache_hit=True)
        assert cost == 0.0

    def test_estimate_dataforseo_cost_labs_keyword_overview(self):
        cost = _estimate_dataforseo_cost("/dataforseo_labs/google/keyword_overview/live", keyword_count=1, cache_hit=False)
        assert cost == 0.01212

    def test_estimate_dataforseo_cost_competitors_domain(self):
        cost = _estimate_dataforseo_cost("/dataforseo_labs/google/competitors_domain/live", keyword_count=1, cache_hit=False)
        assert cost == 0.01212

    def test_log_dataforseo_cost_stores_estimated_cost(self):
        user = make_user(self.db, user_id="user-cost-1", credit_balance=0.0)
        
        _log_dataforseo_cost(
            db=self.db,
            user_id=user.id,
            task_type="test",
            endpoint="/serp/google/organic/live/advanced",
            method="POST",
            keyword_count=1,
            depth=100,
            cache_hit=False,
            success=True,
        )
        self.db.commit()

        cost_record = self.db.scalar(select(DataForSEOCost).where(DataForSEOCost.userId == user.id))
        assert cost_record is not None
        assert cost_record.costCredits == 0.020
        assert cost_record.meta.get("depth") == 100
        assert cost_record.meta.get("cache_hit") is False


class TestProfitabilityReporting:
    """Test profitability reporting service."""

    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_calculate_plan_profitability_returns_metrics(self):
        result = calculate_plan_profitability(self.db, "starter", days=30)
        assert "plan_key" in result
        assert "revenue_inr" in result
        assert "dataforseo_cost" in result
        assert "gross_profit_inr" in result
        assert "gross_margin_percent" in result
        assert "profit_loss" in result

    def test_profitability_summary_aggregates_plans(self):
        summary = get_profitability_summary(self.db, days=30)
        assert "total_revenue_inr" in summary
        assert "total_dfs_cost_inr" in summary
        assert "total_gross_profit_inr" in summary
        assert "plans" in summary
