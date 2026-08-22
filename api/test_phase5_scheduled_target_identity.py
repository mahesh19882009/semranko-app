"""Phase 5 scheduled location/device target regressions."""

import json
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Base, Keyword, KeywordMetricsHistory, ProcessingJob, Project, RefreshJob, User
from app.services.async_bulk_service import run_weekly_bulk_update_job, run_weekly_refresh_worker
from app.services.monthly_metrics_service import run_monthly_metrics_refresh, run_monthly_refresh_worker


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def _user(db, user_id, refresh_frequency):
    user = User(
        id=user_id,
        name=user_id,
        email=f"{user_id}@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        refreshFrequency=refresh_frequency,
        creditBalance=1000,
        automaticCreditBalance=1000,
    )
    db.add(user)
    return user


def _target_rows(db, user, project_id, specs):
    project = Project(
        id=project_id,
        name=project_id,
        domain=f"{project_id}.example.com",
        userId=user.id,
    )
    db.add(project)
    rows = []
    for index, (location, location_code, device) in enumerate(specs):
        row = Keyword(
            id=f"{project_id}-keyword-{index}",
            projectId=project.id,
            userId=user.id,
            keyword="seo company",
            location=location,
            locationCode=location_code,
            device=device,
            isActive=True,
        )
        db.add(row)
        rows.append(row)
    db.commit()
    return project, rows


def _weekly_response(targets):
    response = MagicMock()
    response.headers = {"Content-Type": "application/json"}
    response.json.return_value = {
        "tasks": [
            {
                "id": f"task-{index}",
                "data": {
                    "keyword": "seo company",
                    "location_code": location_code,
                    "device": device,
                },
            }
            for index, (location_code, device) in enumerate(targets)
        ]
    }
    return response


def test_weekly_submission_uses_each_persisted_location_and_device_and_fans_out_ids():
    engine, db = _db()
    try:
        user = _user(db, "weekly-target-owner", "weekly")
        _project, rows = _target_rows(
            db,
            user,
            "weekly-target-project",
            [
                ("India", 2356, "desktop"),
                ("Faridabad", 9061655, "desktop"),
                ("Faridabad", 9061655, "mobile"),
            ],
        )
        queued = run_weekly_bulk_update_job(db)
        refresh = db.get(RefreshJob, queued["job_ids"][0])

        with patch("app.services.dataforseo_client._get_cached_serp", return_value=None), \
             patch("app.services.async_bulk_service.check_dfs_cost_ceiling", create=True), \
             patch(
                 "app.services.async_bulk_service.requests.post",
                 return_value=_weekly_response([(2356, "desktop"), (9061655, "desktop"), (9061655, "mobile")]),
             ) as provider_post:
            assert run_weekly_refresh_worker(db)["processed"] == 1

        payload = provider_post.call_args.kwargs["json"]
        assert {(item["location_code"], item["device"]) for item in payload} == {
            (2356, "desktop"), (9061655, "desktop"), (9061655, "mobile")
        }
        children = db.scalars(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh.id)).all()
        assert {json.loads(child.payload)["keyword_id"] for child in children} == {row.id for row in rows}
        assert {
            (json.loads(child.payload)["location_code"], json.loads(child.payload)["device"])
            for child in children
        } == {(2356, "desktop"), (9061655, "desktop"), (9061655, "mobile")}
    finally:
        db.close()
        engine.dispose()


def test_monthly_submission_uses_location_code_but_reuses_result_across_devices_by_exact_id():
    engine, db = _db()
    try:
        user = _user(db, "monthly-target-owner", "monthly")
        _project, rows = _target_rows(
            db,
            user,
            "monthly-target-project",
            [
                ("India", 2356, "desktop"),
                ("India", 2356, "mobile"),
                ("Faridabad", 9061655, "desktop"),
            ],
        )
        queued = run_monthly_metrics_refresh(db)

        def provider_response(_url, json=None, **_kwargs):
            code = json[0]["location_code"]
            response = MagicMock()
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "tasks": [{
                    "data": {"keyword": "seo company", "location_code": code},
                    "result": [{"items": [{
                        "keyword": "seo company",
                        "keyword_properties": {"keyword_difficulty": code},
                        "keyword_info": {"search_volume": code, "cpc": 1.0, "competition": 0.1},
                        "avg_backlinks_info": {"backlinks": 2, "referring_domains": 1},
                        "search_intent_info": {"main_intent": "commercial"},
                    }]}],
                }],
            }
            return response

        with patch("app.services.dataforseo_client._get_cached_kw_metrics", return_value=None), \
             patch("app.services.dataforseo_client._set_cached_kw_metrics"), \
             patch("app.services.dataforseo_client._log_dataforseo_cost"), \
             patch("app.services.async_bulk_service.requests.post", side_effect=provider_response) as provider_post:
            assert run_monthly_refresh_worker(db)["processed"] == 1

        assert {call.kwargs["json"][0]["location_code"] for call in provider_post.call_args_list} == {
            2356, 9061655
        }
        for row in rows:
            refreshed = db.get(Keyword, row.id)
            assert refreshed.volume == refreshed.locationCode
            assert db.scalar(
                select(KeywordMetricsHistory).where(KeywordMetricsHistory.keywordId == row.id)
            ) is not None
    finally:
        db.close()
        engine.dispose()


def test_legacy_weekly_job_does_not_guess_when_persisted_targets_are_ambiguous():
    engine, db = _db()
    try:
        user = _user(db, "legacy-ambiguous-owner", "weekly")
        _project, _rows = _target_rows(
            db,
            user,
            "legacy-ambiguous-project",
            [("India", 2356, "desktop"), ("India", 2840, "desktop")],
        )
        job = RefreshJob(
            id="legacy-ambiguous-refresh",
            jobType="weekly_serp",
            status="queued",
            batchIndex=0,
            totalBatches=1,
            keywordCount=1,
            keywordsJson=json.dumps([{"keyword": "seo company", "location": "India"}]),
        )
        db.add(job)
        db.commit()
        with patch("app.services.dataforseo_client._get_cached_serp", return_value=None), \
             patch("app.services.async_bulk_service.requests.post") as provider_post:
            assert run_weekly_refresh_worker(db)["processed"] == 1
        provider_post.assert_not_called()
        assert db.scalars(select(ProcessingJob)).all() == []
    finally:
        db.close()
        engine.dispose()
