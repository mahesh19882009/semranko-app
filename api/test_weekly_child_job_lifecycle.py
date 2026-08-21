"""C4 regressions for scheduled weekly ProcessingJob lifecycle."""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.db.models import (  # noqa: E402
    Base,
    CreditLedger,
    Keyword,
    ProcessingJob,
    Project,
    RankResult,
    RefreshJob,
    TrackedKeyword,
    User,
)
from app.services.async_bulk_service import (  # noqa: E402
    REFRESH_JOB_BATCH_SIZE,
    _paginate_eligible_keywords,
    _submit_weekly_refresh,
    recover_stale_weekly_jobs,
)
from app.services.dataforseo_client import get_serp_priority  # noqa: E402
from app.services.serp_result_ingestion import ingest_dataforseo_task_result  # noqa: E402
from app.workers.refresh_worker import process_processing_job  # noqa: E402


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _user(db: Session, user_id: str, automatic_credits: float = 100.0) -> User:
    now = datetime.utcnow()
    row = User(
        id=user_id,
        name=user_id,
        email=f"{user_id}@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        automaticCreditBalance=automatic_credits,
        creditBalance=0.0,
        planCreditBalance=0.0,
        trialStartsAt=now,
        trialEndsAt=now + timedelta(days=7),
        createdAt=now,
        updatedAt=now,
    )
    db.add(row)
    db.flush()
    return row


def _project_keyword(
    db: Session,
    user: User,
    *,
    project_id: str,
    keyword_id: str,
    keyword: str,
    domain: str,
) -> tuple[Project, Keyword]:
    project = Project(
        id=project_id,
        userId=user.id,
        name=project_id,
        domain=domain,
    )
    keyword_row = Keyword(
        id=keyword_id,
        projectId=project_id,
        userId=user.id,
        keyword=keyword,
        location="India",
        device="desktop",
        isActive=True,
    )
    db.add_all([project, keyword_row])
    db.flush()
    return project, keyword_row


def _refresh(db: Session, keyword_texts: list[str], job_id: str = "weekly-job") -> RefreshJob:
    row = RefreshJob(
        id=job_id,
        jobType="weekly_serp",
        status="processing",
        batchIndex=0,
        totalBatches=1,
        keywordCount=len(keyword_texts),
        keywordsJson=json.dumps([
            {"keyword": keyword, "location": "India"}
            for keyword in keyword_texts
        ]),
    )
    db.add(row)
    db.commit()
    return row


def _provider_response(*accepted: tuple[str, str]):
    return type("Response", (), {
        "headers": {"Content-Type": "application/json"},
        "json": lambda self: {
            "tasks": [
                {"id": task_id, "data": {"keyword": keyword}}
                for task_id, keyword in accepted
            ]
        },
    })()


def _submit(db: Session, job: RefreshJob, keywords: list[str], response) -> bool:
    with patch(
        "app.services.dataforseo_client._get_cached_serp",
        return_value=None,
    ), patch(
        "app.services.async_bulk_service.check_dfs_cost_ceiling",
        create=True,
    ), patch(
        "app.services.async_bulk_service.requests.post",
        return_value=response,
    ), patch(
        "app.services.async_bulk_service._log_dataforseo_cost",
        create=True,
    ):
        return _submit_weekly_refresh(db, job, keywords)


