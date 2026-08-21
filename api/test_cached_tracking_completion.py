"""Focused regressions for synchronous cached tracking completion."""

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

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
    _apply_cached_results,
    submit_user_tracking_job,
)
from app.services.credit_service import consume_reserved
from app.api.routes.keywords import bulk_create_keywords, create_keyword


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _user(db: Session) -> User:
    user = User(
        id="cached-user",
        name="Cached User",
        email="cached@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        creditBalance=200.0,
        planCreditBalance=200.0,
        purchasedCreditBalance=0.0,
        automaticCreditBalance=0.0,
    )
    db.add(user)
    db.commit()
    return user


def _project(db: Session, user: User) -> Project:
    project = Project(
        id="cached-project",
        userId=user.id,
        name="Cached Project",
        domain="example.com",
        location="India",
        locationCode=2840,
    )
    db.add(project)
    db.commit()
    return project


def _keyword(db: Session, project: Project, text: str) -> Keyword:
    keyword = Keyword(
        id=f"keyword-{text}",
        projectId=project.id,
        userId=project.userId,
        keyword=text,
        location="India",
        device="desktop",
        isActive=True,
    )
    db.add(keyword)
    db.commit()
    return keyword


def _cached_result(position: int = 3) -> dict:
    organic = {
        "type": "organic",
        "rank_group": position,
        "url": f"https://example.com/rank-{position}",
        "domain": "example.com",
    }
    return {"organic_items": [organic], "items": [organic]}


def _metrics_summary() -> dict:
    return {"requested": 1, "updated": 1, "missing": 0}


def _submit(db, user, project, keyword_texts):
    return submit_user_tracking_job(
        db=db,
        user_id=user.id,
        project_id=project.id,
        keywords=[{"keyword": keyword} for keyword in keyword_texts],
        domain=project.domain,
        action="bulk_add" if len(keyword_texts) > 1 else "add_keyword",
        location_code=2840,
        language_code="en",
        device="desktop",
        depth=100,
        cost_per_keyword=20,
    )


def test_single_fully_cached_completion_is_terminal_and_published_without_provider_call():
    db = _db()
    user = _user(db)
    project = _project(db, user)
    keyword = _keyword(db, project, "fully cached")

    try:
        with patch(
            "app.services.async_tracking_service._get_cached_serp",
            return_value=_cached_result(),
        ), patch(
            "app.services.async_tracking_service._enrich_keyword_metrics",
            return_value=_metrics_summary(),
        ), patch(
            "app.services.async_tracking_service.DataForSEOClient.submit_serp_task_post"
        ) as provider_post, patch(
            "app.services.async_tracking_service.publish_keyword_update"
        ) as publish:
            result = _submit(db, user, project, [keyword.keyword])

        provider_post.assert_not_called()
        publish.assert_called_once_with(
            user_id=user.id,
            project_id=project.id,
            keyword=keyword.keyword,
            status="success",
        )
        assert result["task_ids"] == []
        assert result["completed_keywords"] == [keyword.keyword]

        refresh = db.get(RefreshJob, result["refresh_job_id"])
        children = db.scalars(
            select(ProcessingJob).where(
                ProcessingJob.refreshJobId == refresh.id
            )
        ).all()
        db.refresh(keyword)

        assert refresh.status == "success"
        assert refresh.completedAt is not None
        assert len(children) == 1
        assert children[0].status == "success"
        assert json.loads(children[0].payload)["cached"] is True
        assert json.loads(children[0].payload).get("awaiting_callback") is not True
        assert keyword.processingTimeoutAt is None
        assert keyword.position == 3
    finally:
        db.close()


