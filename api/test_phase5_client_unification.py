import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import sys
sys.path.insert(0, "/Users/maheshsharma/development/rankcare-api/api/fastapi_app")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Base, User, Project, Keyword
from app.services.dataforseo_client import DataForSEOClient, _build_serp_cache_key
from app.services.dataforseo_dashboard import DataForSeoDashboardHelper
from app.services.cache_service import set_cached, get_cached


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


def make_keyword(db: Session, project_id, keyword="test kw", location="India"):
    kw = Keyword(projectId=project_id, keyword=keyword, location=location, isActive=True)
    db.add(kw)
    db.commit()
    return kw


class TestPhase5ClientUnification:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_fetch_dashboard_data_returns_list(self):
        with patch.object(DataForSEOClient, "_fetch_keyword_data_batch") as mock_labs, \
             patch.object(DataForSEOClient, "get_serp_data_batch") as mock_serp:
            mock_labs.return_value = {"test kw": {"volume": 1000, "kd": 50, "cpc": 1.5, "competition": 0.8, "intent": "informational", "backlinks": 100, "referring_domains": 20}}
            mock_serp.return_value = {
                "test kw": {
                    "items": [{"type": "organic", "url": "https://example.com", "rank_group": 5, "domain": "example.com"}],
                    "item_groups": [],
                }
            }

            rows = DataForSEOClient.fetch_dashboard_data(["test kw"], "example.com", location_code=2840)
            assert isinstance(rows, list)
            assert len(rows) == 1

    def test_fetch_dashboard_data_return_shape_matches_old_helper(self):
        with patch.object(DataForSEOClient, "_fetch_keyword_data_batch") as mock_labs, \
             patch.object(DataForSEOClient, "get_serp_data_batch") as mock_serp:
            mock_labs.return_value = {"test kw": {"volume": 1000, "difficulty": 50, "cpc": 1.5, "competition": 0.8, "intent": "informational", "backlinks": 100, "referring_domains": 20}}
            mock_serp.return_value = {
                "test kw": {
                    "items": [{"type": "organic", "url": "https://example.com", "rank_group": 5, "domain": "example.com"}],
                    "item_groups": [],
                }
            }

            rows = DataForSEOClient.fetch_dashboard_data(["test kw"], "example.com", location_code=2840)
            row = rows[0]

            assert row["keyword"] == "test kw"
            assert row["volume"] == 1000
            assert row["kd"] == 50
            assert row["cpc"] == 1.5
            assert row["competition"] == 0.8
            assert row["intent"] == "informational"
            assert row["backlinks"] == 100
            assert row["referring_domains"] == 20
            assert row["position"] == 5
            assert row["check_url"] == "https://example.com"

    def test_fetch_dashboard_data_handles_multiple_keywords(self):
        with patch.object(DataForSEOClient, "_fetch_keyword_data_batch") as mock_labs, \
             patch.object(DataForSEOClient, "get_serp_data_batch") as mock_serp:
            mock_labs.return_value = {
                "kw1": {"volume": 100, "kd": 20},
                "kw2": {"volume": 200, "kd": 40},
            }
            mock_serp.return_value = {
                "kw1": {"items": [{"type": "organic", "url": "https://example.com/kw1", "rank_group": 1, "domain": "example.com"}], "item_groups": []},
                "kw2": {"items": [], "item_groups": []},
            }

            rows = DataForSEOClient.fetch_dashboard_data(["kw1", "kw2"], "example.com", location_code=2840)
            assert len(rows) == 2
            assert rows[0]["keyword"] == "kw1"
            assert rows[1]["keyword"] == "kw2"
            assert rows[0]["position"] == 1
            assert rows[1]["position"] is None

    def test_fetch_dashboard_data_string_keyword(self):
        with patch.object(DataForSEOClient, "_fetch_keyword_data_batch") as mock_labs, \
             patch.object(DataForSEOClient, "get_serp_data_batch") as mock_serp:
            mock_labs.return_value = {"kw1": {"volume": 100, "kd": 20}}
            mock_serp.return_value = {"kw1": {"items": [], "item_groups": []}}

            rows = DataForSEOClient.fetch_dashboard_data("kw1", "example.com", location_code=2840)
            assert isinstance(rows, list)
            assert len(rows) == 1

    def test_fetch_dashboard_data_empty_keywords(self):
        rows = DataForSEOClient.fetch_dashboard_data([], "example.com", location_code=2840)
        assert rows == []

    def test_fetch_dashboard_data_serp_cache_hit(self):
        cache_key = _build_serp_cache_key("test kw", 2840, "en", "desktop", "unknown", 100, False)
        cached_serp = {
            "items": [{"type": "organic", "url": "https://example.com/cached", "rank_group": 3, "domain": "example.com"}],
            "item_groups": [],
        }
        set_cached("serp", cache_key, cached_serp, ttl_seconds=86400)

        with patch.object(DataForSEOClient, "_fetch_keyword_data_batch") as mock_labs, \
             patch("app.services.dataforseo_client.requests.post") as mock_post:
            mock_labs.return_value = {"test kw": {"volume": 100, "kd": 20, "difficulty": 20, "cpc": 1.0, "competition": 0.5, "intent": "informational", "backlinks": 50, "referring_domains": 10}}
            mock_post.return_value.raise_for_status.return_value = None
            mock_post.return_value.json.return_value = {"tasks": []}

            rows = DataForSEOClient.fetch_dashboard_data(
                ["test kw"],
                "example.com",
                location_code=2840,
            )

            assert rows[0]["position"] == 3
            assert rows[0]["check_url"] == "https://example.com/cached"
            assert not mock_post.called or mock_post.call_count == 0

    def test_fetch_dashboard_data_serp_cache_miss(self):
        with patch.object(DataForSEOClient, "_fetch_keyword_data_batch") as mock_labs, \
             patch("app.services.dataforseo_client.requests.post") as mock_post:
            mock_labs.return_value = {"cache-miss-kw": {"volume": 100, "difficulty": 20, "cpc": 1.0, "competition": 0.5, "intent": "informational", "backlinks": 50, "referring_domains": 10}}
            mock_post.return_value.raise_for_status.return_value = None
            mock_post.return_value.json.return_value = {
                "tasks": [{
                    "data": {"keyword": "cache-miss-kw"},
                    "result": [{
                        "items": [{"type": "organic", "url": "https://example.com/new", "rank_group": 7, "domain": "example.com"}],
                        "item_groups": [],
                    }]
                }]
            }

            rows = DataForSEOClient.fetch_dashboard_data(
                ["cache-miss-kw"],
                "example.com",
                location_code=2840,
            )

            assert rows[0]["position"] == 7
            assert rows[0]["check_url"] == "https://example.com/new"
            assert mock_post.called

    def test_fetch_dashboard_data_logs_cost(self):
        user = make_user(self.db, user_id="user-cost", credit_balance=100.0)
        project = make_project(self.db, user.id, project_id="proj-cost", domain="example.com")

        with patch.object(DataForSEOClient, "_fetch_keyword_data_batch") as mock_labs, \
             patch.object(DataForSEOClient, "get_serp_data_batch") as mock_serp:
            mock_labs.return_value = {"test kw": {"volume": 100, "kd": 20}}
            mock_serp.return_value = {"test kw": {"items": [], "item_groups": []}}

            rows = DataForSEOClient.fetch_dashboard_data(
                ["test kw"],
                "example.com",
                location_code=2840,
                db=self.db,
                user_id=user.id,
            )

            assert len(rows) == 1

    def test_deprecated_wrapper_forwarding(self):
        with patch.object(DataForSEOClient, "fetch_dashboard_data") as mock_fetch:
            mock_fetch.return_value = [{"keyword": "kw", "volume": 100}]

            helper = DataForSeoDashboardHelper("user", "pass")
            rows = helper.fetch_cheapest_dashboard_data(["kw"], "example.com", location_code=2840)

            assert rows == [{"keyword": "kw", "volume": 100}]
            mock_fetch.assert_called_once_with(["kw"], "example.com", location_code=2840, language_code="en", pingback_url=None)

    def test_deprecated_wrapper_emits_warning(self):
        with patch.object(DataForSEOClient, "fetch_dashboard_data") as mock_fetch:
            mock_fetch.return_value = []

            with pytest.warns(DeprecationWarning, match="DataForSeoDashboardHelper is deprecated"):
                helper = DataForSeoDashboardHelper("user", "pass")
                helper.fetch_cheapest_dashboard_data(["kw"], "example.com")

    def test_fetch_dashboard_data_uses_settings_auth(self):
        with patch.object(DataForSEOClient, "_fetch_keyword_data_batch") as mock_labs, \
             patch.object(DataForSEOClient, "get_serp_data_batch") as mock_serp, \
             patch("app.services.dataforseo_client.requests.post") as mock_post, \
             patch("app.services.dataforseo_client.settings") as mock_settings:
            mock_labs.return_value = {"test kw": {"volume": 100, "kd": 20}}
            mock_serp.return_value = {"test kw": {"items": [], "item_groups": []}}
            mock_settings.effective_serp_login = "test_user"
            mock_settings.effective_serp_key = "test_key"

            rows = DataForSEOClient.fetch_dashboard_data(
                ["test kw"],
                "example.com",
                location_code=2840,
            )

            assert rows[0]["volume"] == 100

    def test_fetch_dashboard_data_aio_badge_detection(self):
        with patch.object(DataForSEOClient, "_fetch_keyword_data_batch") as mock_labs, \
             patch.object(DataForSEOClient, "get_serp_data_batch") as mock_serp:
            mock_labs.return_value = {"test kw": {"volume": 100, "kd": 20}}
            mock_serp.return_value = {
                "test kw": {
                    "items": [
                        {"type": "ai_overview", "asynchronous_ai_overview": True, "description": "AI overview text", "references": [{"url": "https://example.com/aio"}]},
                    ],
                    "item_groups": [],
                }
            }

            rows = DataForSEOClient.fetch_dashboard_data(["test kw"], "example.com", location_code=2840)
            assert rows[0]["ai_badge"] == "AIO"
            assert rows[0]["ai_description"] == "AI overview text"

    def test_fetch_dashboard_data_aio_badge_via_item_groups(self):
        with patch.object(DataForSEOClient, "_fetch_keyword_data_batch") as mock_labs, \
             patch.object(DataForSEOClient, "get_serp_data_batch") as mock_serp:
            mock_labs.return_value = {"test kw": {"volume": 100, "kd": 20}}
            mock_serp.return_value = {
                "test kw": {
                    "items": [],
                    "item_groups": [
                        {"type": "ai_overview", "items": [{"references": [{"url": "https://example.com/aio"}]}]},
                    ],
                }
            }

            rows = DataForSEOClient.fetch_dashboard_data(["test kw"], "example.com", location_code=2840)
            assert rows[0]["ai_badge"] == "AIO"
