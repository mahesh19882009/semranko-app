import sys
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, "/Users/maheshsharma/development/rankcare-api/api/fastapi_app")

from app.db.models import Base, Subscription, User
from app.services.dataforseo_client import _build_labs_cache_key
from app.services.feature_usage_service import get_feature_usage
from app.services.keyword_research_service import research_keyword
from app.services.competitor_spy_service import spy_competitor_keywords


class FakeRedis:
    def __init__(self):
        self.values = {}

    def setex(self, key, _ttl, value):
        self.values[key] = value
        return True

    def get(self, key):
        return self.values.get(key)


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def make_user(db: Session, user_id: str, plan: str = "starter", credits: float = 100.0):
    now = datetime.utcnow().replace(microsecond=0)
    user = User(
        id=user_id,
        name="User",
        email=f"{user_id}@example.com",
        passwordHash="hash",
        selectedPlan=plan,
        subscriptionStatus="active",
        creditBalance=credits,
        trialStartsAt=now,
        trialEndsAt=now + timedelta(days=7),
        planAnniversaryAt=now,
        lastCreditResetAt=now,
    )
    db.add(user)
    db.add(
        Subscription(
            userId=user_id,
            planId=0,
            status="active",
            isActive=True,
            startDate=now,
            endDate=now + timedelta(days=30),
        )
    )
    db.commit()
    return user


def test_keyword_research_cross_account_never_auto_uses_other_users_state_but_shares_provider_cache_on_submit():
    db = make_db()
    user_a = make_user(db, "user-a")
    user_b = make_user(db, "user-b")
    fake_redis = FakeRedis()
    ideas = [{"keyword": "rankcare", "volume": 100, "difficulty": 10}]

    with patch("app.services.cache_service.redis_client", fake_redis), patch(
        "app.services.keyword_research_service.DataForSEOClient.get_keyword_ideas_api",
        return_value=ideas,
    ) as dfs_call:
        result_a = research_keyword(db, user_a.id, "RankCare", 2356)
        assert result_a["cached"] is False
        assert result_a["credits_charged"] == 1
        db.refresh(user_a)
        assert user_a.creditBalance == 80.0
        assert get_feature_usage(db, user_a.id, "keyword_research")["used"] == 1

        # User B has not submitted anything yet, so usage/state remains empty.
        assert get_feature_usage(db, user_b.id, "keyword_research")["used"] == 0

        result_b = research_keyword(db, user_b.id, "rankcare", 2356)
        assert result_b["cached"] is True
        assert result_b["credits_charged"] == 0
        db.refresh(user_b)
        assert user_b.creditBalance == 100.0
        assert get_feature_usage(db, user_b.id, "keyword_research")["used"] == 0
        assert dfs_call.call_count == 1


def test_keyword_research_different_query_still_fetches_and_charges():
    db = make_db()
    user_a = make_user(db, "user-a")
    user_b = make_user(db, "user-b")
    fake_redis = FakeRedis()

    with patch("app.services.cache_service.redis_client", fake_redis), patch(
        "app.services.keyword_research_service.DataForSEOClient.get_keyword_ideas_api",
        side_effect=[
            [{"keyword": "rankcare", "volume": 100}],
            [{"keyword": "seo audit", "volume": 80}],
        ],
    ) as dfs_call:
        research_keyword(db, user_a.id, "rankcare", 2356)
        result_b = research_keyword(db, user_b.id, "seo audit", 2356)
        assert result_b["cached"] is False
        assert result_b["credits_charged"] == 1
        assert dfs_call.call_count == 2


def test_competitor_spy_cross_account_shares_provider_cache_after_submit_without_spending_user_b_allowance():
    db = make_db()
    user_a = make_user(db, "user-a")
    user_b = make_user(db, "user-b")
    fake_redis = FakeRedis()
    rows = [{"domain": "example.org", "intersections": 12}]

    with patch("app.services.cache_service.redis_client", fake_redis), patch(
        "app.services.competitor_spy_service.DataForSEOClient.get_competitor_keywords",
        return_value=rows,
    ) as dfs_call:
        result_a = spy_competitor_keywords(db, user_a.id, "Example.com", 2356, 10)
        assert result_a["cached"] is False
        assert result_a["credits_charged"] == 1
        db.refresh(user_a)
        assert user_a.creditBalance == 70.0
        assert get_feature_usage(db, user_a.id, "competitor_spy")["used"] == 1

        assert get_feature_usage(db, user_b.id, "competitor_spy")["used"] == 0
        result_b = spy_competitor_keywords(db, user_b.id, "example.com", 2356, 1)
        assert result_b["cached"] is True
        assert result_b["credits_charged"] == 0
        assert len(result_b["keywords"]) == 1
        db.refresh(user_b)
        assert user_b.creditBalance == 100.0
        assert get_feature_usage(db, user_b.id, "competitor_spy")["used"] == 0
        dfs_call.assert_called_once_with("example.com", 2356, 100, db=db, user_id=user_a.id)

        cache_payload = "\n".join(str(value) for value in fake_redis.values.values())
        assert "user-a@example.com" not in cache_payload
        assert "user-b@example.com" not in cache_payload


def test_competitor_spy_different_domain_fetches_new_provider_result():
    db = make_db()
    user_a = make_user(db, "user-a")
    user_b = make_user(db, "user-b")
    fake_redis = FakeRedis()

    with patch("app.services.cache_service.redis_client", fake_redis), patch(
        "app.services.competitor_spy_service.DataForSEOClient.get_competitor_keywords",
        side_effect=[
            [{"domain": "a.example"}],
            [{"domain": "b.example"}],
        ],
    ) as dfs_call:
        spy_competitor_keywords(db, user_a.id, "a.com", 2356, 10)
        result_b = spy_competitor_keywords(db, user_b.id, "b.com", 2356, 10)
        assert result_b["cached"] is False
        assert result_b["credits_charged"] == 1
        assert dfs_call.call_count == 2


def test_research_and_spy_labs_cache_keys_include_material_fields_without_user_identity():
    research_key_a = _build_labs_cache_key("keyword_ideas", "rankcare", 2356, "en")
    research_key_same = _build_labs_cache_key("keyword_ideas", " rankcare ", 2356, "en")
    research_key_keyword_diff = _build_labs_cache_key("keyword_ideas", "seo audit", 2356, "en")
    research_key_location_diff = _build_labs_cache_key("keyword_ideas", "rankcare", 2840, "en")
    research_key_language_diff = _build_labs_cache_key("keyword_ideas", "rankcare", 2356, "hi")

    assert research_key_a == research_key_same
    assert research_key_a != research_key_keyword_diff
    assert research_key_a != research_key_location_diff
    assert research_key_a != research_key_language_diff
    assert "user" not in research_key_a

    spy_key_a = _build_labs_cache_key("competitors_domain", "example.com", 2356, "en")
    spy_key_same = _build_labs_cache_key("competitors_domain", "EXAMPLE.COM", 2356, "en")
    spy_key_domain_diff = _build_labs_cache_key("competitors_domain", "example.org", 2356, "en")
    spy_key_location_diff = _build_labs_cache_key("competitors_domain", "example.com", 2840, "en")
    spy_key_language_diff = _build_labs_cache_key("competitors_domain", "example.com", 2356, "hi")

    assert spy_key_a == spy_key_same
    assert spy_key_a != spy_key_domain_diff
    assert spy_key_a != spy_key_location_diff
    assert spy_key_a != spy_key_language_diff
    assert "user" not in spy_key_a
