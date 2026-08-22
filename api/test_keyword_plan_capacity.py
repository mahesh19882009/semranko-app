"""Focused capacity regressions for the active keyword bulk-add route."""

from pathlib import Path
import sys
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.api.routes.keywords import bulk_create_keywords, create_keyword
from app.core.errors import ApiError
from app.db.models import Base, Keyword, Project, User


def _build_db(existing_count: int = 0) -> tuple[Session, User, Project]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(
        id="capacity-user",
        name="Capacity User",
        email="capacity@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        creditBalance=100000.0,
        planCreditBalance=100000.0,
        purchasedCreditBalance=0.0,
    )
    project = Project(
        id="capacity-project",
        userId=user.id,
        name="Capacity Project",
        domain="example.com",
        location="India",
        locationCode=2356,
    )
    db.add_all([user, project])
    db.add_all([
        Keyword(
            id=f"existing-{index}",
            projectId=project.id,
            userId=user.id,
            keyword=f"existing keyword {index}",
            location="India",
            locationCode=2356,
            device="desktop",
            isActive=True,
        )
        for index in range(existing_count)
    ])
    db.commit()
    return db, user, project


def _active_bulk_route():
    route = bulk_create_keywords
    while hasattr(route, "__wrapped__"):
        route = route.__wrapped__
    return route


def _active_single_route():
    route = create_keyword
    while hasattr(route, "__wrapped__"):
        route = route.__wrapped__
    return route


def _tracking_result(keywords):
    return {
        "refresh_job_id": "capacity-refresh",
        "accepted": True,
        "accepted_keywords": list(keywords),
        "completed_keywords": [],
        "failed_keywords": [],
    }


def _keyword_count(db: Session, user_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(Keyword).where(Keyword.userId == user_id)
    ) or 0


def test_bulk_capacity_allows_one_genuinely_new_target_at_99_of_100():
    db, user, project = _build_db(existing_count=99)
    try:
        with patch(
            "app.services.plan_service.get_user_plan_limits",
            return_value={"keywordLimit": 100},
        ), patch(
            "app.api.routes.keywords.submit_user_tracking_job",
            return_value=_tracking_result(["new target"]),
        ):
            result = _active_bulk_route()(
                request=None,
                project_id=project.id,
                payload={"keywords": ["new target"], "location_code": 2356},
                user={"userId": user.id},
                db=db,
            )

        assert result["data"]["added"] == 1
        assert _keyword_count(db, user.id) == 100
    finally:
        db.close()


def test_bulk_capacity_rejects_two_genuinely_new_targets_at_99_of_100():
    db, user, project = _build_db(existing_count=99)
    try:
        with patch(
            "app.services.plan_service.get_user_plan_limits",
            return_value={"keywordLimit": 100},
        ), patch(
            "app.api.routes.keywords.submit_user_tracking_job"
        ) as tracking:
            with pytest.raises(ApiError) as error:
                _active_bulk_route()(
                    request=None,
                    project_id=project.id,
                    payload={"keywords": ["new target one", "new target two"], "location_code": 2356},
                    user={"userId": user.id},
                    db=db,
                )

        db.rollback()
        assert error.value.status_code == 403
        assert "allows 100 keywords" in error.value.message
        assert _keyword_count(db, user.id) == 99
        tracking.assert_not_called()
    finally:
        db.close()


def test_bulk_capacity_counts_only_new_exact_targets_and_skips_duplicates():
    db, user, project = _build_db(existing_count=99)
    try:
        with patch(
            "app.services.plan_service.get_user_plan_limits",
            return_value={"keywordLimit": 100},
        ), patch(
            "app.api.routes.keywords.submit_user_tracking_job",
            return_value=_tracking_result(["new target"]),
        ):
            result = _active_bulk_route()(
                request=None,
                project_id=project.id,
                payload={
                    "keywords": ["EXISTING KEYWORD 0", "new target", "New Target"],
                    "location_code": 2356,
                    "device": "desktop",
                },
                user={"userId": user.id},
                db=db,
            )

        assert result["data"]["added"] == 1
        assert result["data"]["skipped"] == 2
        assert _keyword_count(db, user.id) == 100
    finally:
        db.close()


