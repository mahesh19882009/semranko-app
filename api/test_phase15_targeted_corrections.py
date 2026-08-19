"""Targeted regressions for Phase 15 launch limits and repository corrections."""

import asyncio
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, "/Users/maheshsharma/development/semranko-api/api/fastapi_app")

from app.api.routes.keyword_research import research_keyword_endpoint, competitor_spy_endpoint
from app.core.errors import ApiError
from app.core.config import settings
from app.db.models import Base, CreditLedger, FeatureUsage, PaymentOrder, Project, RefreshJob, Subscription, User, Keyword
from app.services.async_bulk_service import run_weekly_refresh_worker
from app.services.dataforseo_client import (
    _estimate_dataforseo_cost,
    _get_cached_kw_metrics,
    _get_cached_labs,
    _get_cached_serp,
    _set_cached_kw_metrics,
    _set_cached_labs,
    _set_cached_serp,
)
from app.services.feature_usage_service import (
    ensure_feature_available,
    finalize_feature_usage,
    get_feature_usage,
    reserve_feature_usage,
)
from app.services.keyword_research_service import research_keyword
from app.services.keyword_update_service import refresh_keyword_data
from app.services.payment_service import activate_subscription
from app.services.plan_service import ensure_project_limit, get_user_plan_limits


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def setex(self, key, ttl, value):
        self.values[key] = value
        self.ttls[key] = ttl
        return True

    def get(self, key):
        return self.values.get(key)


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def make_user(db, user_id="u1", plan="starter", credits=1000.0, status="active", cycle_start=None):
    now = cycle_start or datetime.utcnow().replace(microsecond=0)
    user = User(
        id=user_id,
        name="Test",
        email=f"{user_id}@example.com",
        passwordHash="hash",
        selectedPlan=plan,
        subscriptionStatus=status,
        creditBalance=credits,
        trialStartsAt=now,
        trialEndsAt=now + timedelta(days=10),
        planAnniversaryAt=now,
        lastCreditResetAt=now,
    )
    db.add(user)
    if status == "active":
        plan_id = {"starter": 0, "pro": 1, "agency": 2}.get(plan, 0)
        db.add(Subscription(userId=user_id, planId=plan_id, status="active", isActive=True, startDate=now, endDate=now + timedelta(days=30)))
    db.commit()
    return user


def make_project_with_keywords(db, user, count=1):
    project = Project(id=f"p-{user.id}", name="P", domain="example.com", userId=user.id, location="India", locationCode=2356)
    db.add(project)
    for index in range(count):
        db.add(Keyword(id=f"k-{user.id}-{index}", projectId=project.id, userId=user.id, keyword=f"keyword {index}", location="India", isActive=True))
    db.commit()
    return project


def test_real_cache_wrappers_write_and_read_with_ttls():
    fake = FakeRedis()
    with patch("app.services.cache_service.redis_client", fake):
        assert _set_cached_serp("serp-key", {"items": [1]}, ttl=101) is True
        assert _set_cached_labs("labs-key", {"ideas": [1]}, ttl=202) is True
        assert _set_cached_kw_metrics("metrics-key", {"volume": 10}, ttl=303) is True
        assert _get_cached_serp("serp-key") == {"items": [1]}
        assert _get_cached_labs("labs-key") == {"ideas": [1]}
        assert _get_cached_kw_metrics("metrics-key") == {"volume": 10}
        assert sorted(fake.ttls.values()) == [101, 202, 303]


@pytest.mark.parametrize("plan,domain_limit", [("free_trial", 1), ("starter", 1), ("pro", 5), ("agency", 20)])
def test_configured_domain_limits_are_enforced(plan, domain_limit):
    db = make_db()
    user = make_user(db, plan=plan)
    assert get_user_plan_limits(user, db)["domain_limit"] == domain_limit
    for index in range(domain_limit):
        db.add(Project(id=f"p{index}", name="P", domain=f"{index}.example.com", userId=user.id))
    db.commit()
    with pytest.raises(ApiError) as error:
        ensure_project_limit(db, user.id)
    assert error.value.status_code == 403


