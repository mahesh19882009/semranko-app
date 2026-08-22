"""Focused tests for tracking-table locations and read-only exports."""

from pathlib import Path
import json
import sys
from zipfile import ZipFile
from io import BytesIO
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.api.routes.keywords import _resolve_tracking_location, export_project_keywords, create_keyword, bulk_create_keywords
from app.core.errors import ApiError
from app.db.models import Base, Keyword, Project, User, ProcessingJob, RankResult, RefreshJob
from app.services.location_catalog import (
    KEYWORD_LOCATION_CATALOG,
    location_label_for_code,
    resolve_keyword_location,
)
from app.services.async_tracking_service import _apply_cached_results, submit_user_tracking_job
from app.services.serp_result_ingestion import _make_processing_job_worker_ready
from app.utils.export import export_csv, export_xlsx


def test_country_only_location_resolves_one_verified_code():
    resolved = resolve_keyword_location("India")
    assert resolved["location_code"] == 2356
    assert resolved["label"] == "India"


def test_state_and_city_location_resolution_uses_deepest_code():
    assert resolve_keyword_location("India", state="Maharashtra")["location_code"] == 20359
    resolved = resolve_keyword_location("India", state="Maharashtra", city="Mumbai")
    assert resolved["location_code"] == 9062115
    assert resolved["label"] == "Mumbai, Maharashtra, India"
    assert resolve_keyword_location("Australia", state="New South Wales", city="Sydney")["location_code"] == 1000256


def test_backend_loader_reads_the_canonical_frontend_json_catalog():
    catalog_path = Path(__file__).parents[1] / "semrankoapp" / "src" / "data" / "locations.json"
    with catalog_path.open(encoding="utf-8") as catalog_file:
        raw_catalog = json.load(catalog_file)
    assert [entry["name"] for entry in raw_catalog] == [entry["name"] for entry in KEYWORD_LOCATION_CATALOG]
    assert resolve_keyword_location("India", state="Haryana", city="Faridabad")["location_code"] == 9061655


def test_canonical_code_labels_cover_country_state_and_city_hierarchies():
    assert location_label_for_code(2356) == "India"
    assert location_label_for_code(1007787) == "Haryana, India"
    assert location_label_for_code(9061655) == "Faridabad, Haryana, India"
    assert location_label_for_code(9062115) == "Mumbai, Maharashtra, India"
    assert location_label_for_code(1000256) == "Sydney, New South Wales, Australia"
    assert location_label_for_code(1013962) == "Los Angeles, California, United States"


def test_tracking_submission_persists_canonical_location_on_refresh_and_child_jobs():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(
        id="location-user",
        name="Location User",
        email="location@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        creditBalance=100.0,
        planCreditBalance=100.0,
        purchasedCreditBalance=0.0,
        automaticCreditBalance=0.0,
    )
    project = Project(
        id="location-project",
        userId=user.id,
        name="Location Project",
        domain="example.com",
        location="Faridabad, Haryana, India",
        locationCode=9061655,
    )
    keyword = Keyword(
        id="location-keyword",
        projectId=project.id,
        userId=user.id,
        keyword="city keyword",
        location="Faridabad, Haryana, India",
        device="desktop",
        isActive=True,
    )
    db.add_all([user, project, keyword])
    db.commit()
    try:
        with patch("app.services.async_tracking_service._get_cached_serp", return_value=None), \
             patch("app.services.async_tracking_service.DataForSEOClient.submit_serp_task_post", return_value={"task_ids": ["mock-city-task"], "submitted": ["city keyword"], "failed_chunks": 0}), \
             patch("app.services.async_tracking_service.publish_keyword_update"):
            result = submit_user_tracking_job(
                db=db,
                user_id=user.id,
                project_id=project.id,
                keywords=[{"keyword": "city keyword", "location": keyword.location}],
                domain=project.domain,
                action="manual_refresh",
                location_code=9061655,
                device="desktop",
                depth=100,
                cost_per_keyword=20,
            )
        refresh = db.get(RefreshJob, result["refresh_job_id"])
        child = db.scalar(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh.id))
        assert child.location == "Faridabad, Haryana, India"
        assert json.loads(refresh.resultSummary)["location"] == child.location
        assert json.loads(child.payload)["location_code"] == 9061655
        assert json.loads(child.payload)["location"] == child.location
    finally:
        db.close()
        engine.dispose()


def test_bulk_route_passes_canonical_location_and_numeric_code_to_tracking():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(
        id="bulk-location-user",
        name="Bulk Location User",
        email="bulk-location@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        creditBalance=100.0,
        planCreditBalance=100.0,
        purchasedCreditBalance=0.0,
        automaticCreditBalance=0.0,
    )
    project = Project(id="bulk-location-project", userId=user.id, name="Bulk", domain="example.com")
    db.add_all([user, project])
    db.commit()
    route = bulk_create_keywords
    while hasattr(route, "__wrapped__"):
        route = route.__wrapped__
    try:
        with patch(
            "app.api.routes.keywords.submit_user_tracking_job",
            return_value={
                "refresh_job_id": "bulk-city-refresh",
                "accepted": True,
                "accepted_keywords": ["one", "two"],
                "completed_keywords": [],
                "failed_keywords": [],
            },
        ) as submit:
            route(
                request=None,
                project_id=project.id,
                payload={
                    "keywords": ["one", "two"],
                    "location_details": {
                        "country": "India",
                        "state": "Haryana",
                        "city": "Faridabad",
                        "location_code": 9061655,
                    },
                },
                user={"userId": user.id},
                db=db,
            )
        call = submit.call_args.kwargs
        assert call["location_code"] == 9061655
        assert [item["keyword"] for item in call["keywords"]] == ["one", "two"]
        assert all(
            item["location"] == "Faridabad, Haryana, India"
            for item in call["keywords"]
        )
    finally:
        db.close()
        engine.dispose()