def test_same_text_at_different_location_is_a_new_capacity_target():
    db, user, project = _build_db(existing_count=98)
    db.add(Keyword(
        id="existing-shared-target",
        projectId=project.id,
        userId=user.id,
        keyword="shared target",
        location="India",
        locationCode=2356,
        device="desktop",
        isActive=True,
    ))
    db.commit()
    try:
        with patch(
            "app.services.plan_service.get_user_plan_limits",
            return_value={"keywordLimit": 100},
        ), patch(
            "app.api.routes.keywords.submit_user_tracking_job",
            return_value=_tracking_result(["shared target"]),
        ):
            result = _active_bulk_route()(
                request=None,
                project_id=project.id,
                payload={
                    "keywords": ["shared target"],
                    "location_details": {
                        "country": "Australia",
                        "state": "New South Wales",
                        "city": "Sydney",
                        "location_code": 1000256,
                    },
                    "device": "desktop",
                },
                user={"userId": user.id},
                db=db,
            )

        rows = db.scalars(
            select(Keyword).where(Keyword.keyword == "shared target")
        ).all()
        assert result["data"]["added"] == 1
        assert {row.locationCode for row in rows} == {2356, 1000256}
        assert _keyword_count(db, user.id) == 100
    finally:
        db.close()


def test_same_text_on_different_device_is_a_new_capacity_target():
    db, user, project = _build_db(existing_count=98)
    db.add(Keyword(
        id="existing-device-target",
        projectId=project.id,
        userId=user.id,
        keyword="device target",
        location="India",
        locationCode=2356,
        device="desktop",
        isActive=True,
    ))
    db.commit()
    try:
        with patch(
            "app.services.plan_service.get_user_plan_limits",
            return_value={"keywordLimit": 100},
        ), patch(
            "app.api.routes.keywords.submit_user_tracking_job",
            return_value=_tracking_result(["device target"]),
        ):
            result = _active_bulk_route()(
                request=None,
                project_id=project.id,
                payload={
                    "keywords": ["device target"],
                    "location_code": 2356,
                    "device": "mobile",
                },
                user={"userId": user.id},
                db=db,
            )

        rows = db.scalars(
            select(Keyword).where(Keyword.keyword == "device target")
        ).all()
        assert result["data"]["added"] == 1
        assert {row.device for row in rows} == {"desktop", "mobile"}
        assert _keyword_count(db, user.id) == 100
    finally:
        db.close()


def test_existing_exact_target_does_not_consume_capacity_at_limit():
    db, user, project = _build_db(existing_count=100)
    try:
        with patch(
            "app.services.plan_service.get_user_plan_limits",
            return_value={"keywordLimit": 100},
        ), patch(
            "app.api.routes.keywords.submit_user_tracking_job"
        ) as tracking:
            result = _active_bulk_route()(
                request=None,
                project_id=project.id,
                payload={"keywords": ["existing keyword 0"], "location_code": 2356},
                user={"userId": user.id},
                db=db,
            )

        assert result["data"]["added"] == 0
        assert result["data"]["skipped"] == 1
        assert _keyword_count(db, user.id) == 100
        tracking.assert_not_called()
    finally:
        db.close()


def test_single_add_uses_the_same_request_aware_capacity_check():
    db, user, project = _build_db(existing_count=99)
    try:
        with patch(
            "app.services.plan_service.get_user_plan_limits",
            return_value={"keywordLimit": 100},
        ), patch(
            "app.api.routes.keywords.submit_user_tracking_job",
            return_value=_tracking_result(["single target"]),
        ) as tracking:
            _active_single_route()(
                request=None,
                project_id=project.id,
                payload={"keyword": "single target", "location_code": 2356},
                user={"userId": user.id},
                db=db,
            )

        # The real tracking service commits the Keyword with its reservation/job.
        db.commit()
        assert _keyword_count(db, user.id) == 100
        tracking.assert_called_once()

        with patch(
            "app.services.plan_service.get_user_plan_limits",
            return_value={"keywordLimit": 100},
        ), patch(
            "app.api.routes.keywords.submit_user_tracking_job"
        ) as second_tracking:
            with pytest.raises(ApiError) as error:
                _active_single_route()(
                    request=None,
                    project_id=project.id,
                    payload={"keyword": "one target too many", "location_code": 2356},
                    user={"userId": user.id},
                    db=db,
                )

        db.rollback()
        assert error.value.status_code == 403
        assert _keyword_count(db, user.id) == 100
        second_tracking.assert_not_called()
    finally:
        db.close()
