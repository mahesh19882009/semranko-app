"""Read-model regressions for keyword-table comparison and visibility data."""

from datetime import datetime, timedelta
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.db.models import (  # noqa: E402
    Base,
    Keyword,
    KeywordMetricsHistory,
    Project,
    RankResult,
    User,
)
from app.services.keyword_table_service import get_enriched_keywords  # noqa: E402


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _keyword(
    db,
    *,
    position=None,
    local_pack_position=None,
    visibility=None,
    volume=None,
    kd=None,
    cpc=None,
    competition=None,
    backlinks=None,
    referring_domains=None,
):
    user = User(id="owner", name="Owner", email="owner@example.com", passwordHash="hash")
    project = Project(id="project", userId=user.id, name="Project", domain="example.com")
    keyword = Keyword(
        id="keyword",
        projectId=project.id,
        userId=user.id,
        keyword="comparison keyword",
        position=position,
        localPackPosition=local_pack_position,
        visibility=visibility,
        volume=volume,
        kd=kd,
        cpc=cpc,
        competition=competition,
        backlinks=backlinks,
        referring_domains=referring_domains,
    )
    db.add_all([user, project, keyword])
    db.commit()
    return user, project, keyword


def _row(db, user, project):
    return get_enriched_keywords(db, user.id, project.id)[0]


def test_organic_position_is_preferred_for_current_and_previous_visibility(db):
    user, project, keyword = _keyword(
        db,
        position=3,
        local_pack_position=1,
        visibility=0.0,
    )
    checked_at = datetime(2026, 1, 1)
    db.add_all([
        RankResult(
            projectId=project.id,
            keywordId=keyword.id,
            keywordText=keyword.keyword,
            position=8,
            url="https://example.com/old",
            checkedAt=checked_at,
        ),
        RankResult(
            projectId=project.id,
            keywordId=keyword.id,
            keywordText=keyword.keyword,
            position=3,
            url="https://example.com/current",
            checkedAt=checked_at + timedelta(days=7),
        ),
    ])
    db.commit()

    row = _row(db, user, project)

    assert row["visibility"] == 0.8
    assert row["positionChange"] == {
        "previous": 8,
        "current": 3,
        "difference": -5.0,
        "direction": "up",
        "isPositive": True,
    }
    assert row["visibilityChange"] == {
        "previous": 0.3,
        "current": 0.8,
        "difference": 0.5,
        "direction": "up",
        "isPositive": True,
    }
    assert row["url"] == "https://example.com/current"
    assert row["rankCheckedAt"] == (checked_at + timedelta(days=7)).isoformat()


def test_local_pack_is_used_when_current_organic_position_is_missing(db):
    user, project, _ = _keyword(
        db,
        position=None,
        local_pack_position=2,
        visibility=0.0,
    )

    row = _row(db, user, project)

    assert row["visibility"] == 0.9


def test_visibility_is_zero_when_neither_current_rank_exists(db):
    user, project, _ = _keyword(
        db,
        position=None,
        local_pack_position=None,
        visibility=0.8,
    )

    row = _row(db, user, project)

    assert row["visibility"] == 0.0


def test_first_rank_result_has_no_comparison_but_retains_current_metadata(db):
    user, project, keyword = _keyword(db, position=7)
    checked_at = datetime(2026, 2, 1)
    db.add(
        RankResult(
            projectId=project.id,
            keywordId=keyword.id,
            keywordText=keyword.keyword,
            position=7,
            url="https://example.com/only-result",
            checkedAt=checked_at,
        )
    )
    db.commit()

    row = _row(db, user, project)

    assert row["positionChange"] is None
    assert row["visibilityChange"] is None
    assert row["url"] == "https://example.com/only-result"
    assert row["rankCheckedAt"] == checked_at.isoformat()


def test_kd_increase_uses_metrics_history_with_negative_semantics(db):
    user, project, keyword = _keyword(db, kd=34)
    db.add(
        KeywordMetricsHistory(
            keywordId=keyword.id,
            projectId=project.id,
            userId=user.id,
            kd=31,
            refreshedAt=datetime(2026, 1, 1),
        )
    )
    db.commit()

    row = _row(db, user, project)

    assert row["changes"]["kd"] == {
        "previous": 31,
        "current": 34,
        "difference": 3.0,
        "direction": "up",
        "isPositive": False,
    }


def test_kd_decrease_is_a_positive_semantic_change(db):
    user, project, keyword = _keyword(db, kd=28)
    db.add(
        KeywordMetricsHistory(
            keywordId=keyword.id,
            projectId=project.id,
            userId=user.id,
            kd=31,
            refreshedAt=datetime(2026, 1, 1),
        )
    )
    db.commit()

    assert _row(db, user, project)["changes"]["kd"]["isPositive"] is True


def test_position_zero_or_unchanged_history_has_no_comparison(db):
    user, project, keyword = _keyword(db, position=7)
    checked_at = datetime(2026, 1, 1)
    db.add_all([
        RankResult(
            projectId=project.id,
            keywordId=keyword.id,
            keywordText=keyword.keyword,
            position=0,
            checkedAt=checked_at,
        ),
        RankResult(
            projectId=project.id,
            keywordId=keyword.id,
            keywordText=keyword.keyword,
            position=7,
            checkedAt=checked_at + timedelta(days=7),
        ),
    ])
    db.commit()

    row = _row(db, user, project)
    assert row["positionChange"] is None
    assert row["visibilityChange"] is None

    db.query(RankResult).filter(RankResult.position == 0).update({"position": 7})
    db.commit()

    row = _row(db, user, project)
    assert row["positionChange"] is None
    assert row["visibilityChange"] is None


def test_metrics_without_history_have_no_comparisons(db):
    user, project, _ = _keyword(
        db,
        volume=880,
        kd=34,
        cpc=2.5,
        competition=0.65,
        backlinks=80,
        referring_domains=12,
    )

    assert _row(db, user, project)["changes"] == {}


def test_real_zero_cpc_and_competition_history_is_compared(db):
    user, project, keyword = _keyword(db, cpc=2.5, competition=0.65)
    db.add(
        KeywordMetricsHistory(
            keywordId=keyword.id,
            projectId=project.id,
            userId=user.id,
            cpc=0.0,
            competition=0.0,
            refreshedAt=datetime(2026, 1, 1),
        )
    )
    db.commit()

    changes = _row(db, user, project)["changes"]
    assert changes["cpc"]["previous"] == 0.0
    assert changes["cpc"]["difference"] == 2.5
    assert changes["competition"]["previous"] == 0.0
    assert changes["competition"]["difference"] == 0.65
