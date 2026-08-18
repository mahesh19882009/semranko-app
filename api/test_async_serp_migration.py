"""Async SERP task_post migration regression tests.

All provider interactions are mocked. No real DataForSEO requests are made.
"""
import json
import sys
import inspect
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi import Request

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Base, User, Project, Keyword, RankResult, RefreshJob, ProcessingJob
from app.services.dataforseo_client import DataForSEOClient, get_serp_priority, SERP_PRIORITY_WEEKLY, SERP_TASK_POST_BATCH_SIZE
from app.services.async_tracking_service import submit_user_tracking_job, get_user_processing_jobs


def _make_webhook_request(payload: dict) -> Request:
    body = json.dumps(payload).encode("utf-8")
    sent = False

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {
                "type": "http.request",
                "body": body,
                "more_body": False,
            }
        return {
            "type": "http.request",
            "body": b"",
            "more_body": False,
        }

    return Request(
        {
            "type": "http",
            "method": "POST",
            "headers": [(b"content-type", b"application/json")],
            "query_string": b"",
        },
        receive=receive,
    )


def _build_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return Session(engine)


def _build_user(db: Session, plan: str = "starter"):
    user = User(
        id="async-test-user",
        name="Async Test",
        email="async@example.com",
        passwordHash="hash",
        selectedPlan=plan,
        subscriptionStatus="active",
        creditBalance=200.0,
        planCreditBalance=200.0,
        purchasedCreditBalance=0.0,
        automaticCreditBalance=0.0,
    )
    db.add(user)
    db.commit()
    return user


def _build_project(db: Session, user_id: str, domain: str = "example.com") -> Project:
    project = Project(
        id="async-test-project",
        userId=user_id,
        name="Async Test Project",
        domain=domain,
        location="India",
        locationCode=2840,
    )
    db.add(project)
    db.commit()
    return project


def _mock_task_post_response(keywords, task_ids=None, cost=0.0):
    if task_ids is None:
        task_ids = [f"task-{i}" for i in range(len(keywords))]
    tasks = []
    for i, kw in enumerate(keywords):
        tasks.append({
            "id": task_ids[i],
            "data": {"keyword": kw.get("keyword", "")},
            "cost": cost,
            "status_code": 20000,
        })
    return {"tasks": tasks}


class TestPriorityConfiguration:
    def test_all_actions_default_to_normal(self):
        assert get_serp_priority("add_keyword") is None
        assert get_serp_priority("bulk_add") is None
        assert get_serp_priority("manual_refresh") is None
        assert get_serp_priority("automatic") is None
        assert get_serp_priority("weekly") is None
        assert get_serp_priority("monthly") is None

    def test_weekly_default_is_normal_not_legacy_high(self):
        assert SERP_PRIORITY_WEEKLY is None

    def test_invalid_action_returns_none(self):
        assert get_serp_priority("nonexistent") is None

    def test_batch_size_configured(self):
        assert SERP_TASK_POST_BATCH_SIZE == 100


class TestAddKeywordSubmitsTaskPost:
    def test_single_add_uses_task_post_with_normal_priority(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        try:
            mock_response = _mock_task_post_response([{"keyword": "test keyword"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )) as mock_post:
                result = submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "test keyword"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2840,
                    depth=100,
                    cost_per_keyword=20,
                )

            assert result["refresh_job_id"] is not None
            assert mock_post.called
            called_url = mock_post.call_args[0][0]
            assert "task_post" in called_url
            assert "live/advanced" not in called_url
            payload = mock_post.call_args[1]["json"]
            assert len(payload) == 1
            assert payload[0]["keyword"] == "test keyword"
            assert payload[0]["depth"] == 100
            assert payload[0]["priority"] is None
            assert payload[0]["location_code"] == 2840
        finally:
            db.close()

    def test_single_add_preserves_location_language_device(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        try:
            mock_response = _mock_task_post_response([{"keyword": "test keyword"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )) as mock_post:
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "test keyword"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2840,
                    language_code="en",
                    device="mobile",
                    depth=100,
                    cost_per_keyword=20,
                )

            payload = mock_post.call_args[1]["json"]
            assert payload[0]["location_code"] == 2840
            assert payload[0]["device"] == "mobile"
            assert payload[0]["language_code"] == "en"
        finally:
            db.close()

    def test_single_add_stop_crawl_payload_uses_normalized_domain(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id, domain="www.Example.com")
        try:
            mock_response = _mock_task_post_response([{"keyword": "test keyword"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )) as mock_post:
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "test keyword"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2840,
                    depth=100,
                    cost_per_keyword=20,
                )

            payload = mock_post.call_args[1]["json"]
            assert payload[0]["stop_crawl_on_match"] == [
                {"match_type": "with_subdomains", "match_value": "example.com"}
            ]
        finally:
            db.close()


class TestBulkAddSubmitsTaskPost:
    def test_bulk_add_submits_batched_tasks(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        try:
            keywords = [{"keyword": f"keyword {i}"} for i in range(5)]
            mock_response = _mock_task_post_response(keywords)
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )) as mock_post:
                result = submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=keywords,
                    domain=project.domain,
                    action="bulk_add",
                    location_code=2840,
                    depth=100,
                    cost_per_keyword=20,
                )

            assert result["refresh_job_id"] is not None
            assert mock_post.called
            payload = mock_post.call_args[1]["json"]
            assert len(payload) == 5
            for i, task in enumerate(payload):
                assert task["keyword"] == f"keyword {i}"
                assert task["depth"] == 100
                assert task["priority"] is None
        finally:
            db.close()

    def test_bulk_add_maps_task_ids_to_keywords(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        try:
            keywords = [{"keyword": f"keyword {i}"} for i in range(3)]
            task_ids = ["task-a", "task-b", "task-c"]
            mock_response = _mock_task_post_response(keywords, task_ids=task_ids)
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )):
                result = submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=keywords,
                    domain=project.domain,
                    action="bulk_add",
                    location_code=2840,
                    depth=100,
                    cost_per_keyword=20,
                )

            assert result["refresh_job_id"] is not None
            assert len(result["task_ids"]) == 3
            assert result["submitted"] == ["keyword 0", "keyword 1", "keyword 2"]
        finally:
            db.close()