def test_weekly_accepted_task_creates_callback_consumable_child_and_persists_result():
    db = _db()
    try:
        user = _user(db, "owner")
        project, keyword = _project_keyword(
            db,
            user,
            project_id="project-one",
            keyword_id="keyword-one",
            keyword="weekly keyword",
            domain="owner.example",
        )
        refresh = _refresh(db, [keyword.keyword])

        assert _submit(
            db,
            refresh,
            [keyword.keyword],
            _provider_response(("fake-task-one", keyword.keyword)),
        ) is True

        child = db.scalar(select(ProcessingJob))
        assert child is not None
        child_payload = json.loads(child.payload)
        assert child.refreshJobId == refresh.id
        assert child.keywordText == keyword.keyword
        assert child.location == "India"
        assert child.status == "pending"
        assert child_payload["awaiting_callback"] is True
        assert child_payload["task_ids"] == ["fake-task-one"]
        assert child_payload["project_id"] == project.id
        assert child_payload["user_id"] == user.id
        assert child_payload["domain"] == project.domain

        result = ingest_dataforseo_task_result(
            db,
            "fake-task-one",
            [{
                "id": "fake-task-one",
                "data": {"keyword": keyword.keyword, "location_code": 2840},
                "result": [{
                    "items": [{
                        "type": "organic",
                        "domain": "owner.example",
                        "url": "https://owner.example/ranking",
                        "rank_group": 4,
                    }],
                }],
            }],
            enqueue=False,
        )
        assert result["updated"] == 1
        db.refresh(child)
        assert json.loads(child.payload)["awaiting_callback"] is False

        assert process_processing_job(db, child) is True
        db.refresh(keyword)
        assert keyword.position == 4
        assert keyword.check_url == "https://owner.example/ranking"
        rank_results = db.scalars(select(RankResult)).all()
        assert len(rank_results) == 1
        assert rank_results[0].projectId == project.id
        ledger = db.scalar(select(CreditLedger).where(CreditLedger.userId == user.id))
        assert ledger.creditsConsumed == 10.0
    finally:
        db.close()


def test_shared_keyword_creates_isolated_project_and_user_children():
    db = _db()
    try:
        first_user = _user(db, "first-owner")
        second_user = _user(db, "second-owner")
        expected = []
        for user, project_id, keyword_id, domain in (
            (first_user, "first-project", "first-keyword", "first.example"),
            (first_user, "second-project", "second-keyword", "second.example"),
            (second_user, "third-project", "third-keyword", "third.example"),
        ):
            project, keyword = _project_keyword(
                db,
                user,
                project_id=project_id,
                keyword_id=keyword_id,
                keyword="shared keyword",
                domain=domain,
            )
            expected.append((project, keyword, user))
        refresh = _refresh(db, ["shared keyword"], "shared-weekly-job")

        assert _submit(
            db,
            refresh,
            ["shared keyword"],
            _provider_response(("fake-shared-task", "SHARED KEYWORD")),
        ) is True

        children = db.scalars(
            select(ProcessingJob).order_by(ProcessingJob.keywordText, ProcessingJob.id)
        ).all()
        assert len(children) == 3
        payloads = [json.loads(child.payload) for child in children]
        actual = {
            (
                payload["project_id"],
                payload["keyword_id"],
                payload["user_id"],
                payload["domain"],
            )
            for payload in payloads
        }
        assert actual == {
            (project.id, keyword.id, user.id, project.domain)
            for project, keyword, user in expected
        }
        assert all(payload["task_ids"] == ["fake-shared-task"] for payload in payloads)
        assert len({child.deduplicationKey for child in children}) == 3

        ingestion = ingest_dataforseo_task_result(
            db,
            "fake-shared-task",
            [{
                "data": {"keyword": "shared keyword", "location_code": 2840},
                "result": [{
                    "items": [
                        {"type": "organic", "domain": "first.example", "rank_group": 1},
                        {"type": "organic", "domain": "second.example", "rank_group": 2},
                        {"type": "organic", "domain": "third.example", "rank_group": 3},
                    ],
                }],
            }],
            enqueue=False,
        )
        assert ingestion["updated"] == 3
        positions_by_project = {
            json.loads(child.payload)["project_id"]: json.loads(child.payload)["position"]
            for child in children
        }
        assert positions_by_project == {
            "first-project": 1,
            "second-project": 2,
            "third-project": 3,
        }
    finally:
        db.close()


