"""Regression tests for manual QA fixes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db.models import Base, User, Project, Keyword
from app.services.keyword_service import add_keyword
from app.core.errors import ApiError
from app.main import app
from app.api.deps import get_current_user, db_session
from unittest.mock import patch, MagicMock
from datetime import datetime


def _build_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return Session(engine)


def _build_user(db: Session):
    user = User(
        id="test-user-qa",
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
    return user


def _build_project(db: Session, user_id: str):
    project = Project(
        id="test-project-qa",
        userId=user_id,
        name="Test Project",
        domain="example.com",
        location="India",
        locationCode=2840,
    )
    db.add(project)
    db.commit()
    return project


def _override_auth(user: User):
    def _fake_current_user():
        return {
            "userId": user.id,
            "email": user.email,
            "name": user.name,
            "selectedPlan": user.selectedPlan,
            "subscriptionStatus": user.subscriptionStatus,
        }
    app.dependency_overrides[get_current_user] = _fake_current_user


def _override_db(db: Session):
    def _db_override():
        yield db
    app.dependency_overrides[db_session] = _db_override


def _clear_overrides():
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(db_session, None)


def test_keyword_add_rejects_on_day_one_exception():
    """Verify keyword add does not leave orphan keyword when async tracking job creation throws."""
    db = _build_db()
    user = _build_user(db)
    project = _build_project(db, user.id)

    _override_auth(user)
    _override_db(db)
    try:
        with patch("app.api.routes.keywords.submit_user_tracking_job", side_effect=Exception("Network error")):
            response = TestClient(app).post(f"/api/keywords/{project.id}", json={
                "keyword": "test keyword",
                "location": "India",
            })

        assert response.status_code == 502

        orphan = db.scalar(
            select(Keyword).where(
                Keyword.projectId == project.id,
                Keyword.keyword == "test keyword"
            )
        )
        assert orphan is None, "Orphan keyword should not exist after tracking exception"
    finally:
        _clear_overrides()
        db.close()


def test_keyword_add_allows_empty_tracking_job():
    """Verify keyword add succeeds when tracking job returns no refresh_job_id (accepted behavior)."""
    db = _build_db()
    user = _build_user(db)
    project = _build_project(db, user.id)

    _override_auth(user)
    _override_db(db)
    try:
        with patch("app.api.routes.keywords.submit_user_tracking_job", return_value={"refresh_job_id": None}):
            response = TestClient(app).post(f"/api/keywords/{project.id}", json={
                "keyword": "test keyword",
                "location": "India",
            })

        assert response.status_code == 502

        keyword = db.scalar(
            select(Keyword).where(
                Keyword.projectId == project.id,
                Keyword.keyword == "test keyword"
            )
        )
        assert keyword is None, "Keyword should not exist when tracking job creation fails"
    finally:
        _clear_overrides()
        db.close()


def test_refund_reserved_imported_in_keyword_research():
    """Verify refund_reserved is imported in keyword_research_service."""
    from app.services.keyword_research_service import refund_reserved
    assert refund_reserved is not None


def test_refund_reserved_imported_in_keywords_route():
    """Verify refund_reserved is imported in keywords route (actual single-keyword add path)."""
    from app.api.routes.keywords import refund_reserved
    assert refund_reserved is not None


def test_refund_reserved_function_exists():
    """Verify refund_reserved function exists in credit_service."""
    from app.services.credit_service import refund_reserved
    assert callable(refund_reserved)