class TestManualRefreshSubmitsTaskPost:
    def test_manual_refresh_uses_task_post_with_normal_priority(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        try:
            keyword = Keyword(
                projectId=project.id,
                userId=user.id,
                keyword="existing keyword",
                location="India",
                device="desktop",
            )
            db.add(keyword)
            db.commit()

            mock_response = _mock_task_post_response([{"keyword": "existing keyword"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )) as mock_post:
                result = submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "existing keyword"}],
                    domain=project.domain,
                    action="manual_refresh",
                    location_code=2840,
                    depth=100,
                    cost_per_keyword=20,
                )

            assert result["refresh_job_id"] is not None
            assert mock_post.called
            payload = mock_post.call_args[1]["json"]
            assert len(payload) == 1
            assert payload[0]["keyword"] == "existing keyword"
            assert payload[0]["depth"] == 100
            assert payload[0]["priority"] is None
        finally:
            db.close()


class TestNoLiveFallback:
    def test_no_live_advanced_in_active_tracking_modules(self):
        import app.services.async_tracking_service as ats
        import app.api.routes.keywords as kw_routes
        import app.services.async_bulk_service as abs_svc
        import app.workers.refresh_worker as rw

        for mod in [ats, kw_routes, abs_svc, rw]:
            source = inspect.getsource(mod)
            assert "serp/google/organic/live/advanced" not in source, f"{mod.__name__} still references Live"

    def test_task_post_endpoint_used_not_live(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        try:
            mock_response = _mock_task_post_response([{"keyword": "test"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )) as mock_post:
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "test"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2840,
                    depth=100,
                    cost_per_keyword=20,
                )

            called_url = mock_post.call_args[0][0]
            assert "task_post" in called_url
            assert "live/advanced" not in called_url
        finally:
            db.close()


class TestProcessingPersistence:
    def test_processing_jobs_created_for_new_keywords(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        keyword = Keyword(
            projectId=project.id,
            userId=user.id,
            keyword="persist test",
            location="India",
            device="desktop",
        )
        db.add(keyword)
        db.commit()
        try:
            mock_response = _mock_task_post_response([{"keyword": "persist test"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "persist test"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2840,
                    depth=100,
                    cost_per_keyword=20,
                )

            jobs = db.scalars(select(ProcessingJob)).all()
            assert len(jobs) == 1
            assert jobs[0].keywordText == "persist test"
            assert jobs[0].status == "pending"
        finally:
            db.close()

    def test_processing_jobs_survive_reload(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        keyword = Keyword(
            projectId=project.id,
            userId=user.id,
            keyword="reload test",
            location="United States",
            device="desktop",
        )
        db.add(keyword)
        db.commit()
        try:
            mock_response = _mock_task_post_response([{"keyword": "reload test"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "reload test"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2840,
                    depth=100,
                    cost_per_keyword=20,
                )

            jobs = get_user_processing_jobs(db, user.id, project.id)
            assert len(jobs) == 1
            assert jobs[0]["keyword"] == "reload test"
            assert jobs[0]["status"] == "pending"
        finally:
            db.close()


class TestCreditLifecycle:
    def test_reservation_created_once(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        try:
            mock_response = _mock_task_post_response([{"keyword": "credit test"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "credit test"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2840,
                    depth=100,
                    cost_per_keyword=20,
                )

            from app.db.models import CreditLedger
            reservations = db.scalars(
                select(CreditLedger).where(
                    CreditLedger.userId == user.id,
                    CreditLedger.actionType == "reservation",
                    CreditLedger.status == "pending",
                )
            ).all()
            assert len(reservations) == 1
        finally:
            db.close()


class TestWebhookDeduplication:
    def test_duplicate_webhook_does_not_create_duplicate_processing_job(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        try:
            mock_response = _mock_task_post_response([{"keyword": "dedup test"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "dedup test"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2840,
                    depth=100,
                    cost_per_keyword=20,
                )

            refresh_job = db.scalar(select(RefreshJob).where(RefreshJob.jobType == "add_keyword"))
            assert refresh_job is not None
            task_id = (json.loads(refresh_job.dataforseoRequestIds or "[]") or [None])[0]
            assert task_id is not None

            webhook_payload = {
                "task_id": task_id,
                "tasks": [
                    {
                        "data": {"keyword": "dedup test", "location_code": 2840},
                        "result": [
                            {
                                "items": [
                                    {"type": "organic", "rank_group": 5, "url": "https://example.com/page"}
                                ]
                            }
                        ]
                    }
                ]
            }

            from app.api.routes.webhooks import dataforseo_webhook
            from fastapi import Request
            import app.api.routes.webhooks as webhooks_mod

            original_sessionlocal = webhooks_mod.SessionLocal
            webhooks_mod.SessionLocal = lambda: db
            try:
                import asyncio

                result1 = asyncio.run(
                    dataforseo_webhook(_make_webhook_request(webhook_payload))
                )
                result2 = asyncio.run(
                    dataforseo_webhook(_make_webhook_request(webhook_payload))
                )

                assert result1.get("updated") == 1
                assert result1.get("skipped") == 0

                # A duplicate webhook received before the worker completes
                # updates the same pending ProcessingJob again.
                assert result2.get("updated") == 1
                assert result2.get("skipped") == 0

                jobs = db.scalars(select(ProcessingJob)).all()
                assert len(jobs) == 1
            finally:
                webhooks_mod.SessionLocal = original_sessionlocal
        finally:
            db.close()

    def test_webhook_ranked_result_creates_processing_job_with_position(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        try:
            mock_response = _mock_task_post_response([{"keyword": "ranked test"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "ranked test"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2840,
                    depth=100,
                    cost_per_keyword=20,
                )

            refresh_job = db.scalar(select(RefreshJob).where(RefreshJob.jobType == "add_keyword"))
            task_id = (json.loads(refresh_job.dataforseoRequestIds or "[]") or [None])[0]
            refresh_job_id = refresh_job.id

            webhook_payload = {
                "task_id": task_id,
                "tasks": [
                    {
                        "data": {"keyword": "ranked test", "location_code": 2840},
                        "result": [
                            {
                                "items": [
                                    {"type": "organic", "rank_group": 27, "url": "https://example.com/ranked"}
                                ]
                            }
                        ]
                    }
                ]
            }

            from app.api.routes.webhooks import dataforseo_webhook
            from fastapi import Request
            import app.api.routes.webhooks as webhooks_mod

            original_sessionlocal = webhooks_mod.SessionLocal
            webhooks_mod.SessionLocal = lambda: db
            try:
                request = _make_webhook_request(webhook_payload)

                import asyncio
                asyncio.run(dataforseo_webhook(request))

                job = db.scalar(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh_job_id))
                assert job is not None
                payload = json.loads(job.payload or "{}")
                assert payload.get("position") == 27
                assert payload.get("url") == "https://example.com/ranked"
            finally:
                webhooks_mod.SessionLocal = original_sessionlocal
        finally:
            db.close()

    def test_webhook_valid_unranked_creates_processing_job_with_null_position(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        try:
            mock_response = _mock_task_post_response([{"keyword": "unranked test"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "unranked test"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2840,
                    depth=100,
                    cost_per_keyword=20,
                )

            refresh_job = db.scalar(select(RefreshJob).where(RefreshJob.jobType == "add_keyword"))
            task_id = (json.loads(refresh_job.dataforseoRequestIds or "[]") or [None])[0]
            refresh_job_id = refresh_job.id

            webhook_payload = {
                "task_id": task_id,
                "tasks": [
                    {
                        "data": {"keyword": "unranked test", "location_code": 2840},
                        "result": [
                            {
                                "items": []
                            }
                        ]
                    }
                ]
            }

            from app.api.routes.webhooks import dataforseo_webhook
            from fastapi import Request
            import app.api.routes.webhooks as webhooks_mod

            original_sessionlocal = webhooks_mod.SessionLocal
            webhooks_mod.SessionLocal = lambda: db
            try:
                request = _make_webhook_request(webhook_payload)

                import asyncio
                asyncio.run(dataforseo_webhook(request))

                job = db.scalar(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh_job_id))
                assert job is not None
                payload = json.loads(job.payload or "{}")
                assert payload.get("position") is None
                assert payload.get("url") is None
            finally:
                webhooks_mod.SessionLocal = original_sessionlocal
        finally:
            db.close()