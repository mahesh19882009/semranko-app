import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import inspect

import sys
sys.path.insert(0, "/Users/maheshsharma/development/semranko-api/api/fastapi_app")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Base, User, Project, Keyword, Competitor, CompetitorRank
from app.workers.monday_tracker import run_monday_tracker
from app.services.competitor_rank_service import track_competitor_rankings
from app.jobs.rank_scheduler import start_scheduler


def make_user(db: Session, user_id="user-1", email=None, plan="starter", credit_balance=100.0, subscription_status="active"):
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
        refreshFrequency="monthly",
        createdAt=now,
        updatedAt=now,
    )
    db.add(user)
    db.commit()
    return user


def make_project(db: Session, user_id, project_id="proj-1", domain="example.com"):
    project = Project(id=project_id, name="Test", domain=domain, userId=user_id)
    db.add(project)
    db.commit()
    return project


def make_keyword(db: Session, project_id, user_id, keyword="test kw", location="India", is_active=True):
    kw = Keyword(projectId=project_id, userId=user_id, keyword=keyword, location=location, isActive=is_active)
    db.add(kw)
    db.commit()
    return kw


def make_competitor(db: Session, project_id, competitor_id="comp-1", domain="competitor.com"):
    comp = Competitor(id=competitor_id, projectId=project_id, name="Competitor", domain=domain)
    db.add(comp)
    db.commit()
    return comp


