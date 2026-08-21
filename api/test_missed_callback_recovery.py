"""Regression tests for recovery of already-submitted SERP tasks."""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from fastapi import Request
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.routes.webhooks import dataforseo_webhook
from app.db.models import (
    Base,
    CreditLedger,
    Keyword,
    ProcessingJob,
    Project,
    RankResult,
    RefreshJob,
    User,
)
from app.services.async_tracking_service import (
    CALLBACK_RECOVERY_GRACE_MINUTES,
    CALLBACK_RECOVERY_RETRY_MINUTES,
    recover_missed_callback_results,
    recover_stale_user_tracking_jobs,
)
from app.services.credit_service import reserve_credits
from app.workers.refresh_worker import process_pending_processing_jobs


def _db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _request(payload: dict) -> Request:
    request = Request({
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json")],
        "query_string": b"",
    })
    request._body = json.dumps(payload).encode()
    return request


def _ready_response(task_id: str, keyword: str, position: int = 4) -> dict:
    return {
        "status_code": 20000,
        "tasks": [{
            "id": task_id,
            "status_code": 20000,
            "data": {"keyword": keyword, "location_code": 2356},
            "result": [{
                "items": [{
                    "type": "organic",
                    "rank_group": position,
                    "url": f"https://example.com/{keyword.replace(' ', '-')}",
                    "domain": "example.com",
                }],
            }],
        }],
    }


def _waiting_job(
    db: Session,
    pairs: list[tuple[str, str]],
    *,
    user_id: str = "recovery-user",
    project_id: str = "recovery-project",
    age_minutes: int | None = None,
) -> tuple[User, Project, RefreshJob, list[ProcessingJob]]:
    age_minutes = age_minutes or CALLBACK_RECOVERY_GRACE_MINUTES + 1
    user = User(
        id=user_id,
        name="Recovery User",
        email=f"{user_id}@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        creditBalance=1000.0,
        planCreditBalance=1000.0,
        purchasedCreditBalance=0.0,
        automaticCreditBalance=0.0,
    )
    project = Project(
        id=project_id,
        userId=user.id,
        name="Recovery Project",
        domain="example.com",
        location="India",
        locationCode=2356,
    )
    db.add_all([user, project])
    for _, keyword in pairs:
        db.add(Keyword(
            projectId=project.id,
            userId=user.id,
            keyword=keyword,
            location="India",
            device="desktop",
            isActive=True,
            processingTimeoutAt=datetime.utcnow() + timedelta(hours=23),
        ))
    db.commit()

    reference = f"add_keyword:{user.id}:{project.id}:recovery"
    reserve_credits(
        db,
        user.id,
        float(20 * len(pairs)),
        "reservation",
        "Recovery reservation",
        reference=reference,
        project_id=project.id,
    )
    refresh = RefreshJob(
        jobType="bulk_add" if len(pairs) > 1 else "add_keyword",
        status="submitted",
        keywordCount=len(pairs),
        keywordsJson=json.dumps([{"keyword": keyword} for _, keyword in pairs]),
        dataforseoRequestIds=json.dumps([task_id for task_id, _ in pairs]),
        resultSummary=json.dumps({
            "project_id": project.id,
            "user_id": user.id,
            "domain": project.domain,
            "credit_reference": reference,
            "cost_per_keyword": 20,
        }),
        processingTimeoutAt=datetime.utcnow() + timedelta(hours=23),
        createdAt=datetime.utcnow() - timedelta(minutes=age_minutes),
    )
    db.add(refresh)
    db.flush()

    children = []
    for task_id, keyword in pairs:
        child = ProcessingJob(
            refreshJobId=refresh.id,
            keywordText=keyword,
            location="India",
            status="pending",
            deduplicationKey=f"pending:{refresh.id}:{keyword}:2356",
            payload=json.dumps({
                "action": refresh.jobType,
                "credit_reference": reference,
                "cost_per_keyword": 20,
                "location_code": 2356,
                "language_code": "en",
                "device": "desktop",
                "depth": 100,
                "domain": project.domain,
                "user_id": user.id,
                "project_id": project.id,
                "awaiting_callback": True,
            }),
        )
        db.add(child)
        children.append(child)
    db.commit()
    return user, project, refresh, children


def _deliver_webhook(db: Session, payload: dict) -> dict:
    import app.api.routes.webhooks as webhooks_module

    original = webhooks_module.SessionLocal
    webhooks_module.SessionLocal = lambda: db
    try:
        with patch(
            "app.services.serp_result_ingestion.get_rank_check_queue",
            return_value=MagicMock(),
        ):
            return asyncio.run(dataforseo_webhook(_request(payload)))
    finally:
        webhooks_module.SessionLocal = original