def test_mixed_cached_and_uncached_keywords_complete_independently():
    db = _db()
    user = _user(db)
    project = _project(db, user)
    cached_keyword = _keyword(db, project, "cached one")
    async_keyword = _keyword(db, project, "async one")

    try:
        with patch(
            "app.services.async_tracking_service._get_cached_serp",
            side_effect=[_cached_result(2), None],
        ), patch(
            "app.services.async_tracking_service._enrich_keyword_metrics",
            return_value={"requested": 2, "updated": 2, "missing": 0},
        ), patch(
            "app.services.async_tracking_service.DataForSEOClient.submit_serp_task_post",
            return_value={
                "task_ids": ["fake-task-1"],
                "submitted": [async_keyword.keyword],
                "failed_chunks": 0,
            },
        ) as provider_post, patch(
            "app.services.async_tracking_service.publish_keyword_update"
        ) as publish:
            result = _submit(
                db,
                user,
                project,
                [cached_keyword.keyword, async_keyword.keyword],
            )

        provider_post.assert_called_once()
        publish.assert_called_once_with(
            user_id=user.id,
            project_id=project.id,
            keyword=cached_keyword.keyword,
            status="success",
        )
        assert result["completed_keywords"] == [cached_keyword.keyword]

        refresh = db.get(RefreshJob, result["refresh_job_id"])
        children = db.scalars(
            select(ProcessingJob).where(
                ProcessingJob.refreshJobId == refresh.id
            )
        ).all()
        children_by_keyword = {child.keywordText: child for child in children}

        assert refresh.status == "submitted"
        assert children_by_keyword[cached_keyword.keyword].status == "success"
        assert children_by_keyword[async_keyword.keyword].status == "pending"
        assert json.loads(
            children_by_keyword[async_keyword.keyword].payload
        )["awaiting_callback"] is True
        assert db.scalar(
            select(func.count()).select_from(RankResult).where(
                RankResult.keywordId == cached_keyword.id
            )
        ) == 1
        assert db.scalar(
            select(func.count()).select_from(RankResult).where(
                RankResult.keywordId == async_keyword.id
            )
        ) == 0

        with patch(
            "app.services.async_tracking_service.DataForSEOClient.submit_serp_task_post"
        ) as duplicate_provider_post, patch(
            "app.services.async_tracking_service.publish_keyword_update"
        ) as duplicate_publish:
            duplicate_result = _submit(
                db,
                user,
                project,
                [cached_keyword.keyword, async_keyword.keyword],
            )

        duplicate_provider_post.assert_not_called()
        duplicate_publish.assert_not_called()
        assert duplicate_result["refresh_job_id"] == refresh.id
        assert duplicate_result["completed_keywords"] == [
            cached_keyword.keyword
        ]
        assert db.scalar(select(func.count()).select_from(RankResult)) == 1
        ledger = db.scalar(
            select(CreditLedger).where(CreditLedger.userId == user.id)
        )
        assert ledger.creditsConsumed == 20.0
        assert ledger.creditsRefunded == 0.0
    finally:
        db.close()


def test_multiple_cached_keywords_each_publish_completion():
    db = _db()
    user = _user(db)
    project = _project(db, user)
    first = _keyword(db, project, "cached first")
    second = _keyword(db, project, "cached second")

    try:
        with patch(
            "app.services.async_tracking_service._get_cached_serp",
            return_value=_cached_result(),
        ), patch(
            "app.services.async_tracking_service._enrich_keyword_metrics",
            return_value={"requested": 2, "updated": 2, "missing": 0},
        ), patch(
            "app.services.async_tracking_service.DataForSEOClient.submit_serp_task_post"
        ) as provider_post, patch(
            "app.services.async_tracking_service.publish_keyword_update"
        ) as publish:
            result = _submit(db, user, project, [first.keyword, second.keyword])

        provider_post.assert_not_called()
        assert result["completed_keywords"] == [first.keyword, second.keyword]
        assert [call.kwargs["keyword"] for call in publish.call_args_list] == [
            first.keyword,
            second.keyword,
        ]
        assert db.scalar(select(func.count()).select_from(RankResult)) == 2
    finally:
        db.close()


