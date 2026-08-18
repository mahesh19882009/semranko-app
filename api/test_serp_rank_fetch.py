"""Regression tests for Top-100 SERP rank fetch and day-one/manual refresh."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app.db.models import Base, User, Project, Keyword, RankResult
from app.services.dataforseo_client import DataForSEOClient, SerpRankResult
from app.api.routes.keywords import _apply_day_one_tracking
from app.services.keyword_update_service import refresh_keyword_data
from app.core.errors import ApiError


def build_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def build_user(db: Session):
    user = User(
        id="serp-test-user",
        name="Serp Test",
        email="serp@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        creditBalance=200.0,
        planCreditBalance=200.0,
        purchasedCreditBalance=0.0,
        automaticCreditBalance=0.0,
    )
    db.add(user)
    db.commit()
    return user


def build_project(db: Session, user: User, domain="example.com"):
    project = Project(
        id="serp-test-project",
        userId=user.id,
        name="Serp Project",
        domain=domain,
        location="India",
        locationCode=2840,
    )
    db.add(project)
    db.commit()
    return project


def make_serp_mock(items, cost=0.0155, status_code=20000):
    serp_response = {
        "tasks": [
            {
                "status_code": status_code,
                "cost": cost,
                "result": [
                    {
                        "items": items,
                    }
                ]
            }
        ]
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = serp_response
    mock_response.raise_for_status.return_value = None
    return mock_response


def test_fetch_serp_rank_ranked_position_5():
    db = build_db()
    user = build_user(db)
    project = build_project(db, user, domain="w3schools.com")

    mock_response = make_serp_mock([
        {"type": "organic", "rank_absolute": 1, "domain": "other.com", "url": "https://other.com"},
        {"type": "organic", "rank_absolute": 5, "domain": "www.w3schools.com", "url": "https://www.w3schools.com/python/"},
    ])

    with patch("app.services.dataforseo_client.requests.post", return_value=mock_response):
        with patch("app.services.dataforseo_client._get_cached_serp", return_value=None):
            result = DataForSEOClient.fetch_serp_rank("python tutorial", "w3schools.com", 2840, db=db, user_id=user.id)

    assert result["state"] == SerpRankResult.RANKED
    assert result["position"] == 5
    assert result["url"] == "https://www.w3schools.com/python/"
    assert result["has_aio"] is False
    assert result["cached"] is False
    assert result["dfs_cost"] == 0.0155

    db.close()


def test_fetch_serp_rank_valid_unranked():
    db = build_db()
    user = build_user(db)

    mock_response = make_serp_mock([
        {"type": "organic", "rank_absolute": 1, "domain": "other.com", "url": "https://other.com"},
        {"type": "organic", "rank_absolute": 20, "domain": "another.com", "url": "https://another.com"},
    ])

    with patch("app.services.dataforseo_client.requests.post", return_value=mock_response):
        with patch("app.services.dataforseo_client._get_cached_serp", return_value=None):
            result = DataForSEOClient.fetch_serp_rank("rare keyword", "example.com", 2840, db=db, user_id=user.id)

    assert result["state"] == SerpRankResult.VALID_UNRANKED
    assert result["position"] is None
    assert result["url"] is None
    assert result["dfs_cost"] == 0.0155

    db.close()


def test_fetch_serp_rank_provider_error():
    db = build_db()
    user = build_user(db)

    mock_response = make_serp_mock([], status_code=50000, cost=0.0)

    with patch("app.services.dataforseo_client.requests.post", return_value=mock_response):
        with patch("app.services.dataforseo_client._get_cached_serp", return_value=None):
            result = DataForSEOClient.fetch_serp_rank("keyword", "example.com", 2840, db=db, user_id=user.id)

    assert result["state"] == SerpRankResult.PROVIDER_ERROR
    assert result["position"] is None
    assert result["dfs_cost"] == 0.0

    db.close()


def test_fetch_serp_rank_cache_hit():
    db = build_db()
    user = build_user(db)

    cached_entry = {
        "organic_items": [
            {"type": "organic", "rank_absolute": 10, "domain": "example.com", "url": "https://example.com/page"}
        ],
        "items": [],
        "check_url": "https://example.com/page",
    }
    cache_key = "serp:v1:google:abc123:2840:en:desktop:unknown:100:false"
    with patch("app.services.dataforseo_client._get_cached_serp", return_value=cached_entry):
        with patch("app.services.dataforseo_client._build_serp_cache_key", return_value=cache_key):
            result = DataForSEOClient.fetch_serp_rank("cached keyword", "example.com", 2840, depth=100)

    assert result["state"] == SerpRankResult.RANKED
    assert result["position"] == 10
    assert result["url"] == "https://example.com/page"
    assert result["cached"] is True
    assert result["dfs_cost"] == 0.0

    db.close()


def test_fetch_serp_rank_invalid_response_no_tasks():
    db = build_db()
    user = build_user(db)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"tasks": []}
    mock_response.raise_for_status.return_value = None

    with patch("app.services.dataforseo_client.requests.post", return_value=mock_response):
        with patch("app.services.dataforseo_client._get_cached_serp", return_value=None):
            result = DataForSEOClient.fetch_serp_rank("keyword", "example.com", 2840, db=db, user_id=user.id)

    assert result["state"] == SerpRankResult.INVALID_RESPONSE
    assert result["position"] is None
    assert result["dfs_cost"] == 0.0

    db.close()


def test_day_one_tracking_creates_rank_result():
    db = build_db()
    user = build_user(db)
    project = build_project(db, user, domain="example.com")
    keyword = Keyword(
        projectId=project.id,
        userId=user.id,
        keyword="day one rank test",
        location="India",
        device="desktop",
        volume=100,
        kd=10,
        cpc=1.5,
        competition=0.5,
        backlinks=10,
        referring_domains=5,
        intent="informational",
        position=None,
        ai_badge="—",
    )
    db.add(keyword)
    db.commit()

    labs_rows = [{
        "keyword": "day one rank test",
        "volume": 100,
        "kd": 10,
        "cpc": 1.5,
        "competition": 0.5,
        "backlinks": 10,
        "referring_domains": 5,
        "intent": "informational",
        "position": None,
        "ai_badge": "—",
        "ai_description": None,
        "check_url": None,
    }]

    serp_result = {
        "state": SerpRankResult.RANKED,
        "position": 7,
        "url": "https://example.com/page",
        "has_aio": False,
        "ai_description": None,
        "check_url": "https://example.com/page",
        "cached": False,
        "dfs_cost": 0.0155,
    }

    with patch("app.api.routes.keywords.DataForSEOClient.fetch_dashboard_data", return_value=labs_rows):
        with patch("app.api.routes.keywords.DataForSEOClient.fetch_serp_rank", return_value=serp_result):
            with patch("app.services.dataforseo_client.check_dfs_cost_ceiling"):
                with patch("app.api.routes.keywords.reserve_credits", return_value="res"):
                    with patch("app.api.routes.keywords.consume_reserved"):
                        success = _apply_day_one_tracking(db, user.id, "day one rank test", 2840, "example.com", cost=20)

    assert success is True
    db.refresh(keyword)
    assert keyword.position == 7
    assert keyword.check_url == "https://example.com/page"
    assert keyword.volume == 100

    rank = db.scalar(select(RankResult).where(RankResult.keywordText == "day one rank test"))
    assert rank is not None
    assert rank.position == 7
    assert rank.url == "https://example.com/page"

    db.close()


def test_manual_refresh_updates_rank_result():
    db = build_db()
    user = build_user(db)
    project = build_project(db, user, domain="example.com")
    keyword = Keyword(
        projectId=project.id,
        userId=user.id,
        keyword="manual refresh test",
        location="India",
        device="desktop",
        volume=50,
        kd=20,
        cpc=2.0,
        competition=0.4,
        backlinks=5,
        referring_domains=2,
        intent="informational",
        position=10,
        ai_badge="—",
    )
    db.add(keyword)
    db.commit()

    labs_rows = [{
        "keyword": "manual refresh test",
        "volume": 60,
        "kd": 25,
        "cpc": 2.2,
        "competition": 0.45,
        "backlinks": 8,
        "referring_domains": 3,
        "intent": "informational",
        "position": 10,
        "ai_badge": "—",
        "ai_description": None,
        "check_url": None,
    }]

    serp_result = {
        "state": SerpRankResult.RANKED,
        "position": 3,
        "url": "https://example.com/new-page",
        "has_aio": True,
        "ai_description": "AI summary",
        "check_url": "https://example.com/new-page",
        "cached": False,
        "dfs_cost": 0.0155,
    }

    with patch("app.services.keyword_update_service.DataForSEOClient.fetch_dashboard_data", return_value=labs_rows):
        with patch("app.services.keyword_update_service.DataForSEOClient.fetch_serp_rank", return_value=serp_result):
            with patch("app.services.keyword_update_service.ensure_feature_available"):
                with patch("app.services.keyword_update_service.reserve_feature_usage", return_value=("ref", MagicMock())):
                    with patch("app.services.keyword_update_service.finalize_feature_usage", return_value=MagicMock()):
                        with patch("app.services.keyword_update_service.reserve_credits", return_value="res"):
                            with patch("app.services.keyword_update_service.consume_reserved"):
                                with patch("app.services.keyword_update_service.refund_reserved"):
                                    summary = refresh_keyword_data(db, user.id, project.id, keyword_ids=[keyword.id])

    assert summary["success"] is True
    assert summary["updated"] == 1
    db.refresh(keyword)
    assert keyword.position == 3
    assert keyword.check_url == "https://example.com/new-page"
    assert keyword.ai_badge == "AIO"
    assert keyword.ai_description == "AI summary"

    rank = db.scalar(select(RankResult).where(RankResult.keywordText == "manual refresh test"))
    assert rank is not None
    assert rank.position == 3

    db.close()
