"""Targeted regressions for keyword activation and final credit consistency."""

import sys
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

sys.path.insert(0, "/Users/maheshsharma/development/rankcare-api/api/fastapi_app")

from app.core.config import settings
from app.core.errors import ApiError
from app.db.models import Base, CreditLedger, Keyword, KeywordMetricsHistory, Project, RankResult, Subscription, User
from app.services.async_bulk_service import _paginate_eligible_keywords
from app.services.keyword_update_service import refresh_keyword_data
from app.services.monthly_metrics_service import _paginate_eligible_keywords_for_monthly
from app.services.plan_service import activate_keyword, deactivate_keyword, ensure_keyword_limit, set_keywords_active_state


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def make_user(db, user_id="u1", plan="starter", credits=1000.0):
    now = datetime.utcnow().replace(microsecond=0)
    user = User(
        id=user_id,
        name="Test",
        email=f"{user_id}@example.com",
        passwordHash="hash",
        selectedPlan=plan,
        subscriptionStatus="active",
        creditBalance=credits,
        refreshFrequency="monthly",
        planAnniversaryAt=now,
        lastCreditResetAt=now,
    )
    db.add(user)
    db.add(Subscription(userId=user_id, planId=0, status="active", isActive=True, startDate=now, endDate=now + timedelta(days=30)))
    db.commit()
    return user


def make_keyword(db, user, keyword_id="k1", active=True, deleted=False):
    project = db.get(Project, f"p-{user.id}")
    if project is None:
        project = Project(id=f"p-{user.id}", name="P", domain="example.com", userId=user.id, location="India", locationCode=2356)
        db.add(project)
    keyword = Keyword(
        id=keyword_id,
        projectId=project.id,
        userId=user.id,
        keyword=f"keyword-{keyword_id}",
        location="India",
        isActive=active,
        deletedAt=datetime.utcnow() if deleted else None,
        position=4,
        check_url="https://example.com/ranking",
        ai_badge="AIO",
        ai_description="preserved overview",
        lastWeeklyRefreshAt=datetime.utcnow(),
    )
    db.add(keyword)
    db.commit()
    return project, keyword


def test_single_deactivate_and_reactivate_preserve_history_without_cost_or_dfs():
    db = make_db()
    user = make_user(db)
    project, keyword = make_keyword(db, user)
    db.add(RankResult(projectId=project.id, keywordId=keyword.id, keywordText=keyword.keyword, position=4, url=keyword.check_url))
    db.add(KeywordMetricsHistory(keywordId=keyword.id, projectId=project.id, userId=user.id, volume=100))
    db.commit()
    balance = user.creditBalance

    with patch("app.services.dataforseo_client.requests.post") as dfs:
        deactivate_keyword(db, user.id, keyword.id)
        db.refresh(keyword)
        assert keyword.isActive is False
        activate_keyword(db, user.id, keyword.id)
        db.refresh(keyword)
        assert keyword.isActive is True
        assert keyword.lastWeeklyRefreshAt is None
        dfs.assert_not_called()

    db.refresh(user)
    assert user.creditBalance == balance
    assert keyword.position == 4 and keyword.check_url == "https://example.com/ranking"
    assert keyword.ai_badge == "AIO" and keyword.ai_description == "preserved overview"
    assert db.scalar(select(func.count()).select_from(RankResult).where(RankResult.keywordId == keyword.id)) == 1
    assert db.scalar(select(func.count()).select_from(KeywordMetricsHistory).where(KeywordMetricsHistory.keywordId == keyword.id)) == 1
    assert db.scalar(select(func.count()).select_from(CreditLedger).where(CreditLedger.userId == user.id)) == 0


def test_bulk_activate_deactivate_is_tenant_safe_and_partial():
    db = make_db()
    owner = make_user(db, "owner")
    other = make_user(db, "other")
    _, first = make_keyword(db, owner, "first")
    _, second = make_keyword(db, owner, "second")
    _, foreign = make_keyword(db, other, "foreign")
    _, deleted = make_keyword(db, owner, "deleted", active=False, deleted=True)

    result = set_keywords_active_state(db, owner.id, [first.id, second.id, foreign.id, deleted.id, "missing"], False)
    assert set(result["updated"]) == {first.id, second.id}
    assert set(result["invalid"]) == {foreign.id, deleted.id, "missing"}
    assert db.get(Keyword, foreign.id).isActive is True

    result = set_keywords_active_state(db, owner.id, [first.id, second.id, foreign.id], True)
    assert set(result["updated"]) == {first.id, second.id}
    assert result["invalid"] == [foreign.id]


