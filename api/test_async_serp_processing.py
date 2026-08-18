"""Focused async SERP result processing regression tests.

Tests domain matching, AIO matching, worker execution, cache metadata,
credit safety, and result semantics for the canonical postback -> worker path.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import asyncio

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

import pytest
from sqlalchemy import create_engine, select
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
from app.services.async_tracking_service import submit_user_tracking_job
from app.services.credit_service import reserve_credits, consume_reserved, refund_reserved
from app.workers.refresh_worker import run_refresh_worker, process_processing_job
from app.api.routes.webhooks import (
    dataforseo_webhook,
    _aio_cites_target_domain,
)
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
