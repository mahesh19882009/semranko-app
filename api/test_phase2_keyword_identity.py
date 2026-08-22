"""Phase 2 persistent keyword-target identity regressions."""

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.db.models import Base, Keyword, Project, User
from app.api.routes.keywords import create_keyword
from app.core.errors import ApiError
from app.services.keyword_identity import (
    catalog_location_labels,
    effective_location_code,
    normalize_device,
    normalize_keyword,
    resolve_legacy_keyword_target,
)


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _project(db: Session, project_id: str = "phase2-project", user_id: str = "phase2-user") -> Project:
    user = User(id=user_id, name="Phase 2", email=f"{user_id}@example.com", passwordHash="hash")
    project = Project(
        id=project_id,
        userId=user_id,
        name="Phase 2",
        domain="example.com",
        location="India",
        locationCode=2356,
        device="desktop",
    )
    db.add_all([user, project])
    db.commit()
    return project


def _keyword(project: Project, text: str, code: int, device: str = "desktop") -> Keyword:
    return Keyword(
        projectId=project.id,
        userId=project.userId,
        keyword=normalize_keyword(text),
        location="India" if code == 2356 else "Faridabad, Haryana, India",
        locationCode=code,
        device=normalize_device(device),
        isActive=True,
    )


def test_keyword_model_persists_location_code_and_target_unique_index():
    db = _db()
    try:
        project = _project(db)
        row = _keyword(project, " SEO company ", 2356)
        db.add(row)
        db.commit()
        assert row.locationCode == 2356
        indexes = {item["name"]: item for item in inspect(db.bind).get_indexes("Keyword")}
        assert indexes["Keyword_projectId_keyword_locationCode_device_key"]["unique"] == 1
        assert "Keyword_projectId_keyword_key" not in indexes
    finally:
        db.close()


def test_same_keyword_different_location_and_device_are_distinct_targets():
    db = _db()
    try:
        project = _project(db)
        db.add_all([
            _keyword(project, "seo company", 2356, "desktop"),
            _keyword(project, "seo company", 9061655, "desktop"),
            _keyword(project, "seo company", 9061655, "mobile"),
        ])
        db.commit()
        assert db.scalar(select(Keyword).where(Keyword.locationCode == 9061655, Keyword.device == "mobile"))
    finally:
        db.close()


def test_same_target_is_allowed_in_other_projects_and_accounts():
    db = _db()
    try:
        first = _project(db, "project-one", "user-one")
        second = _project(db, "project-two", "user-two")
        db.add_all([
            _keyword(first, "seo company", 2356),
            _keyword(second, "seo company", 2356),
        ])
        db.commit()
        assert db.query(Keyword).count() == 2
    finally:
        db.close()


def test_exact_target_duplicate_is_rejected_without_merging_rows():
    db = _db()
    try:
        project = _project(db)
        db.add(_keyword(project, "seo company", 2356, "desktop"))
        db.commit()
        db.add(_keyword(project, " SEO COMPANY ", 2356, "DESKTOP"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert db.scalar(select(Keyword).where(Keyword.projectId == project.id)).keyword == "seo company"
    finally:
        db.close()


def test_identity_normalization_is_only_trim_lower_and_device_case_normalization():
    assert normalize_keyword("  SEO  Company  ") == "seo  company"
    assert normalize_device(" DESKTOP ") == "desktop"
    assert normalize_device("MOBILE") == "mobile"
    with pytest.raises(ValueError):
        normalize_device("tablet")


def test_effective_location_code_preserves_explicit_and_resolves_catalog_labels():
    assert effective_location_code(location_code=9061655, location="India") == 9061655
    assert effective_location_code(location="Faridabad, Haryana, India") == 9061655
    assert effective_location_code(location="India", project_location_code=2840, project_location="India") == 2840


def test_migration_backfill_resolves_country_state_and_city_without_guessing():
    labels = catalog_location_labels()
    project = {"location": "India", "locationCode": 2356}
    assert resolve_legacy_keyword_target({"id": "a", "keyword": " SEO ", "location": "India", "device": None}, project, labels) == ("seo", 2356, "desktop")
    assert resolve_legacy_keyword_target({"id": "b", "keyword": "seo", "location": "Haryana, India", "device": "Desktop"}, project, labels) == ("seo", 1007787, "desktop")
    assert resolve_legacy_keyword_target({"id": "c", "keyword": "seo", "location": "Faridabad, Haryana, India", "device": "mobile"}, project, labels) == ("seo", 9061655, "mobile")
    unresolved = resolve_legacy_keyword_target({"id": "d", "keyword": "seo", "location": "Unknown Place", "device": "desktop"}, project, labels)
    assert unresolved[0] is None


def test_migration_backfill_does_not_delete_or_merge_rows_on_collision():
    labels = catalog_location_labels()
    project = {"location": "India", "locationCode": 2356}
    first = resolve_legacy_keyword_target({"id": "one", "keyword": " SEO ", "location": "India", "device": "desktop"}, project, labels)
    second = resolve_legacy_keyword_target({"id": "two", "keyword": "seo", "location": "India", "device": "DESKTOP"}, project, labels)
    assert first == second == ("seo", 2356, "desktop")


def test_single_add_duplicate_checks_the_full_target_identity_before_provider():
    db = _db()
    project = _project(db)
    route = create_keyword
    while hasattr(route, "__wrapped__"):
        route = route.__wrapped__
    user = {"userId": project.userId}
    india = {"country": "India", "location_code": 2356}
    faridabad = {
        "country": "India",
        "state": "Haryana",
        "city": "Faridabad",
        "location_code": 9061655,
    }
    try:
        accepted = {
            "refresh_job_id": "phase2-refresh",
            "accepted": True,
            "completed_keywords": [],
        }
        with patch("app.api.routes.keywords.submit_user_tracking_job", return_value=accepted):
            route(MagicMock(), project.id, {"keyword": "seo company", "location_details": india, "device": "desktop"}, user, db)
        with patch("app.api.routes.keywords.submit_user_tracking_job") as duplicate_provider:
            with pytest.raises(ApiError) as error:
                route(MagicMock(), project.id, {"keyword": " SEO COMPANY ", "location_details": india, "device": "DESKTOP"}, user, db)
        assert error.value.status_code == 409
        duplicate_provider.assert_not_called()
        with patch("app.api.routes.keywords.submit_user_tracking_job", return_value=accepted):
            route(MagicMock(), project.id, {"keyword": "seo company", "location_details": faridabad, "device": "desktop"}, user, db)
            route(MagicMock(), project.id, {"keyword": "seo company", "location_details": faridabad, "device": "mobile"}, user, db)
        assert db.query(Keyword).filter(Keyword.projectId == project.id).count() == 3
    finally:
        db.close()
