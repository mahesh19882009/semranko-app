"""Focused async SERP result processing regression tests.

Tests domain matching, AIO matching, worker execution, cache metadata,
credit safety, and result semantics for the canonical postback -> worker path.
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import asyncio

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and not loop.is_closed():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
            asyncio.set_event_loop(None)

def _make_webhook_request(payload: dict) -> Request:
    request = Request({
        "type": "http",
        "method": "POST",
        "headers": [
            (b"content-type", b"application/json"),
        ],
        "query_string": b"",
    })

    request._body = json.dumps(payload).encode("utf-8")
    return request

from app.db.models import Base, User, Project, Keyword, RankResult, RefreshJob, ProcessingJob, CreditLedger
from app.services.async_tracking_service import (
    submit_user_tracking_job,
    get_user_processing_jobs,
    recover_stale_user_tracking_jobs,
)
from app.services.credit_service import reserve_credits, consume_reserved, refund_reserved
from app.workers.refresh_worker import (
    claim_processing_jobs,
    run_refresh_worker,
    process_processing_job,
    process_pending_processing_jobs,
)
from app.api.routes.webhooks import (
    dataforseo_webhook,
    _aio_cites_target_domain,
    _find_refresh_job_by_task_id,
)
from app.api.routes.keywords import create_keyword, bulk_create_keywords
from app.core.errors import ApiError
from fastapi import Request


def _build_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return Session(engine)


def _build_user(db: Session, plan: str = "starter"):
    user = User(
        id="proc-test-user",
        name="Proc Test",
        email="proc@example.com",
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
        id="proc-test-project",
        userId=user_id,
        name="Proc Test Project",
        domain=domain,
        location="India",
        locationCode=2840,
    )
    db.add(project)
    db.commit()
    return project


def _build_keyword(db: Session, project_id: str, keyword: str, location: str = "India"):
    kw = Keyword(
        projectId=project_id,
        userId="proc-test-user",
        keyword=keyword,
        location=location,
        device="desktop",
        isActive=True,
    )
    db.add(kw)
    db.commit()
    return kw


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


class TestDomainMatching:
    def test_target_domain_ranked_5(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id, domain="example.com")
        _build_keyword(db, project.id, "ranked test")
        try:
            mock_response = _mock_task_post_response([{"keyword": "ranked test"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )), patch("app.services.async_tracking_service._get_cached_serp", return_value=None):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "ranked test"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2356,
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
                        "data": {"keyword": "ranked test", "location_code": 2356},
                        "result": [
                            {
                                "items": [
                                    {"type": "organic", "rank_group": 5, "url": "https://example.com/ranked", "domain": "example.com"},
                                    {"type": "organic", "rank_group": 10, "url": "https://other.com/page", "domain": "other.com"},
                                ]
                            }
                        ]
                    }
                ]
            }

            import app.api.routes.webhooks as webhooks_mod
            original_sessionlocal = webhooks_mod.SessionLocal
            webhooks_mod.SessionLocal = lambda: db
            try:
                request = _make_webhook_request(webhook_payload)

                import asyncio
                result = _run_async(dataforseo_webhook(request))
                # created may be 0 when updating existing job

                job = db.scalar(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh_job_id))
                assert job is not None
                payload = json.loads(job.payload or "{}")
                assert payload.get("position") == 5
                assert payload.get("url") == "https://example.com/ranked"
            finally:
                webhooks_mod.SessionLocal = original_sessionlocal
        finally:
            db.close()

    def test_target_domain_ranked_64(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id, domain="example.com")
        _build_keyword(db, project.id, "ranked test")
        try:
            mock_response = _mock_task_post_response([{"keyword": "ranked test"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )), patch("app.services.async_tracking_service._get_cached_serp", return_value=None):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "ranked test"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2356,
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
                        "data": {"keyword": "ranked test", "location_code": 2356},
                        "result": [
                            {
                                "items": [
                                    {"type": "organic", "rank_group": 64, "url": "https://www.example.com/page", "domain": "www.example.com"},
                                    {"type": "organic", "rank_group": 70, "url": "https://other.com/page", "domain": "other.com"},
                                ]
                            }
                        ]
                    }
                ]
            }

            import app.api.routes.webhooks as webhooks_mod
            original_sessionlocal = webhooks_mod.SessionLocal
            webhooks_mod.SessionLocal = lambda: db
            try:
                request = _make_webhook_request(webhook_payload)

                import asyncio
                result = _run_async(dataforseo_webhook(request))
                # created may be 0 when updating existing job

                job = db.scalar(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh_job_id))
                assert job is not None
                payload = json.loads(job.payload or "{}")
                assert payload.get("position") == 64
                assert payload.get("url") == "https://www.example.com/page"
            finally:
                webhooks_mod.SessionLocal = original_sessionlocal
        finally:
            db.close()

    def test_target_domain_ranked_98(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id, domain="example.com")
        _build_keyword(db, project.id, "ranked test")
        try:
            mock_response = _mock_task_post_response([{"keyword": "ranked test"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )), patch("app.services.async_tracking_service._get_cached_serp", return_value=None):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "ranked test"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2356,
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
                        "data": {"keyword": "ranked test", "location_code": 2356},
                        "result": [
                            {
                                "items": [
                                    {"type": "organic", "rank_group": 98, "url": "https://mail.example.com/inbox", "domain": "mail.example.com"},
                                ]
                            }
                        ]
                    }
                ]
            }

            import app.api.routes.webhooks as webhooks_mod
            original_sessionlocal = webhooks_mod.SessionLocal
            webhooks_mod.SessionLocal = lambda: db
            try:
                request = _make_webhook_request(webhook_payload)

                import asyncio
                result = _run_async(dataforseo_webhook(request))
                # created may be 0 when updating existing job

                job = db.scalar(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh_job_id))
                assert job is not None
                payload = json.loads(job.payload or "{}")
                assert payload.get("position") == 98
                assert payload.get("url") == "https://mail.example.com/inbox"
            finally:
                webhooks_mod.SessionLocal = original_sessionlocal
        finally:
            db.close()

    def test_unrelated_organic_results_ignored(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id, domain="example.com")
        _build_keyword(db, project.id, "ranked test")
        try:
            mock_response = _mock_task_post_response([{"keyword": "ranked test"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )), patch("app.services.async_tracking_service._get_cached_serp", return_value=None):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "ranked test"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2356,
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
                        "data": {"keyword": "ranked test", "location_code": 2356},
                        "result": [
                            {
                                "items": [
                                    {"type": "organic", "rank_group": 1, "url": "https://other.com/one", "domain": "other.com"},
                                    {"type": "organic", "rank_group": 2, "url": "https://unrelated.org/two", "domain": "unrelated.org"},
                                ]
                            }
                        ]
                    }
                ]
            }

            import app.api.routes.webhooks as webhooks_mod
            original_sessionlocal = webhooks_mod.SessionLocal
            webhooks_mod.SessionLocal = lambda: db
            try:
                request = _make_webhook_request(webhook_payload)

                import asyncio
                result = _run_async(dataforseo_webhook(request))
                # created may be 0 when updating existing job

                job = db.scalar(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh_job_id))
                assert job is not None
                payload = json.loads(job.payload or "{}")
                assert payload.get("position") is None
                assert payload.get("url") is None
            finally:
                webhooks_mod.SessionLocal = original_sessionlocal
        finally:
            db.close()

    def test_valid_top100_unranked(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id, domain="example.com")
        _build_keyword(db, project.id, "unranked test")
        try:
            mock_response = _mock_task_post_response([{"keyword": "unranked test"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )), patch("app.services.async_tracking_service._get_cached_serp", return_value=None):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "unranked test"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2356,
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
                        "data": {"keyword": "unranked test", "location_code": 2356},
                        "result": [
                            {
                                "items": [
                                    {"type": "organic", "rank_group": 1, "url": "https://other.com/one", "domain": "other.com"},
                                    {"type": "organic", "rank_group": 2, "url": "https://unrelated.org/two", "domain": "unrelated.org"},
                                ]
                            }
                        ]
                    }
                ]
            }

            import app.api.routes.webhooks as webhooks_mod
            original_sessionlocal = webhooks_mod.SessionLocal
            webhooks_mod.SessionLocal = lambda: db
            try:
                request = _make_webhook_request(webhook_payload)

                import asyncio
                result = _run_async(dataforseo_webhook(request))
                # created may be 0 when updating existing job

                job = db.scalar(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh_job_id))
                assert job is not None
                payload = json.loads(job.payload or "{}")
                assert payload.get("position") is None
                assert payload.get("url") is None
            finally:
                webhooks_mod.SessionLocal = original_sessionlocal
        finally:
            db.close()


class TestAioMatching:
    def test_aio_unrelated_domain_is_false(self):
        assert _aio_cites_target_domain("example.com", {
            "type": "ai_overview",
            "ai_overview_reference": [
                {"url": "https://other.com/ref1", "domain": "other.com"},
                {"url": "https://unrelated.org/ref2", "domain": "unrelated.org"},
            ]
        }) is False

    def test_aio_target_domain_cited_is_true(self):
        assert _aio_cites_target_domain("example.com", {
            "type": "ai_overview",
            "ai_overview_reference": [
                {"url": "https://other.com/ref1", "domain": "other.com"},
                {"url": "https://example.com/cited", "domain": "example.com"},
            ]
        }) is True

    def test_aio_subdomain_cited_is_true(self):
        assert _aio_cites_target_domain("example.com", {
            "type": "ai_overview",
            "references": [
                {"url": "https://blog.example.com/post", "domain": "blog.example.com"},
            ]
        }) is True


class TestWorkerMetadata:
    def test_add_uses_depth_100(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        _build_keyword(db, project.id, "depth test unique 001")
        try:
            mock_response = _mock_task_post_response([{"keyword": "depth test unique 001"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )), patch("app.services.async_tracking_service._get_cached_serp", return_value=None):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "depth test unique 001"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2356,
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
                        "data": {"keyword": "depth test unique 001", "location_code": 2356},
                        "result": [
                            {
                                "items": [
                                    {"type": "organic", "rank_group": 5, "url": "https://example.com/page", "domain": "example.com"},
                                ]
                            }
                        ]
                    }
                ]
            }

            import app.api.routes.webhooks as webhooks_mod
            original_sessionlocal = webhooks_mod.SessionLocal
            webhooks_mod.SessionLocal = lambda: db
            try:
                request = _make_webhook_request(webhook_payload)

                import asyncio
                _run_async(dataforseo_webhook(request))
            finally:
                webhooks_mod.SessionLocal = original_sessionlocal

            pending_jobs = db.scalars(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh_job_id)).all()
            for pending_job in pending_jobs:
                process_processing_job(db, pending_job)

            kw = db.scalar(select(Keyword).where(Keyword.keyword == "depth test unique 001"))
            assert kw is not None
            assert kw.position == 5
            assert kw.lastWeeklyRefreshAt is None
            assert kw.weeklyRefreshStatus != "success"
        finally:
            db.close()

    def test_manual_uses_depth_100(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        _build_keyword(db, project.id, "manual depth test unique 002")
        try:
            mock_response = _mock_task_post_response([{"keyword": "manual depth test unique 002"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )), patch("app.services.async_tracking_service._get_cached_serp", return_value=None):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "manual depth test unique 002"}],
                    domain=project.domain,
                    action="manual_refresh",
                    location_code=2356,
                    depth=100,
                    cost_per_keyword=20,
                )

            refresh_job = db.scalar(select(RefreshJob).where(RefreshJob.jobType == "manual_refresh"))
            task_id = (json.loads(refresh_job.dataforseoRequestIds or "[]") or [None])[0]
            refresh_job_id = refresh_job.id

            webhook_payload = {
                "task_id": task_id,
                "tasks": [
                    {
                        "data": {"keyword": "manual depth test unique 002", "location_code": 2356},
                        "result": [
                            {
                                "items": [
                                    {"type": "organic", "rank_group": 12, "url": "https://example.com/page", "domain": "example.com"},
                                ]
                            }
                        ]
                    }
                ]
            }

            import app.api.routes.webhooks as webhooks_mod
            original_sessionlocal = webhooks_mod.SessionLocal
            webhooks_mod.SessionLocal = lambda: db
            try:
                request = _make_webhook_request(webhook_payload)

                import asyncio
                _run_async(dataforseo_webhook(request))
            finally:
                webhooks_mod.SessionLocal = original_sessionlocal

            pending_jobs = db.scalars(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh_job_id)).all()
            for pending_job in pending_jobs:
                process_processing_job(db, pending_job)

            kw = db.scalar(select(Keyword).where(Keyword.keyword == "manual depth test unique 002"))
            assert kw is not None
            assert kw.position == 12
            assert kw.lastWeeklyRefreshAt is None
            assert kw.weeklyRefreshStatus != "success"
        finally:
            db.close()

    def test_weekly_preserves_own_semantics(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        _build_keyword(db, project.id, "weekly test unique 003")
        try:
            mock_response = _mock_task_post_response([{"keyword": "weekly test unique 003"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )), patch("app.services.async_tracking_service._get_cached_serp", return_value=None):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "weekly test unique 003"}],
                    domain=project.domain,
                    action="weekly",
                    location_code=2356,
                    depth=10,
                    cost_per_keyword=10,
                )

            refresh_job = db.scalar(select(RefreshJob).where(RefreshJob.jobType == "weekly"))
            task_id = (json.loads(refresh_job.dataforseoRequestIds or "[]") or [None])[0]
            refresh_job_id = refresh_job.id

            webhook_payload = {
                "task_id": task_id,
                "tasks": [
                    {
                        "data": {"keyword": "weekly test unique 003", "location_code": 2356},
                        "result": [
                            {
                                "items": [
                                    {"type": "organic", "rank_group": 3, "url": "https://example.com/page", "domain": "example.com"},
                                ]
                            }
                        ]
                    }
                ]
            }

            import app.api.routes.webhooks as webhooks_mod
            original_sessionlocal = webhooks_mod.SessionLocal
            webhooks_mod.SessionLocal = lambda: db
            try:
                request = _make_webhook_request(webhook_payload)

                import asyncio
                _run_async(dataforseo_webhook(request))
            finally:
                webhooks_mod.SessionLocal = original_sessionlocal

            pending_jobs = db.scalars(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh_job_id)).all()
            for pending_job in pending_jobs:
                process_processing_job(db, pending_job)

            kw = db.scalar(select(Keyword).where(Keyword.keyword == "weekly test unique 003"))
            assert kw is not None
            assert kw.position == 3
            assert kw.lastWeeklyRefreshAt is not None
            assert kw.weeklyRefreshStatus == "success"
        finally:
            db.close()


class TestWorkerInvocation:
    def test_worker_invoked_after_postback(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        _build_keyword(db, project.id, "auto process test unique 004")
        try:
            mock_response = _mock_task_post_response([{"keyword": "auto process test unique 004"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )), patch("app.services.async_tracking_service._get_cached_serp", return_value=None):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "auto process test unique 004"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2356,
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
                        "data": {"keyword": "auto process test unique 004", "location_code": 2356},
                        "result": [
                            {
                                "items": [
                                    {"type": "organic", "rank_group": 8, "url": "https://example.com/page", "domain": "example.com"},
                                ]
                            }
                        ]
                    }
                ]
            }

            import app.api.routes.webhooks as webhooks_mod
            original_sessionlocal = webhooks_mod.SessionLocal
            webhooks_mod.SessionLocal = lambda: db
            try:
                request = _make_webhook_request(webhook_payload)

                import asyncio
                _run_async(dataforseo_webhook(request))
            finally:
                webhooks_mod.SessionLocal = original_sessionlocal

            jobs_before = db.scalars(select(ProcessingJob).where(ProcessingJob.status == "pending")).all()
            assert len(jobs_before) == 1

            job = jobs_before[0]
            process_processing_job(db, job)

            jobs_after = db.scalars(select(ProcessingJob).where(ProcessingJob.status == "pending")).all()
            assert len(jobs_after) == 0

            kw = db.scalar(select(Keyword).where(Keyword.keyword == "auto process test unique 004"))
            assert kw is not None
            assert kw.position == 8
        finally:
            db.close()

    def test_duplicate_postback_does_not_double_run(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        _build_keyword(db, project.id, "dup test unique 005")
        try:
            mock_response = _mock_task_post_response([{"keyword": "dup test unique 005"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )), patch("app.services.async_tracking_service._get_cached_serp", return_value=None):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "dup test unique 005"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2356,
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
                        "data": {"keyword": "dup test unique 005", "location_code": 2356},
                        "result": [
                            {
                                "items": [
                                    {"type": "organic", "rank_group": 5, "url": "https://example.com/page", "domain": "example.com"},
                                ]
                            }
                        ]
                    }
                ]
            }

            import app.api.routes.webhooks as webhooks_mod
            original_sessionlocal = webhooks_mod.SessionLocal
            webhooks_mod.SessionLocal = lambda: db
            try:
                request = _make_webhook_request(webhook_payload)

                import asyncio
                _run_async(dataforseo_webhook(request))
                _run_async(dataforseo_webhook(request))
            finally:
                webhooks_mod.SessionLocal = original_sessionlocal

            pending_jobs = db.scalars(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh_job_id)).all()
            for pending_job in pending_jobs:
                process_processing_job(db, pending_job)

            rank_results = db.scalars(select(RankResult).where(RankResult.keywordText == "dup test unique 005")).all()
            assert len(rank_results) == 1
        finally:
            db.close()


class TestCreditSafety:
    def test_cached_completion_consumes_reserved_credit(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        _build_keyword(db, project.id, "cached credit test")
        cached = {
            "organic_items": [
                {"type": "organic", "rank_group": 3, "url": "https://example.com/cached", "domain": "example.com"},
            ],
            "items": [],
        }
        try:
            with patch("app.services.async_tracking_service._get_cached_serp", return_value=cached), patch(
                "app.services.async_tracking_service._enrich_keyword_metrics",
                return_value={"requested": 1, "updated": 0, "missing": 1},
            ):
                result = submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "cached credit test"}],
                    domain=project.domain,
                    action="add_keyword",
                    cost_per_keyword=20,
                )

            ledger = db.scalar(select(CreditLedger).where(CreditLedger.userId == user.id))
            assert result["cached_count"] == 1
            assert ledger.status == "completed"
            assert ledger.creditsConsumed == 20.0
            assert ledger.creditsRefunded == 0.0
        finally:
            db.close()

    def test_missing_provider_result_refunds_reserved_credit(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        kw = _build_keyword(db, project.id, "missing result credit test")
        reference = f"add_keyword:{user.id}:{project.id}:missing"
        try:
            reserve_credits(db, user.id, 20.0, "reservation", "Add keyword reservation", reference=reference, project_id=project.id)
            job = ProcessingJob(
                refreshJobId="",
                keywordText=kw.keyword,
                location="India",
                status="pending",
                deduplicationKey="missing-result-credit",
                payload=json.dumps({
                    "first_block": None,
                    "task_id": "task-missing",
                    "action": "add_keyword",
                    "credit_reference": reference,
                    "cost_per_keyword": 20,
                    "user_id": user.id,
                    "project_id": project.id,
                }),
            )
            db.add(job)
            db.commit()

            assert process_processing_job(db, job) is False
            ledger = db.scalar(select(CreditLedger).where(CreditLedger.userId == user.id))
            assert ledger.creditsRefunded == 20.0
            assert user.creditBalance == 200.0
        finally:
            db.close()

    def test_worker_failure_after_credit_step_rolls_back_charge_and_retries(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        kw = _build_keyword(db, project.id, "atomic worker credit")
        reference = f"add_keyword:{user.id}:{project.id}:atomic"
        reserve_credits(db, user.id, 20.0, "reservation", "Add keyword reservation", reference=reference, project_id=project.id)
        job = ProcessingJob(
            refreshJobId="",
            keywordText=kw.keyword,
            location="India",
            status="processing",
            deduplicationKey="atomic-worker-credit",
            payload=json.dumps({
                "position": 4,
                "url": "https://example.com/atomic",
                "task_id": "task-atomic",
                "first_block": {"items": []},
                "action": "add_keyword",
                "credit_reference": reference,
                "cost_per_keyword": 20,
                "user_id": user.id,
                "project_id": project.id,
                "domain": project.domain,
            }),
        )
        db.add(job)
        db.commit()
        try:
            with patch("app.workers.refresh_worker._set_cached_serp", side_effect=RuntimeError("cache write crash")):
                assert process_processing_job(db, job) is False

            db.refresh(job)
            db.refresh(kw)
            ledger = db.scalar(select(CreditLedger).where(CreditLedger.userId == user.id))
            rank_results = db.scalars(select(RankResult).where(RankResult.keywordId == kw.id)).all()
            assert job.status == "retry"
            assert ledger.creditsConsumed == 0.0
            assert rank_results == []
            assert kw.position is None
        finally:
            db.close()

    def test_exhausted_worker_failure_refunds_and_clears_processing_state(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        kw = _build_keyword(db, project.id, "exhausted worker credit")
        kw.processingTimeoutAt = datetime.utcnow() + timedelta(hours=24)
        reference = f"add_keyword:{user.id}:{project.id}:exhausted"
        reserve_credits(db, user.id, 20.0, "reservation", "Add keyword reservation", reference=reference, project_id=project.id)
        job = ProcessingJob(
            refreshJobId="",
            keywordText=kw.keyword,
            location="India",
            status="processing",
            maxRetries=0,
            deduplicationKey="exhausted-worker-credit",
            payload=json.dumps({
                "position": 4,
                "url": "https://example.com/exhausted",
                "task_id": "task-exhausted",
                "first_block": {"items": []},
                "action": "add_keyword",
                "credit_reference": reference,
                "cost_per_keyword": 20,
                "user_id": user.id,
                "project_id": project.id,
                "domain": project.domain,
            }),
        )
        db.add(job)
        db.commit()
        try:
            with patch("app.workers.refresh_worker._set_cached_serp", side_effect=RuntimeError("persistent cache failure")):
                assert process_processing_job(db, job) is False

            db.refresh(job)
            db.refresh(kw)
            ledger = db.scalar(select(CreditLedger).where(CreditLedger.userId == user.id))
            assert job.status == "failed"
            assert ledger.creditsConsumed == 0.0
            assert ledger.creditsRefunded == 20.0
            assert kw.processingTimeoutAt is None
        finally:
            db.close()

    def test_add_does_not_receive_weekly_deduction(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        kw = _build_keyword(db, project.id, "credit test unique 006")
        try:
            reference = f"add_keyword:{user.id}:{project.id}:9999"
            reserve_credits(db, user.id, 20.0, "reservation", "Add keyword reservation", reference=reference, project_id=project.id)

            job = ProcessingJob(
                refreshJobId="",
                keywordText="credit test unique 006",
                location="India",
                status="pending",
                deduplicationKey=f"test:credit_test:{kw.id}",
                payload=json.dumps({
                    "position": 5,
                    "url": "https://example.com/page",
                    "has_aio_badge": None,
                    "ai_description": None,
                    "task_id": "task-credit",
                    "location_code": 2356,
                    "first_block": {
                        "items": [
                            {"type": "organic", "rank_group": 5, "url": "https://example.com/page", "domain": "example.com"},
                        ]
                    },
                    "action": "add_keyword",
                    "credit_reference": reference,
                    "cost_per_keyword": 20,
                    "domain": "example.com",
                    "user_id": user.id,
                    "project_id": project.id,
                }),
            )
            db.add(job)
            db.commit()

            process_processing_job(db, job)

            ledger = db.scalars(select(CreditLedger).where(CreditLedger.userId == user.id)).all()
            weekly_deductions = [l for l in ledger if "Weekly tracking" in (l.description or "")]
            assert len(weekly_deductions) == 0

            add_deductions = [l for l in ledger if "Add keyword" in (l.description or "")]
            assert len(add_deductions) == 1
        finally:
            db.close()

    def test_duplicate_completion_does_not_double_charge(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        kw = _build_keyword(db, project.id, "dup charge test unique 007")
        try:
            reference = f"add_keyword:{user.id}:{project.id}:9998"
            reserve_credits(db, user.id, 20.0, "reservation", "Add keyword reservation", reference=reference, project_id=project.id)

            job = ProcessingJob(
                refreshJobId="",
                keywordText="dup charge test unique 007",
                location="India",
                status="pending",
                deduplicationKey=f"test:dup_charge_test:{kw.id}",
                payload=json.dumps({
                    "position": 5,
                    "url": "https://example.com/page",
                    "has_aio_badge": None,
                    "ai_description": None,
                    "task_id": "task-dup",
                    "location_code": 2356,
                    "first_block": {
                        "items": [
                            {"type": "organic", "rank_group": 5, "url": "https://example.com/page", "domain": "example.com"},
                        ]
                    },
                    "action": "add_keyword",
                    "credit_reference": reference,
                    "cost_per_keyword": 20,
                    "domain": "example.com",
                    "user_id": user.id,
                    "project_id": project.id,
                }),
            )
            db.add(job)
            db.commit()

            process_processing_job(db, job)
            db.refresh(job)

            process_processing_job(db, job)

            ledger = db.scalars(select(CreditLedger).where(CreditLedger.userId == user.id)).all()
            add_deductions = [l for l in ledger if "Add keyword" in (l.description or "")]
            assert len(add_deductions) == 1
        finally:
            db.close()

    def test_failed_provider_result_remains_failed(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        kw = _build_keyword(db, project.id, "fail test unique 008")
        try:
            job = ProcessingJob(
                refreshJobId="",
                keywordText="fail test unique 008",
                location="India",
                status="pending",
                deduplicationKey=f"test:fail_test:{kw.id}",
                payload=json.dumps({
                    "position": None,
                    "url": None,
                    "has_aio_badge": None,
                    "ai_description": None,
                    "task_id": "task-fail",
                    "location_code": 2356,
                    "first_block": None,
                    "action": "add_keyword",
                    "credit_reference": None,
                    "cost_per_keyword": 20,
                    "domain": "example.com",
                    "user_id": user.id,
                    "project_id": project.id,
                }),
            )
            db.add(job)
            db.commit()

            result = process_processing_job(db, job)

            rank_results = db.scalars(select(RankResult).where(RankResult.keywordText == "fail test unique 008")).all()
            assert len(rank_results) == 0

            kw_after = db.scalar(select(Keyword).where(Keyword.keyword == "fail test unique 008"))
            assert kw_after.position is None
        finally:
            db.close()


class TestResultSemantics:
    def test_worker_success_after_valid_result(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        _build_keyword(db, project.id, "success test unique 009")
        try:
            mock_response = _mock_task_post_response([{"keyword": "success test unique 009"}])
            with patch("app.services.dataforseo_client.requests.post", return_value=MagicMock(
                status_code=200,
                headers={"Content-Type": "application/json"},
                json=MagicMock(return_value=mock_response),
            )), patch("app.services.async_tracking_service._get_cached_serp", return_value=None):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "success test unique 009"}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2356,
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
                        "data": {"keyword": "success test unique 009", "location_code": 2356},
                        "result": [
                            {
                                "items": [
                                    {"type": "organic", "rank_group": 15, "url": "https://example.com/page", "domain": "example.com"},
                                ]
                            }
                        ]
                    }
                ]
            }

            import app.api.routes.webhooks as webhooks_mod
            original_sessionlocal = webhooks_mod.SessionLocal
            webhooks_mod.SessionLocal = lambda: db
            try:
                request = _make_webhook_request(webhook_payload)

                import asyncio
                _run_async(dataforseo_webhook(request))
            finally:
                webhooks_mod.SessionLocal = original_sessionlocal

            pending_jobs = db.scalars(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh_job_id)).all()
            for pending_job in pending_jobs:
                process_processing_job(db, pending_job)

            job = db.scalar(select(ProcessingJob).where(ProcessingJob.refreshJobId == refresh_job_id))
            assert job is not None
            assert job.status == "success"

            rank_results = db.scalars(select(RankResult).where(RankResult.keywordText == "success test unique 009")).all()
            assert len(rank_results) == 1
            assert rank_results[0].position == 15
        finally:
            db.close()


class TestPendingRefreshJobRequestIdentity:
    """Regression tests for pending RefreshJob reuse."""

    def test_different_keyword_does_not_reuse_pending_add_job(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)

        keyword_a = "pending identity keyword a"
        keyword_b = "pending identity keyword b"

        _build_keyword(db, project.id, keyword_a)
        _build_keyword(db, project.id, keyword_b)

        try:
            # First DFS submission creates an in-flight RefreshJob for A.
            response_a = _mock_task_post_response([
                {"keyword": keyword_a}
            ])

            with patch(
                "app.services.dataforseo_client.requests.post",
                return_value=MagicMock(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    json=MagicMock(return_value=response_a),
                ),
            ), patch(
                "app.services.async_tracking_service._get_cached_serp",
                return_value=None,
            ):
                result_a = submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": keyword_a}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2356,
                    depth=100,
                    cost_per_keyword=20,
                )

            # A different keyword must cause another DFS submission/job.
            response_b = _mock_task_post_response([
                {"keyword": keyword_b}
            ])

            with patch(
                "app.services.dataforseo_client.requests.post",
                return_value=MagicMock(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    json=MagicMock(return_value=response_b),
                ),
            ) as post_b, patch(
                "app.services.async_tracking_service._get_cached_serp",
                return_value=None,
            ):
                result_b = submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": keyword_b}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2356,
                    depth=100,
                    cost_per_keyword=20,
                )

            assert result_a["refresh_job_id"] != result_b["refresh_job_id"]

            refresh_jobs = db.scalars(
                select(RefreshJob)
                .where(RefreshJob.jobType == "add_keyword")
                .order_by(RefreshJob.createdAt)
            ).all()

            assert len(refresh_jobs) == 2

            payloads = [
                json.loads(job.keywordsJson or "[]")
                for job in refresh_jobs
            ]

            assert any(
                payload and payload[0].get("keyword") == keyword_a
                for payload in payloads
            )
            assert any(
                payload and payload[0].get("keyword") == keyword_b
                for payload in payloads
            )

        finally:
            db.close()


class TestSubmissionFailureSafety:
    def test_total_submission_failure_is_not_accepted(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        _build_keyword(db, project.id, "total submit failure")
        try:
            with patch("app.services.async_tracking_service._get_cached_serp", return_value=None), patch(
                "app.services.async_tracking_service._enrich_keyword_metrics",
                return_value={"requested": 1, "updated": 0, "missing": 1},
            ), patch(
                "app.services.async_tracking_service.DataForSEOClient.submit_serp_task_post",
                return_value={"task_ids": [], "submitted": [], "failed_chunks": 1},
            ):
                result = submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "total submit failure"}],
                    domain=project.domain,
                    action="add_keyword",
                    cost_per_keyword=20,
                )

            ledger = db.scalar(select(CreditLedger).where(CreditLedger.userId == user.id))
            assert result["accepted"] is False
            assert result["failed_keywords"] == ["total submit failure"]
            assert ledger.creditsRefunded == 20.0
            assert db.scalars(select(ProcessingJob)).all() == []
        finally:
            db.close()

    def test_single_add_removes_keyword_when_tracking_is_not_accepted(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        route = create_keyword
        while hasattr(route, "__wrapped__"):
            route = route.__wrapped__
        try:
            with patch(
                "app.api.routes.keywords.submit_user_tracking_job",
                return_value={
                    "refresh_job_id": "failed-refresh",
                    "accepted": False,
                    "accepted_keywords": [],
                    "failed_keywords": ["route failure"],
                },
            ):
                with pytest.raises(ApiError) as exc_info:
                    route(
                        request=MagicMock(),
                        project_id=project.id,
                        payload={"keyword": "route failure"},
                        user={"userId": user.id},
                        db=db,
                    )

            assert exc_info.value.status_code == 502
            assert db.scalar(select(Keyword).where(Keyword.keyword == "route failure")) is None
        finally:
            db.close()

    def test_bulk_add_keeps_only_keywords_with_valid_tracking(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        route = bulk_create_keywords
        while hasattr(route, "__wrapped__"):
            route = route.__wrapped__
        try:
            with patch(
                "app.api.routes.keywords.submit_user_tracking_job",
                return_value={
                    "refresh_job_id": "partial-refresh",
                    "accepted": True,
                    "accepted_keywords": ["kept keyword"],
                    "failed_keywords": ["removed keyword"],
                },
            ):
                result = route(
                    request=MagicMock(),
                    project_id=project.id,
                    payload={"keywords": ["kept keyword", "removed keyword"]},
                    user={"userId": user.id},
                    db=db,
                )

            rows = db.scalars(select(Keyword).where(Keyword.projectId == project.id)).all()
            assert [row.keyword for row in rows] == ["kept keyword"]
            assert result["data"]["processed"] == 1
            assert result["data"]["failed_tracking"] == 1
            assert result["data"]["keywords"] == ["kept keyword"]
        finally:
            db.close()

    def test_partial_submission_only_tracks_submitted_keywords_and_refunds_rest(self):
        db = _build_db()
        user = _build_user(db)
        user.planCreditBalance = 3000.0
        user.creditBalance = 3000.0
        project = _build_project(db, user.id)
        keyword_texts = [f"partial keyword {index}" for index in range(101)]
        db.add_all([
            Keyword(projectId=project.id, userId=user.id, keyword=text, location="India", device="desktop", isActive=True)
            for text in keyword_texts
        ])
        db.commit()
        submitted = keyword_texts[:100]
        try:
            with patch("app.services.async_tracking_service._get_cached_serp", return_value=None), patch(
                "app.services.async_tracking_service._enrich_keyword_metrics",
                return_value={"requested": 101, "updated": 0, "missing": 101},
            ), patch(
                "app.services.async_tracking_service.DataForSEOClient.submit_serp_task_post",
                return_value={"task_ids": [f"task-{index}" for index in range(100)], "submitted": submitted, "failed_chunks": 1},
            ):
                result = submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": text} for text in keyword_texts],
                    domain=project.domain,
                    action="bulk_add",
                    cost_per_keyword=20,
                )

            jobs = db.scalars(select(ProcessingJob)).all()
            ledger = db.scalar(select(CreditLedger).where(CreditLedger.userId == user.id))
            assert result["accepted_keywords"] == submitted
            assert result["failed_keywords"] == [keyword_texts[-1]]
            assert len(jobs) == 100
            assert {job.keywordText for job in jobs} == set(submitted)
            assert ledger.creditsRefunded == 20.0
        finally:
            db.close()


class TestWorkerReadiness:
    def test_awaiting_callback_filter_is_json_format_independent(self):
        db = _build_db()
        refresh = RefreshJob(jobType="add_keyword", status="submitted")
        db.add(refresh)
        db.flush()
        jobs = [
            ProcessingJob(
                refreshJobId=refresh.id,
                keywordText="normal waiting",
                location="India",
                status="pending",
                deduplicationKey="normal-waiting",
                payload=json.dumps({"awaiting_callback": True}),
            ),
            ProcessingJob(
                refreshJobId=refresh.id,
                keywordText="compact waiting",
                location="India",
                status="pending",
                deduplicationKey="compact-waiting",
                payload=json.dumps({"awaiting_callback": True}, separators=(",", ":")),
            ),
            ProcessingJob(
                refreshJobId=refresh.id,
                keywordText="compact ready",
                location="India",
                status="pending",
                deduplicationKey="compact-ready",
                payload=json.dumps({"awaiting_callback": False}, separators=(",", ":")),
            ),
            ProcessingJob(
                refreshJobId=refresh.id,
                keywordText="absent ready",
                location="India",
                status="pending",
                deduplicationKey="absent-ready",
                payload=json.dumps({"task_id": "ready"}),
            ),
        ]
        db.add_all(jobs)
        db.commit()

        claimed = claim_processing_jobs(db, batch_size=10)

        assert {job.keywordText for job in claimed} == {
            "compact ready",
            "absent ready",
        }
        waiting = db.scalars(
            select(ProcessingJob).where(ProcessingJob.status == "pending")
        ).all()
        assert {job.keywordText for job in waiting} == {
            "normal waiting",
            "compact waiting",
        }
        db.close()

    def test_worker_does_not_claim_job_before_callback_payload_arrives(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        _build_keyword(db, project.id, "awaiting callback")
        try:
            with patch("app.services.async_tracking_service._get_cached_serp", return_value=None), patch(
                "app.services.async_tracking_service._enrich_keyword_metrics",
                return_value={"requested": 1, "updated": 0, "missing": 1},
            ), patch(
                "app.services.async_tracking_service.DataForSEOClient.submit_serp_task_post",
                return_value={"task_ids": ["task-awaiting"], "submitted": ["awaiting callback"], "failed_chunks": 0},
            ):
                submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": "awaiting callback"}],
                    domain=project.domain,
                    action="add_keyword",
                    cost_per_keyword=20,
                )

            result = process_pending_processing_jobs(db)
            job = db.scalar(select(ProcessingJob))
            assert result["processed"] == 0
            assert result["failed"] == 0
            assert job.status == "pending"
        finally:
            db.close()

    def test_stale_missed_callback_is_failed_and_refunded(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        keyword = _build_keyword(db, project.id, "missed callback")
        keyword.processingTimeoutAt = datetime.utcnow() - timedelta(minutes=1)
        reference = f"add_keyword:{user.id}:{project.id}:stale"
        reserve_credits(db, user.id, 20.0, "reservation", "Add keyword reservation", reference=reference, project_id=project.id)
        refresh = RefreshJob(
            jobType="add_keyword",
            status="submitted",
            keywordCount=1,
            keywordsJson=json.dumps([{"keyword": keyword.keyword}]),
            dataforseoRequestIds=json.dumps(["task-never-callback"]),
            resultSummary=json.dumps({
                "project_id": project.id,
                "user_id": user.id,
                "credit_reference": reference,
                "cost_per_keyword": 20,
            }),
            processingTimeoutAt=datetime.utcnow() - timedelta(minutes=1),
        )
        db.add(refresh)
        db.flush()
        processing = ProcessingJob(
            refreshJobId=refresh.id,
            keywordText=keyword.keyword,
            location="India",
            status="pending",
            deduplicationKey="pending:missed-callback",
            payload=json.dumps({
                "project_id": project.id,
                "user_id": user.id,
                "action": "add_keyword",
                "credit_reference": reference,
                "cost_per_keyword": 20,
                "awaiting_callback": True,
            }),
        )
        db.add(processing)
        db.commit()

        result = recover_stale_user_tracking_jobs(db)
        db.refresh(refresh)
        db.refresh(processing)
        db.refresh(keyword)
        ledger = db.scalar(select(CreditLedger).where(CreditLedger.userId == user.id))

        assert result == {"jobs": 1, "callbacks_timed_out": 1, "refunded": 20.0}
        assert refresh.status == "failed"
        assert processing.status == "failed"
        assert keyword.processingTimeoutAt is None
        assert ledger.creditsRefunded == 20.0
        db.close()


class TestWebhookTaskCorrelation:
    def test_task_id_match_is_exact_not_json_substring(self):
        db = _build_db()
        longer = RefreshJob(
            jobType="add_keyword",
            status="submitted",
            dataforseoRequestIds=json.dumps(["task-123"]),
        )
        exact = RefreshJob(
            jobType="add_keyword",
            status="submitted",
            dataforseoRequestIds=json.dumps(["task-12"]),
        )
        db.add_all([longer, exact])
        db.commit()

        found = _find_refresh_job_by_task_id(db, "task-12")

        assert found.id == exact.id
        db.close()


class TestProcessingStatusScaleAndIsolation:
    def test_processing_query_rejects_crossed_keyword_location_pair(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        db.add_all([
            Keyword(projectId=project.id, userId=user.id, keyword="alpha", location="India", device="desktop", isActive=True),
            Keyword(projectId=project.id, userId=user.id, keyword="beta", location="United States", device="desktop", isActive=True),
        ])
        refresh = RefreshJob(jobType="bulk_add", status="submitted")
        db.add(refresh)
        db.flush()
        db.add(ProcessingJob(
            refreshJobId=refresh.id,
            keywordText="alpha",
            location="United States",
            status="pending",
            deduplicationKey="crossed-pair",
            payload=json.dumps({"project_id": project.id, "user_id": user.id, "action": "bulk_add"}),
        ))
        db.commit()

        with patch(
            "app.services.async_tracking_service.json.loads",
            wraps=json.loads,
        ) as parse_payload:
            jobs = get_user_processing_jobs(db, user.id, project.id)

        assert jobs == []
        parse_payload.assert_not_called()
        db.close()

    def test_processing_jobs_are_project_isolated_without_n_plus_one_queries(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)
        other_project = Project(id="other-project", userId=user.id, name="Other", domain="other.com", location="India", locationCode=2840)
        db.add(other_project)
        db.commit()

        own_keywords = [f"status keyword {index}" for index in range(30)]
        for text in own_keywords:
            db.add(Keyword(projectId=project.id, userId=user.id, keyword=text, location="India", device="desktop", isActive=True))
        db.add(Keyword(projectId=other_project.id, userId=user.id, keyword=own_keywords[0], location="India", device="desktop", isActive=True))

        own_refresh = RefreshJob(jobType="bulk_add", status="submitted", keywordsJson="[]", resultSummary=json.dumps({"project_id": project.id, "user_id": user.id}))
        other_refresh = RefreshJob(jobType="bulk_add", status="submitted", keywordsJson="[]", resultSummary=json.dumps({"project_id": other_project.id, "user_id": user.id}))
        db.add_all([own_refresh, other_refresh])
        db.flush()
        db.add_all([
            ProcessingJob(
                refreshJobId=own_refresh.id,
                keywordText=text,
                location="India",
                status="pending",
                deduplicationKey=f"own:{index}",
                payload=json.dumps({"project_id": project.id, "user_id": user.id, "action": "bulk_add"}),
            )
            for index, text in enumerate(own_keywords)
        ])
        db.add(ProcessingJob(
            refreshJobId=other_refresh.id,
            keywordText=own_keywords[0],
            location="India",
            status="pending",
            deduplicationKey="other:0",
            payload=json.dumps({"project_id": other_project.id, "user_id": user.id, "action": "bulk_add"}),
        ))
        db.commit()

        query_count = 0
        def count_query(*_args, **_kwargs):
            nonlocal query_count
            query_count += 1

        event.listen(db.bind, "before_cursor_execute", count_query)
        try:
            jobs = get_user_processing_jobs(db, user.id, project.id)
        finally:
            event.remove(db.bind, "before_cursor_execute", count_query)

        assert len(jobs) == 30
        assert {job["keyword"] for job in jobs} == set(own_keywords)
        assert query_count <= 4
        db.close()

class TestPendingRefreshJobIdenticalReuse:
    def test_identical_keyword_reuses_pending_add_job_without_second_dfs_post(self):
        db = _build_db()
        user = _build_user(db)
        project = _build_project(db, user.id)

        keyword = "pending identity same keyword"

        _build_keyword(db, project.id, keyword)

        try:
            response = _mock_task_post_response([
                {"keyword": keyword}
            ])

            with patch(
                "app.services.dataforseo_client.requests.post",
                return_value=MagicMock(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    json=MagicMock(return_value=response),
                ),
            ), patch(
                "app.services.async_tracking_service._get_cached_serp",
                return_value=None,
            ):
                first = submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": keyword}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2356,
                    depth=100,
                    cost_per_keyword=20,
                )

            # Calling the exact same request while the first is still
            # submitted must reuse it and must not POST to DFS again.
            with patch(
                "app.services.dataforseo_client.requests.post"
            ) as second_post, patch(
                "app.services.async_tracking_service._get_cached_serp",
                return_value=None,
            ):
                second = submit_user_tracking_job(
                    db=db,
                    user_id=user.id,
                    project_id=project.id,
                    keywords=[{"keyword": keyword}],
                    domain=project.domain,
                    action="add_keyword",
                    location_code=2356,
                    depth=100,
                    cost_per_keyword=20,
                )

            assert second["refresh_job_id"] == first["refresh_job_id"]
            assert second["task_ids"] == first["task_ids"]
            second_post.assert_not_called()

            refresh_jobs = db.scalars(
                select(RefreshJob).where(
                    RefreshJob.jobType == "add_keyword"
                )
            ).all()

            assert len(refresh_jobs) == 1

        finally:
            db.close()
