"""C5 regressions for canonical weekly callback URL construction."""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.api.routes.webhooks import dataforseo_webhook  # noqa: E402
from app.db.models import (  # noqa: E402
    AsyncTaskQueue,
    Base,
    Keyword,
    Project,
    RefreshJob,
    User,
)
from app.services.async_bulk_service import (  # noqa: E402
    _submit_weekly_refresh,
    submit_bulk_to_dataforseo,
)
from app.services.async_tracking_service import (  # noqa: E402
    _build_postback_url,
    settings,
)


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _weekly_rows(db: Session, *, prefix: str = "url"):
    now = datetime.utcnow()
    user = User(
        id=f"{prefix}-user",
        name="URL Owner",
        email=f"{prefix}@example.com",
        passwordHash="hash",
        selectedPlan="starter",
        subscriptionStatus="active",
        automaticCreditBalance=100.0,
        creditBalance=0.0,
        planCreditBalance=0.0,
        trialStartsAt=now,
        trialEndsAt=now + timedelta(days=7),
        createdAt=now,
        updatedAt=now,
    )
    project = Project(
        id=f"{prefix}-project",
        userId=user.id,
        name="URL Project",
        domain="url.example",
    )
    keyword = Keyword(
        id=f"{prefix}-keyword",
        projectId=project.id,
        userId=user.id,
        keyword="callback keyword",
        location="India",
        device="desktop",
        isActive=True,
    )
    db.add_all([user, project, keyword])
    db.commit()
    return user, project, keyword


def _provider_response(task_id: str = "fake-url-task"):
    return type("Response", (), {
        "headers": {"Content-Type": "application/json"},
        "json": lambda self: {
            "tasks": [{
                "id": task_id,
                "data": {"keyword": "callback keyword"},
            }],
        },
    })()


def test_canonical_url_with_secret_has_one_query_separator_and_one_secret():
    with patch.object(settings, "PINGBACK_URL", "https://callbacks.example"), patch.object(
        settings, "DATAFORSEO_WEBHOOK_SECRET", "abc-123"
    ):
        callback_url = _build_postback_url()

    assert callback_url == (
        "https://callbacks.example/api/webhooks/dataforseo"
        "?task_id=$id&secret=abc-123"
    )
    assert callback_url.count("?") == 1
    assert callback_url.count("secret=") == 1
    assert callback_url.count("$id") == 1
    assert parse_qs(urlsplit(callback_url).query) == {
        "task_id": ["$id"],
        "secret": ["abc-123"],
    }


def test_canonical_url_without_secret_has_no_secret_parameter():
    with patch.object(settings, "PINGBACK_URL", "https://callbacks.example/"), patch.object(
        settings, "DATAFORSEO_WEBHOOK_SECRET", None
    ):
        callback_url = _build_postback_url()

    assert callback_url == (
        "https://callbacks.example/api/webhooks/dataforseo?task_id=$id"
    )
    assert callback_url.count("?") == 1
    assert "secret=" not in callback_url
    assert callback_url.count("$id") == 1


def test_pingback_url_and_current_frontend_fallback_are_preserved():
    with patch.object(settings, "PINGBACK_URL", "https://ping.example/root/"), patch.object(
        settings, "FRONTEND_URL", "https://frontend.example"
    ), patch.object(settings, "DATAFORSEO_WEBHOOK_SECRET", None):
        assert _build_postback_url() == (
            "https://ping.example/root/api/webhooks/dataforseo?task_id=$id"
        )

    with patch.object(settings, "PINGBACK_URL", None), patch.object(
        settings, "FRONTEND_URL", "https://frontend.example/"
    ), patch.object(settings, "DATAFORSEO_WEBHOOK_SECRET", None):
        assert _build_postback_url() == (
            "https://frontend.example/api/webhooks/dataforseo?task_id=$id"
        )


def test_webhook_validation_accepts_canonical_generated_secret_semantics():
    with patch.object(settings, "PINGBACK_URL", "https://callbacks.example"), patch.object(
        settings, "DATAFORSEO_WEBHOOK_SECRET", "abc-123"
    ):
        callback_url = _build_postback_url().replace("$id", "fake-url-task")
        request = Request({
            "type": "http",
            "method": "POST",
            "headers": [(b"content-type", b"application/json")],
            "query_string": urlsplit(callback_url).query.encode("utf-8"),
        })
        request._body = json.dumps({
            "task_id": "fake-url-task",
            "tasks": [],
        }).encode("utf-8")

        result = asyncio.run(dataforseo_webhook(request))

    assert result == {
        "success": True,
        "message": "Task fake-url-task no tasks in payload",
    }


def test_active_weekly_submission_uses_canonical_helper_output_unchanged():
    db = _db()
    try:
        _, _, keyword = _weekly_rows(db, prefix="active")
        refresh = RefreshJob(
            id="active-refresh",
            jobType="weekly_serp",
            status="processing",
            batchIndex=0,
            totalBatches=1,
            keywordCount=1,
            keywordsJson=json.dumps([{
                "keyword": keyword.keyword,
                "location": "India",
            }]),
        )
        db.add(refresh)
        db.commit()
        canonical_url = (
            "https://callbacks.example/api/webhooks/dataforseo"
            "?task_id=$id&secret=abc-123"
        )

        with patch.object(settings, "DATAFORSEO_WEBHOOK_SECRET", "abc-123"), patch(
            "app.services.async_bulk_service._build_postback_url",
            return_value=canonical_url,
        ), patch(
            "app.services.dataforseo_client._get_cached_serp",
            return_value=None,
        ), patch(
            "app.services.async_bulk_service.requests.post",
            return_value=_provider_response("fake-active-task"),
        ) as provider_post:
            assert _submit_weekly_refresh(db, refresh, [keyword.keyword]) is True

        assert provider_post.call_args.kwargs["json"][0]["pingback_url"] == canonical_url
    finally:
        db.close()


def test_legacy_weekly_submission_uses_canonical_helper_output_unchanged():
    db = _db()
    try:
        user, project, keyword = _weekly_rows(db, prefix="legacy")
        task = AsyncTaskQueue(
            id="legacy-task",
            taskType="weekly_serp",
            status="pending",
            keywordsJson=json.dumps([{
                "keyword": keyword.keyword,
                "location": "India",
            }]),
            domain=project.domain,
            locationCode=2840,
            device="desktop",
            userId=user.id,
            projectId=project.id,
        )
        db.add(task)
        db.commit()
        canonical_url = (
            "https://callbacks.example/api/webhooks/dataforseo"
            "?task_id=$id&secret=abc-123"
        )

        with patch.object(settings, "DATAFORSEO_WEBHOOK_SECRET", "abc-123"), patch(
            "app.services.async_bulk_service._build_postback_url",
            return_value=canonical_url,
        ), patch(
            "app.services.dataforseo_client._get_cached_serp",
            return_value=None,
        ), patch(
            "app.services.async_bulk_service.requests.post",
            return_value=_provider_response("fake-legacy-provider-task"),
        ) as provider_post:
            assert submit_bulk_to_dataforseo(db, task) is True

        assert provider_post.call_args.kwargs["json"][0]["pingback_url"] == canonical_url
    finally:
        db.close()
