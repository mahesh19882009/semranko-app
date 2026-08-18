"""Regression tests for keyword add workflow recovery."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db.models import Base, User, Project, Keyword
from app.services.keyword_service import add_keyword
from app.core.errors import ApiError
from unittest.mock import patch
from datetime import datetime, timedelta


def test_single_keyword_add_with_empty_dataforseo():
    """Verify single keyword add succeeds when DataForSEO returns empty data (accepted behavior)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)

    user = User(
        id="test-user-workflow",
        name="Test User",
        email="test@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        creditBalance=100.0,
        planCreditBalance=100.0,
        purchasedCreditBalance=0.0,
        automaticCreditBalance=0.0,
    )
    db.add(user)
    db.commit()

    project = Project(
        id="test-project-workflow",
        userId=user.id,
        name="Test Project",
        domain="example.com",
        location="India",
        locationCode=2840,
    )
    db.add(project)
    db.commit()

    with patch("app.services.keyword_service._apply_day_one_tracking", return_value=True):
        result = add_keyword(db, user.id, project.id, {"keyword": "test keyword"})
        
        assert result is not None
        assert result["keyword"] == "test keyword"

    keyword = db.scalar(
        select(Keyword).where(
            Keyword.projectId == project.id,
            Keyword.keyword == "test keyword"
        )
    )
    assert keyword is not None

    db.close()


def test_keyword_add_with_existing_active():
    """Verify adding existing active keyword is rejected."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)

    user = User(
        id="test-user-existing",
        name="Test User",
        email="test@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        creditBalance=100.0,
        planCreditBalance=100.0,
        purchasedCreditBalance=0.0,
        automaticCreditBalance=0.0,
    )
    db.add(user)
    db.commit()

    project = Project(
        id="test-project-existing",
        userId=user.id,
        name="Test Project",
        domain="example.com",
        location="India",
        locationCode=2840,
    )
    db.add(project)
    db.commit()

    existing = Keyword(
        projectId=project.id,
        userId=user.id,
        keyword="existing",
        location="India",
        device="desktop",
        volume=0,
        kd=0,
        cpc=0.0,
        competition=0.0,
        backlinks=0.0,
        referring_domains=0.0,
        intent="—",
        position=0,
        ai_badge="—",
        isActive=True,
    )
    db.add(existing)
    db.commit()

    with pytest.raises(ApiError) as exc_info:
        add_keyword(db, user.id, project.id, {"keyword": "existing"})
    
    assert "already exists" in str(exc_info.value).lower()

    db.close()


def test_keyword_add_with_deleted_cooldown():
    """Verify adding recently deleted keyword respects cooldown."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)

    user = User(
        id="test-user-cooldown",
        name="Test User",
        email="test@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        creditBalance=100.0,
        planCreditBalance=100.0,
        purchasedCreditBalance=0.0,
        automaticCreditBalance=0.0,
    )
    db.add(user)
    db.commit()

    project = Project(
        id="test-project-cooldown",
        userId=user.id,
        name="Test Project",
        domain="example.com",
        location="India",
        locationCode=2840,
    )
    db.add(project)
    db.commit()

    deleted = Keyword(
        projectId=project.id,
        userId=user.id,
        keyword="deleted",
        location="India",
        device="desktop",
        volume=0,
        kd=0,
        cpc=0.0,
        competition=0.0,
        backlinks=0.0,
        referring_domains=0.0,
        intent="—",
        position=0,
        ai_badge="—",
        isActive=False,
        deletedAt=datetime.utcnow(),
    )
    db.add(deleted)
    db.commit()

    with pytest.raises(ApiError) as exc_info:
        add_keyword(db, user.id, project.id, {"keyword": "deleted"})
    
    assert "cooldown" in str(exc_info.value).lower() or "recently deleted" in str(exc_info.value).lower()

    db.close()


def test_keyword_add_after_cooldown_expires():
    """Verify adding deleted keyword succeeds after cooldown expires."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)

    user = User(
        id="test-user-expired",
        name="Test User",
        email="test@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        creditBalance=100.0,
        planCreditBalance=100.0,
        purchasedCreditBalance=0.0,
        automaticCreditBalance=0.0,
    )
    db.add(user)
    db.commit()

    project = Project(
        id="test-project-expired",
        userId=user.id,
        name="Test Project",
        domain="example.com",
        location="India",
        locationCode=2840,
    )
    db.add(project)
    db.commit()

    deleted = Keyword(
        projectId=project.id,
        userId=user.id,
        keyword="expired",
        location="India",
        device="desktop",
        volume=0,
        kd=0,
        cpc=0.0,
        competition=0.0,
        backlinks=0.0,
        referring_domains=0.0,
        intent="—",
        position=0,
        ai_badge="—",
        isActive=False,
        deletedAt=datetime.utcnow() - timedelta(days=31),
    )
    db.add(deleted)
    db.commit()

    with patch("app.services.keyword_service._apply_day_one_tracking", return_value=True):
        result = add_keyword(db, user.id, project.id, {"keyword": "expired"})

        assert result is not None
        assert result["keyword"] == "expired"

    db.close()


def test_fresh_keyword_add_with_day_one_tracking():
    """Verify fresh keyword add succeeds with day-one tracking."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)

    user = User(
        id="test-user-fresh",
        name="Test User",
        email="test@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        creditBalance=100.0,
        planCreditBalance=100.0,
        purchasedCreditBalance=0.0,
        automaticCreditBalance=0.0,
    )
    db.add(user)
    db.commit()

    project = Project(
        id="test-project-fresh",
        userId=user.id,
        name="Test Project",
        domain="example.com",
        location="India",
        locationCode=2840,
    )
    db.add(project)
    db.commit()

    with patch("app.services.keyword_service._apply_day_one_tracking", return_value=True):
        result = add_keyword(db, user.id, project.id, {"keyword": "fresh keyword"})

        assert result is not None
        assert result["keyword"] == "fresh keyword"

    keyword = db.scalar(
        select(Keyword).where(
            Keyword.projectId == project.id,
            Keyword.keyword == "fresh keyword"
        )
    )
    assert keyword is not None
    assert keyword.isActive is True

    db.close()


def test_keyword_add_refunds_reserved_credits_on_day_one_failure():
    """Verify reserved credits are refunded when day-one tracking fails."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)

    user = User(
        id="test-user-refund",
        name="Test User",
        email="test@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        creditBalance=100.0,
        planCreditBalance=100.0,
        purchasedCreditBalance=0.0,
        automaticCreditBalance=0.0,
    )
    db.add(user)
    db.commit()

    project = Project(
        id="test-project-refund",
        userId=user.id,
        name="Test Project",
        domain="example.com",
        location="India",
        locationCode=2840,
    )
    db.add(project)
    db.commit()

    initial_balance = user.creditBalance

    with patch("app.services.keyword_service._apply_day_one_tracking", side_effect=Exception("tracking failed")):
        with pytest.raises(Exception, match="tracking failed"):
            add_keyword(db, user.id, project.id, {"keyword": "refund keyword"})

    db.refresh(user)
    assert user.creditBalance == initial_balance

    db.close()