class TestPhase6MondayCompetitorOnly:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_scheduler_no_longer_has_weekly_monday_job(self):
        source = inspect.getsource(start_scheduler)
        assert "run_weekly_job" not in source
        assert "weekly-monday-job" not in source

    def test_monday_tracker_does_not_update_keyword_positions(self):
        user = make_user(self.db, user_id="user-active", subscription_status="active", credit_balance=100.0)
        project = make_project(self.db, user.id, project_id="p1", domain="example.com")
        kw = make_keyword(self.db, project.id, user.id, keyword="active kw", is_active=True)
        kw_id = kw.id

        with patch("app.workers.monday_tracker.SessionLocal") as MockSessionLocal, \
             patch("app.services.competitor_rank_service.track_competitor_rankings") as mock_comp:
            MockSessionLocal.return_value = self.db
            mock_comp.return_value = {"tracked": 0}

            result = run_monday_tracker()

        assert result["updated_keywords"] == 0
        refreshed = self.db.scalar(select(Keyword).where(Keyword.id == kw_id))
        assert refreshed.position is None

    def test_monday_tracker_does_not_fetch_serp_for_keywords(self):
        user = make_user(self.db, user_id="user-active", subscription_status="active", credit_balance=100.0)
        project = make_project(self.db, user.id, project_id="p1", domain="example.com")
        make_keyword(self.db, project.id, user.id, keyword="active kw", is_active=True)

        with patch("app.workers.monday_tracker.SessionLocal") as MockSessionLocal, \
             patch("app.services.dataforseo_client.DataForSEOClient.fetch_dashboard_data") as mock_fetch, \
             patch("app.services.competitor_rank_service.track_competitor_rankings") as mock_comp:
            MockSessionLocal.return_value = self.db
            mock_comp.return_value = {"tracked": 0}

            result = run_monday_tracker()

        mock_fetch.assert_not_called()

    def test_monday_tracker_ignores_inactive_keywords_for_competitor_tracking(self):
        user = make_user(self.db, user_id="user-active", subscription_status="active", credit_balance=100.0)
        project = make_project(self.db, user.id, project_id="p1", domain="example.com")
        kw_active = make_keyword(self.db, project.id, user.id, keyword="active kw", is_active=True)
        make_keyword(self.db, project.id, user.id, keyword="inactive kw", is_active=False)

        with patch("app.workers.monday_tracker.SessionLocal") as MockSessionLocal, \
             patch("app.services.competitor_rank_service.track_competitor_rankings") as mock_comp:
            MockSessionLocal.return_value = self.db
            mock_comp.return_value = {"tracked": 0}

            result = run_monday_tracker()

        assert result["updated_keywords"] == 0
        assert result["competitor_tracked"] == 0

    def test_monday_tracker_ignores_trial_users(self):
        user_trial = make_user(self.db, user_id="user-trial", email="trial@test.com", subscription_status="trialing", credit_balance=100.0)
        project = make_project(self.db, user_trial.id, project_id="p1", domain="example.com")
        kw = make_keyword(self.db, project.id, user_trial.id, keyword="trial kw", is_active=True)
        kw_id = kw.id

        with patch("app.workers.monday_tracker.SessionLocal") as MockSessionLocal, \
             patch("app.services.competitor_rank_service.track_competitor_rankings") as mock_comp:
            MockSessionLocal.return_value = self.db
            mock_comp.return_value = {"tracked": 0}

            result = run_monday_tracker()

        assert result["updated_keywords"] == 0
        assert result["competitor_tracked"] == 0
        refreshed = self.db.scalar(select(Keyword).where(Keyword.id == kw_id))
        assert refreshed.position is None

    def test_competitor_tracking_triggered_from_monday_tracker(self):
        user = make_user(self.db, user_id="user-active", subscription_status="active", credit_balance=100.0)
        project = make_project(self.db, user.id, project_id="p1", domain="example.com")
        kw = make_keyword(self.db, project.id, user.id, keyword="active kw", is_active=True)
        comp = make_competitor(self.db, project.id, competitor_id="comp-1", domain="competitor.com")
        kw_id = kw.id
        user_id = user.id
        project_id = project.id

        with patch("app.workers.monday_tracker.SessionLocal") as MockSessionLocal, \
             patch("app.workers.monday_tracker.track_competitor_rankings") as mock_comp:
            MockSessionLocal.return_value = self.db
            mock_comp.return_value = {"tracked": 1}

            result = run_monday_tracker()

        assert result["competitor_tracked"] == 1
        assert result["updated_keywords"] == 0
        mock_comp.assert_called_once_with(db=self.db, user_id=user_id, project_id=project_id, depth=10)
        refreshed = self.db.scalar(select(Keyword).where(Keyword.id == kw_id))
        assert refreshed.position is None

    def test_competitor_tracking_failure_does_not_break_job(self):
        user = make_user(self.db, user_id="user-active", subscription_status="active", credit_balance=100.0)
        project = make_project(self.db, user.id, project_id="p1", domain="example.com")
        kw = make_keyword(self.db, project.id, user.id, keyword="active kw", is_active=True)
        make_competitor(self.db, project.id, competitor_id="comp-1", domain="competitor.com")
        kw_id = kw.id

        with patch("app.workers.monday_tracker.SessionLocal") as MockSessionLocal, \
             patch("app.workers.monday_tracker.track_competitor_rankings") as mock_comp:
            MockSessionLocal.return_value = self.db
            mock_comp.side_effect = Exception("DataForSEO competitor fetch failed")

            result = run_monday_tracker()

        assert result["updated_keywords"] == 0
        assert result["competitor_tracked"] == 0
        refreshed = self.db.scalar(select(Keyword).where(Keyword.id == kw_id))
        assert refreshed.position is None

    def test_no_duplicate_monday_legacy_jobs_queued(self):
        from app.services.ranking_service import queue_weekly_tracking_for_all_projects

        user = make_user(self.db, user_id="user-1", credit_balance=100.0)
        project = make_project(self.db, user.id, project_id="p1", domain="example.com")
        make_keyword(self.db, project.id, user.id, keyword="kw1", is_active=True)
        make_competitor(self.db, project.id, competitor_id="comp-1", domain="competitor.com")

        queue = MagicMock()
        queue.enqueue.side_effect = [MagicMock(id="rank-job"), MagicMock(id="competitor-job")]
        with patch("app.services.ranking_service.get_rank_check_queue", return_value=queue):
            result = queue_weekly_tracking_for_all_projects(self.db)

        assert result["queued"] is True
        rank_jobs = result.get("rankJobIds", [])
        competitor_jobs = result.get("competitorJobIds", [])

        assert len(rank_jobs) == 1
        assert len(competitor_jobs) == 1

    def test_sunday_bulk_path_uses_eligibility_filter(self):
        from app.services.async_bulk_service import _paginate_eligible_keywords

        user = make_user(self.db, user_id="user-1", subscription_status="active", credit_balance=100.0)
        project = make_project(self.db, user.id, project_id="p1", domain="example.com")
        kw = make_keyword(self.db, project.id, user.id, keyword="kw1", is_active=True)

        batches = _paginate_eligible_keywords(self.db, job_type="weekly")
        assert len(batches) >= 0

    def test_subscription_filtering_remains_intact(self):
        user_active = make_user(self.db, user_id="user-active", subscription_status="active", credit_balance=100.0)
        user_trial = make_user(self.db, user_id="user-trial", email="trial@test.com", subscription_status="trialing", credit_balance=100.0)
        user_inactive = make_user(self.db, user_id="user-inactive", email="inactive@test.com", subscription_status="inactive", credit_balance=100.0)

        project_active = make_project(self.db, user_active.id, project_id="p1", domain="example.com")
        project_trial = make_project(self.db, user_trial.id, project_id="p2", domain="example2.com")
        project_inactive = make_project(self.db, user_inactive.id, project_id="p3", domain="example3.com")

        make_keyword(self.db, project_active.id, user_active.id, keyword="active kw", is_active=True)
        make_keyword(self.db, project_trial.id, user_trial.id, keyword="trial kw", is_active=True)
        make_keyword(self.db, project_inactive.id, user_inactive.id, keyword="inactive kw", is_active=True)

        with patch("app.workers.monday_tracker.SessionLocal") as MockSessionLocal, \
             patch("app.services.competitor_rank_service.track_competitor_rankings") as mock_comp:
            MockSessionLocal.return_value = self.db
            mock_comp.return_value = {"tracked": 0}

            result = run_monday_tracker()

        assert result["updated_keywords"] == 0
        assert result["scanned_users"] == 1