@pytest.mark.parametrize("feature", ["manual_refresh", "keyword_research", "competitor_spy"])
def test_free_plan_blocks_paid_features_before_dfs(feature):
    db = make_db()
    user = make_user(db, plan="free_trial", status="trialing")
    with pytest.raises(ApiError) as error:
        ensure_feature_available(db, user.id, feature)
    assert error.value.data["error"] == "upgrade_required"
    assert error.value.message == "This feature is available on paid plans. Upgrade to continue."


@pytest.mark.parametrize(
    "plan,manual,research,spy",
    [("starter", 10, 10, 3), ("pro", 50, 30, 10), ("agency", 150, 75, 25)],
)
def test_paid_plan_feature_limits(plan, manual, research, spy):
    db = make_db()
    user = make_user(db, plan=plan)
    assert get_feature_usage(db, user.id, "manual_refresh")["limit"] == manual
    assert get_feature_usage(db, user.id, "keyword_research")["limit"] == research
    assert get_feature_usage(db, user.id, "competitor_spy")["limit"] == spy


def test_research_route_charges_once_and_cache_hit_uses_no_credit_or_allowance():
    db = make_db()
    user = make_user(db, credits=100.0)
    with patch("app.services.keyword_research_service.DataForSEOClient.get_keyword_ideas_api", return_value=[{"keyword": "seed", "volume": 10}]):
        asyncio.run(research_keyword_endpoint(keyword="seed", location_code=2356, location="India", x_test_mode=None, db=db, current_user={"id": user.id, "userId": user.id}))
    db.refresh(user)
    assert user.creditBalance == 80.0
    assert get_feature_usage(db, user.id, "keyword_research")["used"] == 1
    charge_count = len(db.scalars(select(CreditLedger).where(CreditLedger.userId == user.id, CreditLedger.actionType == "charge")).all())
    assert charge_count == 1

    asyncio.run(research_keyword_endpoint(keyword="seed", location_code=2356, location="India", x_test_mode=None, db=db, current_user={"id": user.id, "userId": user.id}))
    db.refresh(user)
    assert user.creditBalance == 80.0
    assert get_feature_usage(db, user.id, "keyword_research")["used"] == 1


def test_competitor_spy_route_charges_once():
    db = make_db()
    user = make_user(db, credits=100.0)
    rows = [{"domain": "competitor.com", "organic_keywords": 5}]
    with patch("app.services.competitor_spy_service.DataForSEOClient.get_competitor_keywords", return_value=rows):
        asyncio.run(competitor_spy_endpoint(domain="competitor.com", location_code=2356, location="India", limit=100, x_test_mode=None, db=db, current_user={"id": user.id, "userId": user.id}))
    db.refresh(user)
    assert user.creditBalance == 70.0
    assert get_feature_usage(db, user.id, "competitor_spy")["used"] == 1
    assert len(db.scalars(select(CreditLedger).where(CreditLedger.userId == user.id, CreditLedger.actionType == "charge")).all()) == 1


def test_manual_refresh_bulk_cannot_exceed_remaining_allowance():
    db = make_db()
    user = make_user(db, credits=1000.0)
    project = make_project_with_keywords(db, user, count=2)
    ref, _ = reserve_feature_usage(db, user.id, "manual_refresh", 9)
    finalize_feature_usage(db, ref, 9)
    with patch("app.services.keyword_update_service.DataForSEOClient.fetch_dashboard_data") as dfs:
        with pytest.raises(ApiError) as error:
            refresh_keyword_data(db, user.id, project.id)
    assert error.value.data["error"] == "feature_limit_exceeded"
    dfs.assert_not_called()