def test_metrics_cache_alone_does_not_complete_uncached_serp_early():
    db = _db()
    user = _user(db)
    project = _project(db, user)
    keyword = _keyword(db, project, "metrics only cached")

    try:
        with patch(
            "app.services.async_tracking_service._get_cached_serp",
            return_value=None,
        ), patch(
            "app.services.async_tracking_service._enrich_keyword_metrics",
            return_value=_metrics_summary(),
        ), patch(
            "app.services.async_tracking_service.DataForSEOClient.submit_serp_task_post",
            return_value={
                "task_ids": ["fake-task-2"],
                "submitted": [keyword.keyword],
                "failed_chunks": 0,
            },
        ), patch(
            "app.services.async_tracking_service.publish_keyword_update"
        ) as publish:
            result = _submit(db, user, project, [keyword.keyword])

        publish.assert_not_called()
        assert result["completed_keywords"] == []
        refresh = db.get(RefreshJob, result["refresh_job_id"])
        child = db.scalar(
            select(ProcessingJob).where(
                ProcessingJob.refreshJobId == refresh.id
            )
        )
        assert refresh.status == "submitted"
        assert child.status == "pending"
        assert json.loads(child.payload)["awaiting_callback"] is True
        assert db.scalar(select(func.count()).select_from(RankResult)) == 0
    finally:
        db.close()


def test_duplicate_cached_application_does_not_duplicate_result_or_credit():
    db = _db()
    user = _user(db)
    project = _project(db, user)
    keyword = _keyword(db, project, "idempotent cached")

    try:
        with patch(
            "app.services.async_tracking_service._get_cached_serp",
            return_value=_cached_result(),
        ), patch(
            "app.services.async_tracking_service._enrich_keyword_metrics",
            return_value=_metrics_summary(),
        ), patch(
            "app.services.async_tracking_service.DataForSEOClient.submit_serp_task_post"
        ), patch(
            "app.services.async_tracking_service.publish_keyword_update"
        ):
            result = _submit(db, user, project, [keyword.keyword])

        refresh = db.get(RefreshJob, result["refresh_job_id"])
        summary = json.loads(refresh.resultSummary)
        cached_results = {keyword.keyword: _cached_result()}

        _apply_cached_results(
            db,
            project.id,
            user.id,
            project.domain,
            cached_results,
            refresh.id,
        )
        consume_reserved(
            db,
            user.id,
            summary["credit_reference"],
            20.0,
            commit=False,
        )
        db.commit()

        ledger = db.scalar(
            select(CreditLedger).where(CreditLedger.userId == user.id)
        )
        assert db.scalar(select(func.count()).select_from(RankResult)) == 1
        assert db.scalar(select(func.count()).select_from(ProcessingJob)) == 1
        assert ledger.creditsConsumed == 20.0
        assert ledger.creditsRefunded == 0.0
    finally:
        db.close()


def test_single_and_bulk_routes_preserve_completed_keyword_metadata():
    db = _db()
    user = _user(db)
    project = _project(db, user)
    auth_user = {"userId": user.id}
    single_route = create_keyword
    bulk_route = bulk_create_keywords
    while hasattr(single_route, "__wrapped__"):
        single_route = single_route.__wrapped__
    while hasattr(bulk_route, "__wrapped__"):
        bulk_route = bulk_route.__wrapped__

    try:
        with patch(
            "app.api.routes.keywords.submit_user_tracking_job",
            return_value={
                "refresh_job_id": "cached-single-refresh",
                "accepted": True,
                "accepted_keywords": ["route cached single"],
                "completed_keywords": ["route cached single"],
                "failed_keywords": [],
            },
        ):
            response = single_route(
                request=MagicMock(),
                project_id=project.id,
                payload={"keyword": "route cached single"},
                user=auth_user,
                db=db,
            )

        single_data = json.loads(response.body)["data"]
        assert single_data["completed_keywords"] == ["route cached single"]

        with patch(
            "app.api.routes.keywords.submit_user_tracking_job",
            return_value={
                "refresh_job_id": "cached-bulk-refresh",
                "accepted": True,
                "accepted_keywords": ["route cached bulk", "route async bulk"],
                "completed_keywords": ["route cached bulk"],
                "failed_keywords": [],
            },
        ):
            result = bulk_route(
                request=MagicMock(),
                project_id=project.id,
                payload={
                    "keywords": ["route cached bulk", "route async bulk"]
                },
                user=auth_user,
                db=db,
            )

        assert result["data"]["completed_keywords"] == [
            "route cached bulk"
        ]
    finally:
        db.close()