def test_partial_acceptance_creates_only_accepted_child_and_refunds_rejected_work():
    db = _db()
    try:
        user = _user(db, "partial-owner")
        project, accepted = _project_keyword(
            db,
            user,
            project_id="partial-project",
            keyword_id="accepted-keyword",
            keyword="accepted weekly",
            domain="partial.example",
        )
        rejected = Keyword(
            id="rejected-keyword",
            projectId=project.id,
            userId=user.id,
            keyword="rejected weekly",
            location="India",
            device="desktop",
            isActive=True,
        )
        db.add(rejected)
        db.flush()
        refresh = _refresh(db, [accepted.keyword, rejected.keyword], "partial-job")

        assert _submit(
            db,
            refresh,
            [accepted.keyword, rejected.keyword],
            _provider_response(("fake-accepted-task", accepted.keyword)),
        ) is True

        children = db.scalars(select(ProcessingJob)).all()
        assert [child.keywordText for child in children] == [accepted.keyword]
        reservation = db.scalar(select(CreditLedger).where(
            CreditLedger.userId == user.id,
            CreditLedger.creditPool == "automatic",
        ))
        assert reservation.creditsReserved == 20.0
        assert reservation.creditsRefunded == 10.0
        db.refresh(user)
        assert user.automaticCreditBalance == 90.0
    finally:
        db.close()


def test_provider_rejection_creates_no_orphan_and_refunds_reservation():
    db = _db()
    try:
        user = _user(db, "rejected-owner")
        _, keyword = _project_keyword(
            db,
            user,
            project_id="rejected-project",
            keyword_id="only-rejected-keyword",
            keyword="provider rejected",
            domain="rejected.example",
        )
        refresh = _refresh(db, [keyword.keyword], "rejected-job")

        assert _submit(
            db,
            refresh,
            [keyword.keyword],
            _provider_response(),
        ) is False

        assert db.scalars(select(ProcessingJob)).all() == []
        db.refresh(refresh)
        db.refresh(user)
        assert refresh.status == "failed"
        assert user.automaticCreditBalance == 100.0
        reservation = db.scalar(select(CreditLedger).where(
            CreditLedger.userId == user.id,
            CreditLedger.creditPool == "automatic",
        ))
        assert reservation.status == "refunded"
        assert reservation.creditsRefunded == 10.0
    finally:
        db.close()


def test_duplicate_callback_does_not_duplicate_rank_result_or_charge():
    db = _db()
    try:
        user = _user(db, "duplicate-owner")
        _, keyword = _project_keyword(
            db,
            user,
            project_id="duplicate-project",
            keyword_id="duplicate-keyword",
            keyword="duplicate callback",
            domain="duplicate.example",
        )
        refresh = _refresh(db, [keyword.keyword], "duplicate-job")
        assert _submit(
            db,
            refresh,
            [keyword.keyword],
            _provider_response(("fake-duplicate-task", keyword.keyword)),
        ) is True
        tasks = [{
            "data": {"keyword": keyword.keyword, "location_code": 2840},
            "result": [{
                "items": [{
                    "type": "organic",
                    "domain": "duplicate.example",
                    "rank_group": 8,
                }],
            }],
        }]

        first = ingest_dataforseo_task_result(
            db, "fake-duplicate-task", tasks, enqueue=False
        )
        duplicate_before_worker = ingest_dataforseo_task_result(
            db, "fake-duplicate-task", tasks, enqueue=False
        )
        child = db.scalar(select(ProcessingJob))
        assert first["updated"] == 1
        assert duplicate_before_worker["updated"] == 1
        assert len(db.scalars(select(ProcessingJob)).all()) == 1
        assert process_processing_job(db, child) is True
        duplicate_after_worker = ingest_dataforseo_task_result(
            db, "fake-duplicate-task", tasks, enqueue=False
        )
        assert duplicate_after_worker["updated"] == 0
        assert process_processing_job(db, child) is True

        assert len(db.scalars(select(RankResult)).all()) == 1
        reservation = db.scalar(select(CreditLedger).where(
            CreditLedger.userId == user.id,
            CreditLedger.creditPool == "automatic",
        ))
        assert reservation.creditsConsumed == 10.0
    finally:
        db.close()