def test_usage_resets_at_new_subscription_cycle_boundary():
    db = make_db()
    start = datetime(2026, 8, 1)
    user = make_user(db, cycle_start=start)
    ref, _ = reserve_feature_usage(db, user.id, "keyword_research", 1)
    finalize_feature_usage(db, ref, 1)
    sub = db.scalar(select(Subscription).where(Subscription.userId == user.id))
    sub.startDate = sub.endDate
    sub.endDate = sub.startDate + timedelta(days=30)
    db.add(sub)
    db.commit()
    usage = get_feature_usage(db, user.id, "keyword_research")
    assert usage["used"] == 0
    assert usage["remaining"] == 10
    assert usage["resetAt"] == sub.endDate.isoformat()


def test_concurrent_allowance_reservations_cannot_exceed_limit(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'feature-usage.db'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = make_user(db)
    barrier = Barrier(2)

    def reserve(reference):
        with Session(engine) as worker_db:
            barrier.wait()
            try:
                reserve_feature_usage(worker_db, user.id, "competitor_spy", 2, reference=reference)
                return "reserved"
            except ApiError as error:
                return error.data["error"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reserve, ["concurrent-a", "concurrent-b"]))

    assert sorted(results) == ["feature_limit_exceeded", "reserved"]
    db.expire_all()
    usage = get_feature_usage(db, user.id, "competitor_spy")
    assert usage["reserved"] == 2 and usage["remaining"] == 1


def test_weekly_worker_drains_all_queued_refresh_jobs_once():
    db = make_db()
    jobs = [RefreshJob(jobType="weekly_serp", status="queued", batchIndex=i, totalBatches=2, keywordCount=1, keywordsJson=json.dumps([])) for i in range(2)]
    db.add_all(jobs)
    db.commit()

    def submitted(_db, job):
        job.status = "submitted"
        _db.add(job)
        _db.commit()
        return True

    with patch("app.services.async_bulk_service.submit_refresh_job_to_dataforseo", side_effect=submitted) as submit:
        result = run_weekly_refresh_worker(db)
    assert result["processed"] == 2
    assert submit.call_count == 2
    assert run_weekly_refresh_worker(db)["processed"] == 0


def test_worker_entry_points_have_session_factory_imports():
    from app.workers import refresh_worker
    from app.services import webhook_credit_retry_service
    assert refresh_worker.SessionLocal is not None
    assert webhook_credit_retry_service.SessionLocal is not None


def test_payment_mismatch_has_no_partial_mutation():
    db = make_db()
    user = make_user(db, plan="pro", credits=321.0)
    user.pendingPlanChange = "starter"
    order = PaymentOrder(userId=user.id, razorpayOrderId="order-mismatch", planId=2, amount=100, status="created", purchaseType="SUBSCRIPTION_UPGRADE")
    db.add_all([user, order])
    db.commit()
    sub = db.scalar(select(Subscription).where(Subscription.userId == user.id))
    original = (user.selectedPlan, user.creditBalance, sub.planId, order.status)
    with pytest.raises(Exception, match="Payment plan mismatch"):
        activate_subscription(db, user.id, 2, "pay-1", order.razorpayOrderId)
    db.expire_all()
    user = db.get(User, user.id)
    sub = db.get(Subscription, sub.id)
    order = db.get(PaymentOrder, order.id)
    assert (user.selectedPlan, user.creditBalance, sub.planId, order.status) == original


def test_official_phase15_cost_formulas():
    assert _estimate_dataforseo_cost("/serp/google/organic/live/advanced", 1, depth=100) == 0.02
    assert _estimate_dataforseo_cost("/serp/google/organic/task_post", 1, depth=100) == 0.006
    assert _estimate_dataforseo_cost("/serp/google/organic/task_post", 1, depth=100, priority=1) == 0.012
    assert _estimate_dataforseo_cost("/dataforseo_labs/google/keyword_overview/live", 10) == 0.0132
    assert _estimate_dataforseo_cost("/dataforseo_labs/google/competitors_domain/live", 100) == 0.024


def test_single_and_bulk_keyword_credit_costs_match():
    assert settings.plan_config.credit_costs["add_keyword"] == 20
    assert settings.plan_config.credit_costs["bulk_add_keyword"] == 20