def test_invalid_hierarchy_is_rejected_before_tracking_boundary():
    endpoint = create_keyword.__wrapped__.__wrapped__
    with patch("app.api.routes.keywords.submit_user_tracking_job") as provider:
        with pytest.raises(ApiError) as error:
            endpoint(
                None,
                "unknown-project",
                {
                    "keyword": "blocked city",
                    "location_details": {
                        "country": "India",
                        "state": "Haryana",
                        "city": "Not A City",
                        "location_code": 9061655,
                    },
                },
                {"userId": "location-user"},
                None,
            )
    assert error.value.status_code == 400
    provider.assert_not_called()


def test_callback_normalizes_legacy_child_location_before_worker_matching():
    child = ProcessingJob(
        refreshJobId="refresh-city",
        keywordText="city keyword",
        location="India",
        status="pending",
        deduplicationKey="pending-city",
        payload=json.dumps({"location_code": 9061655, "project_id": "project-city"}),
    )
    _make_processing_job_worker_ready(
        child,
        task_id="mock-city-task",
        task_data={"result": [{"items": []}]},
        current_keyword="city keyword",
        location_code=9061655,
        location_name="India",
    )
    assert child.location == "Faridabad, Haryana, India"
    assert json.loads(child.payload)["location"] == child.location


def test_cached_application_keeps_canonical_keyword_and_rank_locations():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(id="cached-location-user", name="Cached", email="cached-location@example.com", passwordHash="hash")
    project = Project(id="cached-location-project", userId=user.id, name="Cached", domain="example.com")
    keyword = Keyword(
        id="cached-location-keyword",
        projectId=project.id,
        userId=user.id,
        keyword="cached city",
        location="Faridabad, Haryana, India",
        device="desktop",
        isActive=True,
    )
    db.add_all([user, project, keyword])
    db.commit()
    try:
        completed = _apply_cached_results(
            db,
            project.id,
            user.id,
            project.domain,
            {"cached city": {"organic_items": [{"type": "organic", "rank_group": 2, "url": "https://example.com/cached", "domain": "example.com"}], "items": []}},
            "cached-city-refresh",
        )
        assert completed == ["cached city"]
        child = db.scalar(select(ProcessingJob).where(ProcessingJob.refreshJobId == "cached-city-refresh"))
        assert child.location == "Faridabad, Haryana, India"
        assert db.scalar(select(RankResult)).location == child.location
    finally:
        db.close()
        engine.dispose()


def test_unverified_child_location_is_rejected_instead_of_guessing():
    with pytest.raises(ValueError):
        resolve_keyword_location("India", state="Unknown")


def test_tracking_boundary_accepts_legacy_country_payloads():
    # Existing callers sometimes provide an explicit code independently of the
    # display country; preserve that established provider boundary.
    assert _resolve_tracking_location({"location": "India", "location_code": 2840}) == ("India", 2840)


def test_generic_csv_export_escapes_values_and_has_headers():
    response = export_csv(("Keyword", "Location", "Device"), [("a,b", 'Haryana, India', "desktop")], "keywords.csv")
    body = response.body.decode("utf-8-sig")
    assert body.splitlines() == ["Keyword,Location,Device", '"a,b","Haryana, India",desktop']
    assert response.headers["content-disposition"].endswith('filename="keywords.csv"')


def test_generic_xlsx_export_contains_headers_and_values():
    response = export_xlsx(("Keyword", "Location", "Device"), [("alpha", "India", "mobile")], "keywords.xlsx")
    with ZipFile(BytesIO(response.body)) as archive:
        worksheet = archive.read("xl/worksheets/sheet1.xml").decode()
    assert "Keyword" in worksheet
    assert "alpha" in worksheet
    assert "mobile" in worksheet


def test_tracking_location_rejects_mismatched_hierarchy_code():
    with pytest.raises(ApiError) as error:
        _resolve_tracking_location({
            "location": "India",
            "location_code": 2356,
            "location_details": {"country": "India", "state": "Haryana", "location_code": 2356},
        })
    assert error.value.status_code == 400


@pytest.fixture
def export_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    try:
        user = User(id="export-user", name="Export User", email="export@example.com", passwordHash="hash")
        project = Project(id="export-project", userId=user.id, name="Project", domain="example.com", location="India", locationCode=2356)
        db.add_all([user, project])
        db.add_all([
            Keyword(id="keyword-a", projectId=project.id, userId=user.id, keyword="alpha", location="India", device="desktop"),
            Keyword(id="keyword-b", projectId=project.id, userId=user.id, keyword="beta", location="Australia", device="mobile"),
        ])
        db.commit()
        yield db
    finally:
        db.close()
        engine.dispose()


def test_export_all_queries_entire_project_and_selected_ids_are_authorized(export_db):
    all_response = export_project_keywords("export-project", {"format": "csv"}, {"userId": "export-user"}, export_db)
    assert all_response.body.decode("utf-8-sig").count("\n") == 3

    selected_response = export_project_keywords(
        "export-project",
        {"format": "xlsx", "keyword_ids": ["keyword-b"]},
        {"userId": "export-user"},
        export_db,
    )
    with ZipFile(BytesIO(selected_response.body)) as archive:
        worksheet = archive.read("xl/worksheets/sheet1.xml").decode()
    assert "beta" in worksheet and "alpha" not in worksheet


def test_export_rejects_foreign_keyword_ids(export_db):
    with pytest.raises(ApiError) as error:
        export_project_keywords(
            "export-project",
            {"format": "csv", "keyword_ids": ["foreign-id"]},
            {"userId": "export-user"},
            export_db,
        )
    assert error.value.status_code == 403