def test_weekly_recovery_keeps_waiting_child_callback_consumable():
    db = _db()
    try:
        user = _user(db, "recovery-owner")
        _, keyword = _project_keyword(
            db,
            user,
            project_id="recovery-project",
            keyword_id="recovery-keyword",
            keyword="recovery weekly",
            domain="recovery.example",
        )
        refresh = _refresh(db, [keyword.keyword], "recovery-job")
        assert _submit(
            db,
            refresh,
            [keyword.keyword],
            _provider_response(("fake-recovery-task", keyword.keyword)),
        ) is True
        refresh.processingTimeoutAt = datetime.utcnow() - timedelta(minutes=1)
        db.add(refresh)
        db.commit()

        assert recover_stale_weekly_jobs(db) == {"recovered": 1}
        child = db.scalar(select(ProcessingJob))
        db.refresh(refresh)
        db.refresh(user)
        assert refresh.status == "retry"
        assert json.loads(child.payload)["awaiting_callback"] is True
        assert user.automaticCreditBalance == 90.0
        reservation = db.scalar(select(CreditLedger).where(
            CreditLedger.userId == user.id,
            CreditLedger.creditPool == "automatic",
        ))
        assert reservation.status == "pending"
        assert reservation.creditsRefunded == 0.0

        recovered = ingest_dataforseo_task_result(
            db,
            "fake-recovery-task",
            [{
                "data": {"keyword": keyword.keyword, "location_code": 2840},
                "result": [{"items": []}],
            }],
            enqueue=False,
        )
        assert recovered["updated"] == 1
        assert json.loads(child.payload)["awaiting_callback"] is False
    finally:
        db.close()


def test_child_metadata_and_frozen_weekly_request_contract_are_preserved():
    db = _db()
    try:
        user = _user(db, "aio-owner")
        project, keyword = _project_keyword(
            db,
            user,
            project_id="aio-project",
            keyword_id="aio-keyword",
            keyword="aio weekly",
            domain="aio.example",
        )
        db.add(TrackedKeyword(
            id="tracked-aio",
            userId=user.id,
            keyword=keyword.keyword,
            location="India",
            device="desktop",
            lockedUntil=datetime.utcnow() + timedelta(days=7),
            isActive=True,
            trackAio=True,
        ))
        db.commit()
        refresh = _refresh(db, [keyword.keyword], "aio-job")

        response = _provider_response(("fake-aio-task", keyword.keyword))
        with patch(
            "app.services.dataforseo_client._get_cached_serp",
            return_value=None,
        ), patch(
            "app.services.async_bulk_service.requests.post",
            return_value=response,
        ) as provider_post:
            assert _submit_weekly_refresh(db, refresh, [keyword.keyword]) is True

        provider_post.assert_called_once()
        call = provider_post.call_args
        assert call.args[0] == "https://api.dataforseo.com/v3/serp/google/organic/task_post"
        assert call.kwargs["json"] == [{
            "keyword": keyword.keyword,
            "location_code": 2840,
            "language_code": "en",
            "device": "desktop",
            "depth": 10,
            "pingback_url": call.kwargs["json"][0]["pingback_url"],
            "priority": get_serp_priority("weekly"),
            "expand_ai_overview": True,
        }]

        child = db.scalar(select(ProcessingJob))
        payload = json.loads(child.payload)
        assert payload == {
            "action": "weekly_serp",
            "credit_reference": f"auto:weekly:{refresh.id}:{user.id}",
            "cost_per_keyword": 10,
            "task_ids": ["fake-aio-task"],
            "location_code": 2840,
            "language_code": "en",
            "device": "desktop",
            "depth": 10,
            "domain": project.domain,
            "user_id": user.id,
            "project_id": project.id,
            "keyword_id": keyword.id,
            "expand_ai_overview": True,
            "awaiting_callback": True,
        }
        assert child.processingTimeoutAt == refresh.processingTimeoutAt
    finally:
        db.close()


def test_existing_5000_keyword_refresh_batch_limit_is_unchanged():
    assert REFRESH_JOB_BATCH_SIZE == 5000

    db = _db()
    try:
        user = _user(db, "batch-owner", automatic_credits=100000.0)
        project = Project(
            id="batch-project",
            userId=user.id,
            name="batch-project",
            domain="batch.example",
        )
        db.add(project)
        db.add_all([
            Keyword(
                id=f"batch-keyword-{index:04d}",
                projectId=project.id,
                userId=user.id,
                keyword=f"batch keyword {index:04d}",
                location="India",
                device="desktop",
                isActive=True,
            )
            for index in range(5001)
        ])
        db.commit()

        batches = _paginate_eligible_keywords(db, "weekly")
        assert [len(batch) for batch in batches] == [5000, 1]
    finally:
        db.close()
