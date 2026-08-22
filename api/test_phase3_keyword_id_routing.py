"""Phase 3 regressions for exact Keyword.id tracking correlation."""

import json
from pathlib import Path
import sys
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.db.models import Base, Keyword, ProcessingJob, Project, RankResult, RefreshJob, User
from app.services.async_tracking_service import _apply_cached_results, submit_user_tracking_job
from app.services.serp_result_ingestion import ingest_dataforseo_task_result
from app.workers.refresh_worker import process_processing_job


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _setup(db: Session):
    user = User(
        id="phase3-user", name="Phase 3", email="phase3@example.com", passwordHash="hash",
        selectedPlan="starter", subscriptionStatus="active", creditBalance=500,
        planCreditBalance=500, purchasedCreditBalance=0, automaticCreditBalance=0,
    )
    project = Project(
        id="phase3-project", userId=user.id, name="Phase 3", domain="example.com",
        location="India", locationCode=2840,
    )
    db.add_all([user, project])
    db.commit()
    return user, project


def _keyword(db: Session, user: User, project: Project, keyword_id: str, code: int, device: str = "desktop"):
    row = Keyword(
        id=keyword_id, projectId=project.id, userId=user.id, keyword="same query",
        location=f"Location {code}", locationCode=code, device=device, isActive=True,
    )
    db.add(row)
    db.commit()
    return row


def _task(task_id: str, keyword: str = "same query", code: int = 2840):
    return {
        "id": task_id,
        "status_code": 20000,
        "data": {"keyword": keyword, "location_code": code},
        "result": [{"items": [{"type": "organic", "rank_group": 4, "url": "https://example.com"}]}],
    }


def test_callback_task_id_updates_only_exact_child_target():
    db = _db()
    user, project = _setup(db)
    first = _keyword(db, user, project, "keyword-a", 2840)
    second = _keyword(db, user, project, "keyword-b", 2356)
    refresh = RefreshJob(
        id="refresh-phase3", jobType="add_keyword", status="submitted",
        keywordCount=2, dataforseoRequestIds=json.dumps(["task-a", "task-b"]),
        resultSummary=json.dumps({"project_id": project.id, "user_id": user.id}),
    )
    db.add(refresh)
    db.add_all([
        ProcessingJob(
            id="child-a", refreshJobId=refresh.id, keywordId=first.id,
            keywordText="same query", location="Location 2840", status="pending",
            deduplicationKey="child-a", payload=json.dumps({"task_ids": ["task-a"], "location_code": 2840}),
        ),
        ProcessingJob(
            id="child-b", refreshJobId=refresh.id, keywordId=second.id,
            keywordText="same query", location="Location 2356", status="pending",
            deduplicationKey="child-b", payload=json.dumps({"task_ids": ["task-b"], "location_code": 2356}),
        ),
    ])
    db.commit()

    with patch("app.services.serp_result_ingestion.get_rank_check_queue"):
        result = ingest_dataforseo_task_result(db, "task-a", [_task("task-a", code=2840)], enqueue=False)

    assert result["updated"] == 1
    db.refresh(first)
    db.refresh(second)
    child_a = db.get(ProcessingJob, "child-a")
    child_b = db.get(ProcessingJob, "child-b")
    assert child_a.keywordId == first.id and child_a.status == "pending"
    assert child_b.status == "pending" and child_b.keywordId == second.id
    db.close()


def test_cached_result_uses_requested_keyword_id_not_same_text_first_row():
    db = _db()
    user, project = _setup(db)
    first = _keyword(db, user, project, "keyword-a", 2840)
    second = _keyword(db, user, project, "keyword-b", 2356)
    refresh = RefreshJob(id="refresh-cache", jobType="add_keyword", status="queued", keywordCount=1)
    db.add(refresh)
    db.flush()
    cached = {"same query": {"organic_items": [{"type": "organic", "rank_group": 2, "domain": "example.com", "url": "https://example.com"}], "items": []}}
    completed = _apply_cached_results(
        db, project.id, user.id, project.domain, cached, refresh.id,
        keyword_targets=[{"keyword": "same query", "keyword_id": second.id, "location_code": 2356, "device": "desktop"}],
    )
    assert completed == ["same query"]
    assert db.scalar(select(RankResult).where(RankResult.keywordId == second.id)) is not None
    assert db.scalar(select(RankResult).where(RankResult.keywordId == first.id)) is None
    db.close()


