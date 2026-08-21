from datetime import datetime, timedelta
import re
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import Base, CreditLedger, Subscription, User
from app.services.dataforseo_client import (
    DataForSEOClient,
    DataForSEOKeywordIdeasError,
)
from app.services.feature_usage_service import get_feature_usage
from app.services.keyword_research_service import research_keyword


def make_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def make_user(db: Session, user_id: str = "research-user", credits: float = 100.0) -> User:
    now = datetime.utcnow().replace(microsecond=0)
    user = User(
        id=user_id,
        name="Research User",
        email=f"{user_id}@example.com",
        passwordHash="hash",
        selectedPlan="starter",
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
            userId=user.id,
            planId=0,
            status="active",
            isActive=True,
            startDate=now,
            endDate=now + timedelta(days=30),
        )
    )
    db.commit()
    return user


def test_keyword_ideas_network_failure_is_explicit_when_requested():
    with patch(
        "app.services.dataforseo_client.requests.post",
        side_effect=TimeoutError("provider timeout"),
    ):
        with pytest.raises(DataForSEOKeywordIdeasError):
            DataForSEOClient.get_keyword_ideas_api(
                "semranko", 2356, raise_on_error=True
            )


def test_keyword_ideas_default_failure_contract_remains_unchanged():
    with patch(
        "app.services.dataforseo_client.requests.post",
        side_effect=TimeoutError("provider timeout"),
    ):
        assert DataForSEOClient.get_keyword_ideas_api("semranko", 2356) == []


def test_keyword_ideas_http_failure_is_explicit_when_requested():
    response = MagicMock(status_code=502, text="bad gateway")
    response.raise_for_status.side_effect = RuntimeError("provider 502")
    with patch("app.services.dataforseo_client.requests.post", return_value=response):
        with pytest.raises(DataForSEOKeywordIdeasError):
            DataForSEOClient.get_keyword_ideas_api(
                "semranko", 2356, raise_on_error=True
            )


def test_keyword_ideas_successful_empty_result_is_not_provider_failure():
    response = MagicMock(status_code=200, text="{}")
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "tasks": [{"status_code": 20000, "result": [{"items": []}]}]
    }
    with patch("app.services.dataforseo_client.requests.post", return_value=response):
        assert DataForSEOClient.get_keyword_ideas_api(
            "semranko", 2356, raise_on_error=True
        ) == []


def test_keyword_ideas_task_failure_is_explicit_when_requested():
    response = MagicMock(status_code=200, text="task failure")
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "tasks": [{"status_code": 40100, "status_message": "invalid request"}]
    }
    with patch("app.services.dataforseo_client.requests.post", return_value=response):
        with pytest.raises(DataForSEOKeywordIdeasError):
            DataForSEOClient.get_keyword_ideas_api(
                "semranko", 2356, raise_on_error=True
            )


def test_research_provider_failure_refunds_credits_and_releases_usage():
    db = make_db()
    user = make_user(db)

    with patch(
        "app.services.keyword_research_service.DataForSEOClient.get_keyword_ideas_api",
        side_effect=DataForSEOKeywordIdeasError("provider unavailable"),
    ):
        with pytest.raises(ApiError) as error:
            research_keyword(db, user.id, "semranko", 2356)

    assert error.value.status_code == 502
    db.refresh(user)
    assert user.creditBalance == 100.0
    usage = get_feature_usage(db, user.id, "keyword_research")
    assert usage["reserved"] == 0
    assert usage["used"] == 0
    reservation = db.scalar(
        select(CreditLedger).where(
            CreditLedger.userId == user.id,
            CreditLedger.description.like("%Keyword research: semranko%"),
        )
    )
    assert reservation.status == "refunded"
    assert reservation.creditsRefunded == 20.0


def test_research_success_charges_once_and_cache_hit_is_free():
    db = make_db()
    user = make_user(db)
    ideas = [{"keyword": "semranko", "volume": 100}]

    with patch(
        "app.services.keyword_research_service.DataForSEOClient.get_keyword_ideas_api",
        return_value=ideas,
    ) as provider:
        result = research_keyword(db, user.id, "semranko", 2356)
        cached = research_keyword(db, user.id, "semranko", 2356)

    assert result["cached"] is False
    assert result["credits_charged"] == 1
    assert cached["cached"] is True
    assert cached["credits_charged"] == 0
    provider.assert_called_once()
    db.refresh(user)
    assert user.creditBalance == 80.0
    assert get_feature_usage(db, user.id, "keyword_research")["used"] == 1


def test_research_successful_empty_result_is_billable_and_then_cached():
    db = make_db()
    user = make_user(db)

    with patch(
        "app.services.keyword_research_service.DataForSEOClient.get_keyword_ideas_api",
        return_value=[],
    ) as provider:
        result = research_keyword(db, user.id, "no ideas", 2356)
        cached = research_keyword(db, user.id, "no ideas", 2356)

    assert result["cached"] is False
    assert result["suggestions"] == []
    assert cached["cached"] is True
    assert cached["suggestions"] == []
    provider.assert_called_once()
    db.refresh(user)
    assert user.creditBalance == 80.0


def test_refund_reserved_is_idempotent_for_research_reservation():
    db = make_db()
    user = make_user(db)

    with patch(
        "app.services.keyword_research_service.DataForSEOClient.get_keyword_ideas_api",
        side_effect=DataForSEOKeywordIdeasError("provider unavailable"),
    ):
        with pytest.raises(ApiError):
            research_keyword(db, user.id, "semranko", 2356)

    db.refresh(user)
    balance_after_failure = user.creditBalance
    reservation = db.scalar(
        select(CreditLedger).where(
            CreditLedger.userId == user.id,
            CreditLedger.actionType == "reservation",
        )
    )
    reference = re.search(r"\[ref:(.+)\]$", reservation.description).group(1)
    from app.services.credit_service import refund_reserved

    refund_reserved(db, user.id, reference, 20.0)
    db.refresh(user)
    assert user.creditBalance == balance_after_failure
