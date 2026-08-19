import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, "/Users/maheshsharma/development/semranko-api/api/fastapi_app")

from app.db.models import Base, User, Subscription, Project, Keyword, CreditLedger, KeywordMetricsHistory, RankResult
from app.services.plan_service import (
    PLAN_DEFINITIONS,
    get_effective_plan_key,
    reset_due_credits_for_all_users,
    change_user_plan,
)
from app.services.credit_service import deduct_credits
from app.services.monthly_metrics_service import run_monthly_metrics_refresh
from app.services.keyword_update_service import refresh_keyword_data
from app.services.async_bulk_service import create_async_bulk_task, submit_bulk_to_dataforseo
from app.utils.change_indicators import compute_change, keyword_change
from app.core.errors import ApiError


def make_user(db: Session, user_id="user-1", email=None, plan="starter", credit_balance=0.0, subscription_status="active", plan_anniversary_at=None, last_credit_reset_at=None, refresh_frequency="monthly"):
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


class TestPhase4aMonthlyMetricsRefresh:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.now = datetime.utcnow()

    def teardown_method(self):
        self.db.close()

    @patch("app.services.async_bulk_service.requests.post")
    def test_monthly_refresh_only_active_users(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tasks": [{
                "result": [{
                    "items": [{
                        "keyword": "test keyword",
                        "keyword_properties": {"keyword_difficulty": 50},
                        "keyword_info": {"search_volume": 1000, "cpc": 1.5, "competition": 0.8},
                        "avg_backlinks_info": {"backlinks": 100, "referring_domains": 20},
                        "search_intent_info": {"main_intent": "informational"},
                    }]
                }]
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        user_active = make_user(self.db, user_id="user-active", subscription_status="active", plan_anniversary_at=self.now - timedelta(days=40), credit_balance=100.0)
        user_trial = make_user(self.db, user_id="user-trial", email="trial@test.com", subscription_status="trialing", plan_anniversary_at=self.now - timedelta(days=40), credit_balance=100.0)
        user_inactive = make_user(self.db, user_id="user-inactive", email="inactive@test.com", subscription_status="inactive", plan_anniversary_at=self.now - timedelta(days=40), credit_balance=100.0)
        
        project = Project(id="p1", name="Test", domain="test.com", userId=user_active.id)
        self.db.add(project)
        kw = Keyword(id="k1", projectId=project.id, userId=user_active.id, keyword="test keyword", location="India", isActive=True)
        self.db.add(kw)
        self.db.commit()
        
        result = run_monthly_metrics_refresh(self.db)
        
        assert result["status"] == "queued"
        assert len(result.get("job_ids", [])) == 1
        
        from app.services.monthly_metrics_service import run_monthly_refresh_worker
        worker_result = run_monthly_refresh_worker(self.db)
        assert worker_result["processed"] == 1
        
        self.db.refresh(kw)
        assert kw.lastMonthlyMetricsRefreshAt is not None

    @patch("app.services.async_bulk_service.requests.post")
    def test_monthly_refresh_respects_refresh_frequency(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tasks": [{
                "result": [{
                    "items": [{
                        "keyword": "monthly kw",
                        "keyword_properties": {"keyword_difficulty": 50},
                        "keyword_info": {"search_volume": 1000, "cpc": 1.5, "competition": 0.8},
                        "avg_backlinks_info": {"backlinks": 100, "referring_domains": 20},
                        "search_intent_info": {"main_intent": "informational"},
                    }]
                }]
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        user_weekly = make_user(self.db, user_id="user-weekly", refresh_frequency="weekly", plan_anniversary_at=self.now - timedelta(days=40), credit_balance=100.0)
        user_monthly = make_user(self.db, user_id="user-monthly", email="monthly@test.com", refresh_frequency="monthly", plan_anniversary_at=self.now - timedelta(days=40), credit_balance=100.0)
        
        project1 = Project(id="p1", name="Test1", domain="test1.com", userId=user_weekly.id)
        project2 = Project(id="p2", name="Test2", domain="test2.com", userId=user_monthly.id)
        self.db.add_all([project1, project2])
        kw1 = Keyword(id="k1", projectId=project1.id, userId=user_weekly.id, keyword="weekly kw", isActive=True)
        kw2 = Keyword(id="k2", projectId=project2.id, userId=user_monthly.id, keyword="monthly kw", isActive=True)
        self.db.add_all([kw1, kw2])
        self.db.commit()
        
        result = run_monthly_metrics_refresh(self.db)
        
        assert result["status"] == "queued"
        assert len(result.get("job_ids", [])) == 1
        
        from app.services.monthly_metrics_service import run_monthly_refresh_worker
        worker_result = run_monthly_refresh_worker(self.db)
        assert worker_result["processed"] == 1
        
        from app.db.models import RefreshJob
        job = self.db.scalar(select(RefreshJob).where(RefreshJob.id == result["job_ids"][0]))
        print(f"TEST DEBUG: job_status={job.status}, result_summary={job.resultSummary[:200] if job.resultSummary else None}")
        
        self.db.refresh(kw1)
        self.db.refresh(kw2)
        print(f"TEST DEBUG: kw1.lastMonthlyMetricsRefreshAt={kw1.lastMonthlyMetricsRefreshAt}, kw2.lastMonthlyMetricsRefreshAt={kw2.lastMonthlyMetricsRefreshAt}")
        assert kw1.lastMonthlyMetricsRefreshAt is None
        assert kw2.lastMonthlyMetricsRefreshAt is not None

    @patch("app.services.async_bulk_service.requests.post")
    def test_monthly_refresh_creates_history(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tasks": [{
                "result": [{
                    "items": [{
                        "keyword": "test keyword",
                        "keyword_properties": {"keyword_difficulty": 50},
                        "keyword_info": {"search_volume": 1000, "cpc": 1.5, "competition": 0.8},
                        "avg_backlinks_info": {"backlinks": 100, "referring_domains": 20},
                        "search_intent_info": {"main_intent": "informational"},
                    }]
                }]
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        user = make_user(self.db, plan_anniversary_at=self.now - timedelta(days=40), credit_balance=100.0)
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        kw = Keyword(id="k1", projectId=project.id, userId=user.id, keyword="test keyword", location="India", isActive=True, volume=1000, kd=50)
        self.db.add(kw)
        self.db.commit()
        
        result = run_monthly_metrics_refresh(self.db)
        assert result["status"] == "queued"
        
        from app.services.monthly_metrics_service import run_monthly_refresh_worker
        worker_result = run_monthly_refresh_worker(self.db)
        assert worker_result["processed"] == 1
        
        history = self.db.scalars(
            select(KeywordMetricsHistory).where(KeywordMetricsHistory.keywordId == kw.id)
        ).all()
        assert len(history) == 1
        assert history[0].volume == 1000
        assert history[0].kd == 50

    @patch("app.services.async_bulk_service.requests.post")
    def test_monthly_refresh_charges_credits(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tasks": [{
                "result": [{
                    "items": [{
                        "keyword": "test keyword",
                        "keyword_properties": {"keyword_difficulty": 50},
                        "keyword_info": {"search_volume": 1000, "cpc": 1.5, "competition": 0.8},
                        "avg_backlinks_info": {"backlinks": 100, "referring_domains": 20},
                        "search_intent_info": {"main_intent": "informational"},
                    }]
                }]
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        user = make_user(self.db, credit_balance=100.0, plan_anniversary_at=self.now - timedelta(days=40))
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        kw = Keyword(id="k1", projectId=project.id, userId=user.id, keyword="test keyword", location="India", isActive=True)
        self.db.add(kw)
        self.db.commit()
        
        result = run_monthly_metrics_refresh(self.db)
        assert result["status"] == "queued"
        
        from app.services.monthly_metrics_service import run_monthly_refresh_worker
        worker_result = run_monthly_refresh_worker(self.db)
        assert worker_result["processed"] == 1
        
        self.db.refresh(user)
        assert user.creditBalance == 100.0
        assert user.automaticCreditBalance == 90.0


class TestPhase4bCreditReservation:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_reserve_and_consume_credits(self):
        from app.services.credit_service import reserve_credits, consume_reserved, get_credit_balance
        
        user = make_user(self.db, credit_balance=100.0)
        
        reserve_credits(self.db, user.id, 30.0, "test", "Test reservation", reference="test-ref-1")
        self.db.refresh(user)
        assert user.creditBalance == 70.0
        
        consume_reserved(self.db, user.id, "test-ref-1", 30.0, action_type="charge")
        self.db.refresh(user)
        assert user.creditBalance == 70.0

    def test_refund_reserved_credits(self):
        from app.services.credit_service import reserve_credits, refund_reserved, get_credit_balance
        
        user = make_user(self.db, credit_balance=100.0)
        
        reserve_credits(self.db, user.id, 30.0, "test", "Test reservation", reference="test-ref-2")
        self.db.refresh(user)
        assert user.creditBalance == 70.0
        
        refund_reserved(self.db, user.id, "test-ref-2", 30.0, description="Test refund")
        self.db.refresh(user)
        assert user.creditBalance == 100.0


class TestPhase4cChangeIndicators:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_compute_change_position(self):
        result = compute_change(5, 4, lower_is_better=True)
        assert result is not None
        assert result["previous"] == 4
        assert result["current"] == 5
        assert result["difference"] == 1.0
        assert result["direction"] == "down"
        assert result["isPositive"] is False

    def test_compute_change_volume(self):
        result = compute_change(12000, 10000, lower_is_better=False)
        assert result is not None
        assert result["previous"] == 10000
        assert result["current"] == 12000
        assert result["difference"] == 2000.0
        assert result["direction"] == "up"
        assert result["isPositive"] is True

    def test_compute_change_none_returns_none(self):
        result = compute_change(None, 5)
        assert result is None

    def test_keyword_change_integration(self):
        current = {"position": 5, "volume": 12000, "kd": 42}
        previous = {"position": 4, "volume": 10000, "kd": 35}
        changes = keyword_change(current, previous)
        
        assert "position" in changes
        assert changes["position"]["direction"] == "down"
        assert changes["position"]["isPositive"] is False
        
        assert "volume" in changes
        assert changes["volume"]["direction"] == "up"
        assert changes["volume"]["isPositive"] is True
        
        assert "kd" in changes
        assert changes["kd"]["direction"] == "up"
        assert changes["kd"]["isPositive"] is True


class TestPhase4WeeklyJobFixes:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_monday_tracker_does_not_update_keyword_positions(self):
        user_active = make_user(self.db, user_id="user-active", subscription_status="active", credit_balance=10.0)
        user_trial = make_user(self.db, user_id="user-trial", email="trial@test.com", subscription_status="trialing")
        
        project_active = Project(id="p1", name="Test", domain="test.com", userId=user_active.id)
        project_trial = Project(id="p2", name="Test2", domain="test2.com", userId=user_trial.id)
        self.db.add_all([project_active, project_trial])
        
        kw_active = Keyword(id="k1", projectId=project_active.id, userId=user_active.id, keyword="active kw", isActive=True)
        kw_inactive = Keyword(id="k2", projectId=project_active.id, userId=user_active.id, keyword="inactive kw", isActive=False)
        kw_trial = Keyword(id="k3", projectId=project_trial.id, userId=user_trial.id, keyword="trial kw", isActive=True)
        self.db.add_all([kw_active, kw_inactive, kw_trial])
        self.db.commit()
        
        kw_active_id = kw_active.id
        kw_inactive_id = kw_inactive.id
        kw_trial_id = kw_trial.id
        
        from unittest.mock import patch, MagicMock
        with patch("app.workers.monday_tracker.SessionLocal") as MockSessionLocal, \
             patch("app.services.competitor_rank_service.track_competitor_rankings") as mock_comp:
            MockSessionLocal.return_value = self.db
            mock_comp.return_value = {"tracked": 0}
            
            from app.workers.monday_tracker import run_monday_tracker
            result = run_monday_tracker()
    
        assert result["updated_keywords"] == 0
        refreshed_kw = self.db.scalar(select(Keyword).where(Keyword.id == kw_active_id))
        assert refreshed_kw.position is None
        refreshed_inactive = self.db.scalar(select(Keyword).where(Keyword.id == kw_inactive_id))
        assert refreshed_inactive.position is None
        refreshed_trial = self.db.scalar(select(Keyword).where(Keyword.id == kw_trial_id))
        assert refreshed_trial.position is None

    def test_webhook_only_active_users(self):
        from app.api.routes.webhooks import dataforseo_webhook
        from fastapi import Request
        from unittest.mock import patch, MagicMock
        import asyncio
        
        user_active = make_user(self.db, user_id="user-active", subscription_status="active")
        user_trial = make_user(self.db, user_id="user-trial", email="trial@test.com", subscription_status="trialing")
        
        project_active = Project(id="p1", name="Test", domain="test.com", userId=user_active.id)
        project_trial = Project(id="p2", name="Test2", domain="test2.com", userId=user_trial.id)
        self.db.add_all([project_active, project_trial])
        
        kw_active = Keyword(id="k1", projectId=project_active.id, userId=user_active.id, keyword="test kw", location="Global", isActive=True)
        kw_trial = Keyword(id="k2", projectId=project_trial.id, userId=user_trial.id, keyword="test kw", location="Global", isActive=True)
        self.db.add_all([kw_active, kw_trial])
        self.db.commit()
        
        class FakeRequest:
            async def json(self):
                return {
                    "task_id": "task-1",
                    "tasks": [{
                        "data": {"keyword": "test kw", "location_code": 2840},
                        "result": [{
                            "items": [{"type": "organic", "url": "https://example.com", "rank_group": 5}]
                        }]
                    }]
                }
            def __init__(self):
                self.query_params = MagicMock()
                self.query_params.get.return_value = None
        
        mock_request = FakeRequest()
        
        from app.db.models import AsyncTaskQueue, RefreshJob
        async_task = AsyncTaskQueue(
            taskType="rank_tracking",
            status="processing",
            keywordsJson='[{"keyword": "test kw", "location": "India"}]',
            userId=user_active.id,
            projectId=project_active.id,
        )
        self.db.add(async_task)
        
        refresh_job = RefreshJob(
            jobType="weekly_serp",
            status="submitted",
            batchIndex=0,
            totalBatches=1,
            keywordCount=1,
            keywordsJson='[{"keyword": "test kw", "location": "India"}]',
            dataforseoRequestIds='["task-1"]',
        )
        self.db.add(refresh_job)
        self.db.commit()
        
        kw_active_id = kw_active.id
        kw_trial_id = kw_trial.id
        
        with patch("app.api.routes.webhooks.SessionLocal") as MockSessionLocal, \
             patch("app.services.credit_service.settings") as mock_settings:
            MockSessionLocal.return_value = self.db
            mock_settings.plan_config.credit_costs = {"weekly_refresh_per_keyword": 10}
    
            result = asyncio.run(dataforseo_webhook(mock_request))
    
        assert result["created"] == 1
        from app.db.models import ProcessingJob
        jobs = self.db.scalars(select(ProcessingJob)).all()
        assert len(jobs) == 1
        assert jobs[0].keywordText == "test kw"