class TestMissedCallbackRecovery:
    def test_normal_callback_remains_primary_and_task_get_is_not_called(self):
        db = _db()
        _, _, refresh, _ = _waiting_job(db, [("task-normal", "normal callback")])
        refresh_id = refresh.id
        payload = _ready_response("task-normal", "normal callback")

        result = _deliver_webhook(db, {"task_id": "task-normal", "tasks": payload["tasks"]})
        with patch(
            "app.services.async_tracking_service.DataForSEOClient._retrieve_task_result"
        ) as task_get:
            recovery = recover_missed_callback_results(db)

        refresh = db.get(RefreshJob, refresh_id)
        assert result["updated"] == 1
        assert recovery["retrieved"] == 0
        task_get.assert_not_called()
        assert "task-normal" in json.loads(refresh.resultSummary)["processed_task_ids"]
        db.close()

    def test_ready_task_get_reuses_paid_task_and_normal_worker_once(self):
        db = _db()
        user, _, _, children = _waiting_job(db, [("task-ready", "ready recovery")])
        response = _ready_response("task-ready", "ready recovery", position=7)

        with patch(
            "app.services.async_tracking_service.DataForSEOClient._retrieve_task_result",
            return_value=response,
        ) as task_get, patch(
            "app.services.async_tracking_service.DataForSEOClient.submit_serp_task_post"
        ) as task_post, patch(
            "app.services.serp_result_ingestion.get_rank_check_queue",
            return_value=MagicMock(),
        ), patch(
            "app.workers.refresh_worker._set_cached_serp"
        ), patch(
            "app.workers.refresh_worker.publish_keyword_update"
        ):
            recovered = recover_missed_callback_results(db)
            processed = process_pending_processing_jobs(db)

        db.refresh(children[0])
        ledger = db.scalar(select(CreditLedger).where(CreditLedger.userId == user.id))
        assert recovered["recovered"] == 1
        assert processed["processed"] == 1
        assert json.loads(children[0].payload)["awaiting_callback"] is False
        assert children[0].status == "success"
        assert db.scalar(select(Keyword).where(Keyword.keyword == "ready recovery")).position == 7
        assert len(db.scalars(select(RankResult)).all()) == 1
        assert ledger.creditsConsumed == 20.0
        task_get.assert_called_once_with("task-ready", result_type="regular")
        task_post.assert_not_called()
        db.close()

    def test_not_ready_is_throttled_and_remains_pending_without_refund(self):
        db = _db()
        user, _, _, children = _waiting_job(db, [("task-wait", "still waiting")])
        now = datetime.utcnow()
        not_ready = {
            "status_code": 20000,
            "tasks": [{"id": "task-wait", "status_code": 40601, "result": None}],
        }

        with patch(
            "app.services.async_tracking_service.DataForSEOClient._retrieve_task_result",
            return_value=not_ready,
        ) as task_get:
            first = recover_missed_callback_results(db, now=now)
            second = recover_missed_callback_results(db, now=now + timedelta(minutes=1))

        db.refresh(children[0])
        ledger = db.scalar(select(CreditLedger).where(CreditLedger.userId == user.id))
        assert first["not_ready"] == 1
        assert second["retrieved"] == 0
        assert children[0].status == "pending"
        assert json.loads(children[0].payload)["awaiting_callback"] is True
        assert ledger.creditsRefunded == 0.0
        task_get.assert_called_once()
        assert process_pending_processing_jobs(db)["processed"] == 0
        db.close()

    def test_provider_error_stays_eligible_for_later_recovery(self):
        db = _db()
        _, _, _, children = _waiting_job(db, [("task-error", "provider error")])
        now = datetime.utcnow()

        with patch(
            "app.services.async_tracking_service.DataForSEOClient._retrieve_task_result",
            side_effect=[None, _ready_response("task-error", "provider error")],
        ) as task_get, patch(
            "app.services.serp_result_ingestion.get_rank_check_queue",
            return_value=MagicMock(),
        ):
            failed = recover_missed_callback_results(db, now=now)
            recovered = recover_missed_callback_results(
                db,
                now=now + timedelta(minutes=CALLBACK_RECOVERY_RETRY_MINUTES + 1),
            )

        db.refresh(children[0])
        assert failed["errors"] == 1
        assert recovered["recovered"] == 1
        assert task_get.call_count == 2
        assert json.loads(children[0].payload)["awaiting_callback"] is False
        db.close()

    def test_recovery_then_delayed_webhook_is_idempotent(self):
        db = _db()
        user, _, _, _ = _waiting_job(db, [("task-late", "late callback")])
        user_id = user.id
        response = _ready_response("task-late", "late callback", position=9)

        with patch(
            "app.services.async_tracking_service.DataForSEOClient._retrieve_task_result",
            return_value=response,
        ) as task_get, patch(
            "app.services.serp_result_ingestion.get_rank_check_queue",
            return_value=MagicMock(),
        ), patch(
            "app.workers.refresh_worker._set_cached_serp"
        ), patch(
            "app.workers.refresh_worker.publish_keyword_update"
        ):
            recover_missed_callback_results(db)
            process_pending_processing_jobs(db)
            repeat = recover_missed_callback_results(db)
            delayed = _deliver_webhook(
                db,
                {"task_id": "task-late", "tasks": response["tasks"]},
            )

        ledger = db.scalar(select(CreditLedger).where(CreditLedger.userId == user_id))
        assert repeat["retrieved"] == 0
        assert delayed["updated"] == 0
        assert delayed["skipped"] == 1
        assert task_get.call_count == 1
        assert len(db.scalars(select(RankResult)).all()) == 1
        assert ledger.creditsConsumed == 20.0
        db.close()

    def test_bulk_recovery_only_retrieves_missing_task(self):
        db = _db()
        _, _, refresh, children = _waiting_job(
            db,
            [("task-done", "already done"), ("task-missing", "missing callback")],
        )
        refresh_id = refresh.id
        child_ids = [child.id for child in children]
        done_response = _ready_response("task-done", "already done")
        _deliver_webhook(
            db,
            {"task_id": "task-done", "tasks": done_response["tasks"]},
        )

        with patch(
            "app.services.async_tracking_service.DataForSEOClient._retrieve_task_result",
            return_value=_ready_response("task-missing", "missing callback"),
        ) as task_get, patch(
            "app.services.serp_result_ingestion.get_rank_check_queue",
            return_value=MagicMock(),
        ):
            result = recover_missed_callback_results(db)

        refresh = db.get(RefreshJob, refresh_id)
        children = [db.get(ProcessingJob, child_id) for child_id in child_ids]
        assert result["recovered"] == 1
        task_get.assert_called_once_with("task-missing", result_type="regular")
        assert all(json.loads(child.payload)["awaiting_callback"] is False for child in children)
        assert set(json.loads(refresh.resultSummary)["processed_task_ids"]) == {
            "task-done",
            "task-missing",
        }
        db.close()

    def test_task_result_cannot_update_another_project_job(self):
        db = _db()
        _, _, _, first_children = _waiting_job(
            db,
            [("task-owned", "shared keyword")],
            user_id="owner-a",
            project_id="project-a",
        )
        _, _, _, second_children = _waiting_job(
            db,
            [("task-other", "shared keyword")],
            user_id="owner-b",
            project_id="project-b",
        )

        with patch(
            "app.services.async_tracking_service.DataForSEOClient._retrieve_task_result",
            side_effect=lambda task_id, result_type="regular": (
                _ready_response(task_id, "shared keyword")
                if task_id == "task-owned"
                else {"status_code": 20000, "tasks": [{"id": task_id, "status_code": 40601, "result": None}]}
            ),
        ), patch(
            "app.services.serp_result_ingestion.get_rank_check_queue",
            return_value=MagicMock(),
        ):
            recover_missed_callback_results(db)

        db.refresh(first_children[0])
        db.refresh(second_children[0])
        assert json.loads(first_children[0].payload)["awaiting_callback"] is False
        assert json.loads(second_children[0].payload)["awaiting_callback"] is True
        db.close()

    def test_terminal_timeout_still_fails_and_refunds_unrecovered_task(self):
        db = _db()
        user, _, refresh, children = _waiting_job(db, [("task-terminal", "terminal")])
        refresh.processingTimeoutAt = datetime.utcnow() - timedelta(minutes=1)
        db.add(refresh)
        db.commit()

        result = recover_stale_user_tracking_jobs(db)

        db.refresh(children[0])
        ledger = db.scalar(select(CreditLedger).where(CreditLedger.userId == user.id))
        assert result["callbacks_timed_out"] == 1
        assert children[0].status == "failed"
        assert ledger.creditsRefunded == 20.0
        db.close()