def test_submission_persists_keyword_id_and_internal_task_correlation():
    db = _db()
    user, project = _setup(db)
    keyword = _keyword(db, user, project, "keyword-submit", 2840)
    with patch("app.services.async_tracking_service._get_cached_serp", return_value=None), \
         patch("app.services.async_tracking_service._enrich_keyword_metrics", return_value={"requested": 0, "updated": 0, "missing": 0}), \
         patch("app.services.async_tracking_service.DataForSEOClient.submit_serp_task_post", return_value={"task_ids": ["task-submit"], "submitted": ["same query"], "failed_chunks": 0}):
        result = submit_user_tracking_job(
            db, user.id, project.id,
            [{"keyword": "same query", "keyword_id": keyword.id, "location_code": 2840, "device": "desktop"}],
            project.domain, "manual_refresh", 2840, "en", "desktop", 100, 20,
        )
    child = db.scalar(select(ProcessingJob).where(ProcessingJob.refreshJobId == result["refresh_job_id"]))
    refresh = db.get(RefreshJob, result["refresh_job_id"])
    target = json.loads(refresh.keywordsJson)[0]
    assert target["keyword_id"] == keyword.id
    assert target["project_id"] == project.id and target["user_id"] == user.id
    assert target["location_code"] == 2840 and target["device"] == "desktop"
    assert child.keywordId == keyword.id
    assert json.loads(child.payload)["task_ids"] == ["task-submit"]
    db.close()


def test_same_text_targets_create_isolated_children_for_location_and_device():
    db = _db()
    user, project = _setup(db)
    india = _keyword(db, user, project, "keyword-india", 2840, "desktop")
    faridabad_mobile = _keyword(db, user, project, "keyword-faridabad-mobile", 2356, "mobile")
    with patch("app.services.async_tracking_service._get_cached_serp", return_value=None), \
         patch("app.services.async_tracking_service._enrich_keyword_metrics", return_value={"requested": 0, "updated": 0, "missing": 0}), \
         patch("app.services.async_tracking_service.DataForSEOClient.submit_serp_task_post", side_effect=[
             {"task_ids": ["task-india"], "submitted": ["same query"], "failed_chunks": 0},
             {"task_ids": ["task-mobile"], "submitted": ["same query"], "failed_chunks": 0},
         ]):
        first = submit_user_tracking_job(
            db, user.id, project.id,
            [{"keyword": "same query", "keyword_id": india.id, "location_code": 2840, "device": "desktop"}],
            project.domain, "manual_refresh", 2840, "en", "desktop", 100, 20,
        )
        second = submit_user_tracking_job(
            db, user.id, project.id,
            [{"keyword": "same query", "keyword_id": faridabad_mobile.id, "location_code": 2356, "device": "mobile"}],
            project.domain, "manual_refresh", 2356, "en", "mobile", 100, 20,
        )
    children = db.scalars(select(ProcessingJob)).all()
    assert {child.keywordId for child in children} == {india.id, faridabad_mobile.id}
    assert {json.loads(child.payload)["task_ids"][0] for child in children} == {"task-india", "task-mobile"}
    assert first["refresh_job_id"] != second["refresh_job_id"]
    db.close()


