"""Tenant-authorization regressions for the enriched keyword table."""

from datetime import datetime
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.api.routes.keywords import get_keyword_table
from app.core.errors import ApiError
from app.db.models import (
    Base,
    Keyword,
    KeywordMetricsHistory,
    Project,
    RankResult,
    User,
)
from app.services.keyword_table_service import get_enriched_keywords


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


def _user(db: Session, user_id: str) -> User:
    user = User(
        id=user_id,
        name=user_id,
        email=f"{user_id}@example.com",
        passwordHash="hash",
    )
    db.add(user)
    db.commit()
    return user


def _project(db: Session, user_id: str, project_id: str) -> Project:
    project = Project(
        id=project_id,
        userId=user_id,
        name=project_id,
        domain="example.com",
        location="India",
        locationCode=2840,
    )
    db.add(project)
    db.commit()
    return project


def _keyword(
    db: Session,
    project_id: str,
    user_id: str,
    keyword_id: str,
    *,
    active: bool = True,
    deleted: bool = False,
) -> Keyword:
    keyword = Keyword(
        id=keyword_id,
        projectId=project_id,
        userId=user_id,
        keyword=keyword_id,
        location="India",
        device="desktop",
        volume=100,
        kd=20,
        cpc=1.5,
        competition=0.4,
        backlinks=12,
        referring_domains=5,
        intent="commercial",
        position=3,
        check_url=f"https://example.com/{keyword_id}",
        isActive=active,
        deletedAt=datetime.utcnow() if deleted else None,
    )
    db.add(keyword)
    db.commit()
    return keyword


def _assert_project_not_found(db: Session, user_id: str, project_id: str) -> None:
    with pytest.raises(ApiError) as error:
        get_keyword_table(project_id, {"userId": user_id}, db)
    assert error.value.status_code == 404
    assert error.value.message == "Project not found"


def test_owner_receives_existing_response_contract_and_enrichment(db):
    owner = _user(db, "owner")
    project = _project(db, owner.id, "owner-project")
    keyword = _keyword(db, project.id, owner.id, "owner-keyword")
    db.add(
        RankResult(
            projectId=project.id,
            keywordId=keyword.id,
            keywordText=keyword.keyword,
            position=3,
            url="https://example.com/private-ranking-url",
        )
    )
    db.add(
        KeywordMetricsHistory(
            projectId=project.id,
            keywordId=keyword.id,
            userId=owner.id,
            volume=90,
            kd=19,
            cpc=1.0,
            competition=0.3,
            backlinks=10,
            referring_domains=4,
            intent="commercial",
        )
    )
    db.commit()

    response = get_keyword_table(project.id, {"userId": owner.id}, db)

    assert set(response) == {"success", "data"}
    assert response["success"] is True
    assert set(response["data"]) == {"rows"}
    assert len(response["data"]["rows"]) == 1
    row = response["data"]["rows"][0]
    assert row["keyword"] == keyword.keyword
    assert row["url"] == "https://example.com/private-ranking-url"
    assert row["changes"]["volume"]["previous"] == 90


def test_non_owner_cannot_read_project_keyword_table_or_child_data(db):
    owner = _user(db, "owner")
    intruder = _user(db, "intruder")
    project = _project(db, owner.id, "private-project")
    keyword = _keyword(db, project.id, owner.id, "private-keyword")
    db.add(
        RankResult(
            projectId=project.id,
            keywordId=keyword.id,
            keywordText=keyword.keyword,
            position=1,
            url="https://secret.example/ranking",
        )
    )
    db.add(
        KeywordMetricsHistory(
            projectId=project.id,
            keywordId=keyword.id,
            userId=owner.id,
            volume=999,
        )
    )
    db.commit()

    _assert_project_not_found(db, intruder.id, project.id)


def test_unknown_project_is_rejected(db):
    owner = _user(db, "owner")
    _assert_project_not_found(db, owner.id, "missing-project")


def test_keyword_user_constraint_is_defense_in_depth(db):
    owner = _user(db, "owner")
    other = _user(db, "other")
    project = _project(db, owner.id, "owner-project")
    own_keyword = _keyword(db, project.id, owner.id, "own-keyword")
    _keyword(db, project.id, other.id, "inconsistent-foreign-keyword")

    rows = get_enriched_keywords(db, owner.id, project.id)

    assert [row["id"] for row in rows] == [own_keyword.id]


def test_inactive_and_deleted_rows_keep_existing_visibility(db):
    owner = _user(db, "owner")
    project = _project(db, owner.id, "owner-project")
    inactive = _keyword(
        db, project.id, owner.id, "inactive-keyword", active=False
    )
    deleted = _keyword(
        db,
        project.id,
        owner.id,
        "deleted-keyword",
        active=False,
        deleted=True,
    )

    rows = get_enriched_keywords(db, owner.id, project.id)
    rows_by_id = {row["id"]: row for row in rows}

    assert set(rows_by_id) == {inactive.id, deleted.id}
    assert rows_by_id[inactive.id]["is_active"] is False
    assert rows_by_id[inactive.id]["deletedAt"] is None
    assert rows_by_id[deleted.id]["is_active"] is False
    assert rows_by_id[deleted.id]["deletedAt"] is not None


def test_enriched_table_query_count_is_bounded(db):
    owner = _user(db, "owner")
    project = _project(db, owner.id, "owner-project")
    for index in range(30):
        _keyword(db, project.id, owner.id, f"keyword-{index}")

    query_count = 0

    def count_query(*_args, **_kwargs):
        nonlocal query_count
        query_count += 1

    event.listen(db.bind, "before_cursor_execute", count_query)
    try:
        rows = get_enriched_keywords(db, "owner", "owner-project")
    finally:
        event.remove(db.bind, "before_cursor_execute", count_query)

    assert len(rows) == 30
    assert query_count == 4
