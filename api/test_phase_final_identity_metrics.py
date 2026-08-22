"""Focused regressions for final tracking identity and add-keyword metrics."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.db.models import Base, Keyword, ProcessingJob, Project, RefreshJob, User
from app.services.async_tracking_service import _enrich_keyword_metrics
from app.services.dataforseo_client import DataForSEOClient
from app.services.location_catalog import get_country_code_for_location
from app.services.serp_result_ingestion import ingest_dataforseo_task_result


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _task(task_id: str, keyword: str, location_code: int) -> dict:
    return {
        "id": task_id,
        "status_code": 20000,
        "data": {"keyword": keyword, "location_code": location_code},
        "result": [{"items": []}],
    }


def test_callback_keeps_exact_submission_deduplication_identity():
    db = _db()
    user = User(
        id="final-user", name="Final", email="final@example.com", passwordHash="hash",
        selectedPlan="starter", subscriptionStatus="active", creditBalance=100,
        planCreditBalance=100, purchasedCreditBalance=0, automaticCreditBalance=0,
    )
    project = Project(
        id="final-project", userId=user.id, name="Final", domain="example.com",
        location="India", locationCode=2356,
    )
    keyword = Keyword(
        id="faridabad-keyword", projectId=project.id, userId=user.id,
        keyword="same query", location="Faridabad, Haryana, India",
        locationCode=9061655, device="desktop", isActive=True,
    )
    refresh = RefreshJob(
        id="final-refresh", jobType="add_keyword", status="submitted",
        keywordCount=1, dataforseoRequestIds=json.dumps(["final-task"]),
    )
    original_key = "pending:final-refresh:faridabad-keyword:9061655:desktop"
    child = ProcessingJob(
        id="final-child", refreshJobId=refresh.id, keywordId=keyword.id,
        keywordText=keyword.keyword, location=keyword.location, status="pending",
        deduplicationKey=original_key,
        payload=json.dumps({
            "task_ids": ["final-task"], "location_code": 9061655,
            "location": keyword.location, "device": "desktop",
            "awaiting_callback": True,
        }),
    )
    db.add_all([user, project, keyword, refresh, child])
    db.commit()

    with patch("app.services.serp_result_ingestion.get_rank_check_queue"):
        result = ingest_dataforseo_task_result(
            db, "final-task", [_task("final-task", keyword.keyword, 9061655)], enqueue=False
        )

    db.refresh(child)
    assert result["updated"] == 1
    assert child.deduplicationKey == original_key
    assert json.loads(child.payload)["location_code"] == 9061655
    assert json.loads(child.payload)["keyword_id"] == keyword.id
    db.close()


def test_keyword_metrics_batch_preserves_explicit_city_location_code():
    response = MagicMock(status_code=200)
    response.text = "{}"
    response.json.return_value = {
        "tasks": [{
            "status_code": 20000,
            "result": [{
                "items": [{
                    "keyword": "same query",
                    "keyword_properties": {"keyword_difficulty": 12},
                    "keyword_info": {"search_volume": 100, "cpc": 1.2, "competition": 0.3},
                    "avg_backlinks_info": {"backlinks": 4, "referring_domains": 2},
                    "search_intent_info": {"main_intent": "commercial"},
                }],
            }],
        }],
    }

    with patch("app.services.dataforseo_client._get_cached_kw_metrics", return_value=None) as cache_get, \
         patch("app.services.dataforseo_client._set_cached_kw_metrics"), \
         patch("app.services.dataforseo_client.requests.post", return_value=response) as post:
        result = DataForSEOClient._fetch_keyword_data_batch(
            ["Same Query"], "India", location_code=9061655
        )

    payload = post.call_args.kwargs["json"]
    assert payload[0]["location_code"] == 2356
    assert cache_get.call_args.args[0].endswith(":2356:en")
    assert result["Same Query"]["volume"] == 100


@pytest.mark.parametrize(
    ("tracking_code", "country_code"),
    [
        (2356, 2356),
        (9061655, 2356),
        (9062115, 2356),
        (1007809, 2356),
        (2036, 2036),
        (1000256, 2036),
        (1000142, 2036),
        (1000109, 2036),
        (2840, 2840),
        (1013962, 2840),
        (1023191, 2840),
        (1026480, 2840),
    ],
)
def test_tracking_location_resolves_to_root_country_for_labs(tracking_code, country_code):
    assert get_country_code_for_location(tracking_code) == country_code


def test_add_keyword_metrics_enrichment_updates_city_target_without_provider_call():
    db = _db()
    user = User(
        id="metrics-user", name="Metrics", email="metrics@example.com", passwordHash="hash",
        selectedPlan="starter", subscriptionStatus="active", creditBalance=100,
        planCreditBalance=100, purchasedCreditBalance=0, automaticCreditBalance=0,
    )
    project = Project(
        id="metrics-project", userId=user.id, name="Metrics", domain="example.com",
        location="Faridabad, Haryana, India", locationCode=9061655,
    )
    keyword = Keyword(
        id="metrics-keyword", projectId=project.id, userId=user.id,
        keyword="Same Query", location="Faridabad, Haryana, India",
        locationCode=9061655, device="desktop", isActive=True,
    )
    india_keyword = Keyword(
        id="metrics-india-keyword", projectId=project.id, userId=user.id,
        keyword="Same Query", location="India", locationCode=2356,
        device="desktop", isActive=True,
    )
    db.add_all([user, project, keyword, india_keyword])
    db.commit()

    metrics = {
        "volume": 100, "difficulty": 12, "cpc": 1.2,
        "competition": 0.3, "backlinks": 4,
        "referring_domains": 2, "intent": "commercial",
    }
    with patch(
        "app.services.async_tracking_service.DataForSEOClient._fetch_keyword_data_batch",
        return_value={"same query": metrics},
    ) as fetch:
        summary = _enrich_keyword_metrics(
            db, user.id, project.id, ["same query"], 9061655
        )

    db.refresh(keyword)
    db.refresh(india_keyword)
    assert summary == {"requested": 1, "updated": 1, "missing": 0}
    assert keyword.volume == 100 and keyword.kd == 12
    assert keyword.locationCode == 9061655
    assert india_keyword.volume is None
    assert fetch.call_args.kwargs["location_code"] == 9061655
    db.close()