def test_worker_rejects_keyword_id_from_another_project():
    db = _db()
    user, project = _setup(db)
    other_project = Project(
        id="phase3-other-project", userId=user.id, name="Other", domain="other.example",
        location="India", locationCode=2840,
    )
    db.add(other_project)
    db.commit()
    foreign_keyword = _keyword(db, user, other_project, "keyword-foreign", 2840)
    refresh = RefreshJob(id="refresh-tenant", jobType="manual_refresh", status="submitted", keywordCount=1)
    child = ProcessingJob(
        id="tenant-child", refreshJobId=refresh.id, keywordId=foreign_keyword.id,
        keywordText=foreign_keyword.keyword, location=foreign_keyword.location, status="pending",
        deduplicationKey="tenant-child", payload=json.dumps({
            "keyword_id": foreign_keyword.id, "project_id": project.id, "user_id": user.id,
            "action": "manual_refresh", "credit_reference": "ref-tenant", "cost_per_keyword": 20,
        }),
    )
    db.add_all([refresh, child])
    db.commit()
    with patch("app.workers.refresh_worker.refund_reserved"):
        assert process_processing_job(db, child) is True
    assert db.scalar(select(RankResult).where(RankResult.keywordId == foreign_keyword.id)) is None
    assert db.get(ProcessingJob, child.id).status == "success"
    db.close()


def test_pending_refresh_reuse_requires_exact_keyword_id_target_set():
    db = _db()
    user, project = _setup(db)
    first = _keyword(db, user, project, "keyword-a", 2840)
    second = _keyword(db, user, project, "keyword-b", 2356)
    pending = RefreshJob(
        id="refresh-reuse", jobType="manual_refresh", status="submitted", keywordCount=1,
        keywordsJson=json.dumps([{"keyword": "same query", "keyword_id": first.id, "location_code": 2840, "device": "desktop"}]),
        dataforseoRequestIds=json.dumps(["task-a"]),
        resultSummary=json.dumps({"project_id": project.id, "user_id": user.id}),
    )
    db.add(pending)
    db.commit()

    with patch("app.services.async_tracking_service._get_cached_serp", return_value={}), \
         patch("app.services.async_tracking_service.DataForSEOClient.submit_serp_task_post", return_value={"task_ids": [], "submitted": [], "failed_chunks": 1}), \
         patch("app.services.async_tracking_service._enrich_keyword_metrics", return_value={"requested": 0, "updated": 0, "missing": 0}), \
         patch("app.services.dataforseo_client.check_dfs_cost_ceiling", return_value=None):
        result = submit_user_tracking_job(
            db, user.id, project.id,
            [{"keyword": "same query", "keyword_id": second.id, "location_code": 2356, "device": "desktop"}],
            project.domain, "manual_refresh", 2356, "en", "desktop", 100, 20,
        )
    assert result["refresh_job_id"] != pending.id
    db.close()


def test_worker_persists_rank_result_to_processing_job_keyword_id_only():
    db = _db()
    user, project = _setup(db)
    first = _keyword(db, user, project, "keyword-a", 2840)
    second = _keyword(db, user, project, "keyword-b", 2356)
    refresh = RefreshJob(id="refresh-worker", jobType="manual_refresh", status="submitted", keywordCount=1)
    child = ProcessingJob(
        id="worker-child", refreshJobId=refresh.id, keywordId=second.id,
        keywordText="same query", location="Location 2356", status="pending",
        deduplicationKey="worker-child", payload=json.dumps({
            "keyword_id": second.id, "project_id": project.id, "user_id": user.id,
            "action": "manual_refresh", "credit_reference": "ref-worker",
            "cost_per_keyword": 20, "location_code": 2356, "device": "desktop",
            "first_block": {"items": []}, "position": 7, "url": "https://example.com",
        }),
    )
    db.add_all([refresh, child])
    db.commit()

    with patch("app.workers.refresh_worker.consume_reserved"), \
         patch("app.workers.refresh_worker._log_dataforseo_cost"), \
         patch("app.workers.refresh_worker._set_cached_serp"), \
         patch("app.workers.refresh_worker.publish_keyword_update"):
        assert process_processing_job(db, child) is True

    assert db.scalar(select(RankResult).where(RankResult.keywordId == second.id)) is not None
    assert db.scalar(select(RankResult).where(RankResult.keywordId == first.id)) is None
    db.close()