def test_cross_user_single_activation_is_hidden():
    db = make_db()
    owner = make_user(db, "owner")
    other = make_user(db, "other")
    _, keyword = make_keyword(db, owner, "private", active=False)
    with pytest.raises(ApiError) as error:
        activate_keyword(db, other.id, keyword.id)
    assert error.value.status_code == 404


def test_deleted_and_inactive_are_distinct_states():
    db = make_db()
    user = make_user(db)
    _, inactive = make_keyword(db, user, "inactive", active=False)
    _, deleted = make_keyword(db, user, "deleted", active=False, deleted=True)
    activate_keyword(db, user.id, inactive.id)
    with pytest.raises(ApiError) as error:
        activate_keyword(db, user.id, deleted.id)
    assert error.value.status_code == 409
    assert db.get(Keyword, deleted.id).deletedAt is not None


def test_inactive_keywords_are_excluded_from_scheduled_refreshes():
    db = make_db()
    user = make_user(db)
    _, inactive = make_keyword(db, user, "inactive", active=False)
    inactive.lastWeeklyRefreshAt = None
    inactive.lastMonthlyMetricsRefreshAt = None
    db.commit()
    assert _paginate_eligible_keywords(db, job_type="weekly") == []
    assert _paginate_eligible_keywords_for_monthly(db) == []


def test_inactive_keyword_manual_refresh_is_blocked_before_dfs_or_credit():
    db = make_db()
    user = make_user(db, credits=100.0)
    project, keyword = make_keyword(db, user, "inactive", active=False)
    with patch("app.services.keyword_update_service.DataForSEOClient.fetch_dashboard_data") as dfs:
        result = refresh_keyword_data(db, user.id, project.id, [keyword.id])
    assert result["error"] == "KEYWORD_INACTIVE"
    assert result["message"] == "Activate this keyword before refreshing it."
    dfs.assert_not_called()
    db.refresh(user)
    assert user.creditBalance == 100.0


def test_inactive_keyword_still_consumes_plan_slot():
    db = make_db()
    user = make_user(db)
    make_keyword(db, user, "inactive", active=False)
    with patch("app.services.plan_service.get_user_plan_limits", return_value={"keywordLimit": 1}):
        with pytest.raises(ApiError):
            ensure_keyword_limit(db, user.id)


def test_manual_refresh_charges_twenty_credits_per_successful_keyword():
    db = make_db()
    user = make_user(db, credits=100.0)
    project, keyword = make_keyword(db, user)
    keyword.lastWeeklyRefreshAt = None
    db.commit()
    row = {"keyword": keyword.keyword, "volume": 100, "kd": 20, "cpc": 1.0, "position": 3}
    with patch("app.services.keyword_update_service.DataForSEOClient.fetch_dashboard_data", return_value=[row]):
        result = refresh_keyword_data(db, user.id, project.id, [keyword.id])
    assert result["updated"] == 1
    db.refresh(user)
    assert user.creditBalance == 80.0


def test_final_credit_costs_and_paid_feature_limits_are_canonical():
    costs = settings.plan_config.credit_costs
    assert costs["add_keyword"] == costs["bulk_add_keyword"] == 20
    assert costs["manual_refresh_per_keyword"] == 20
    assert costs["weekly_refresh_per_keyword"] == 10
    assert costs["monthly_refresh_per_keyword"] == 10
    assert costs["keyword_research"] == 20
    assert costs["competitor_spy"] == 30

    expected = {
        "free_trial": (0, 0, 0),
        "starter": (10, 10, 3),
        "pro": (50, 30, 10),
        "agency": (150, 75, 25),
    }
    for plan, limits in expected.items():
        definition = settings.plan_config.plans[plan]
        assert (definition.manual_refresh_limit, definition.keyword_research_limit, definition.competitor_spy_limit) == limits
