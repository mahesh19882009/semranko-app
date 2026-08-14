"""Focused account aggregate coverage for protected-app Phase B."""

import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.db.models import Base, Keyword, Project, User
from app.services.dashboard_service import get_dashboard_overview
from app.services.project_service import get_projects


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _user(db):
    user = User(
        id="phase-b-user", name="Phase B", email="phase-b@example.com", passwordHash="hash",
        selectedPlan="free_trial", subscriptionStatus="free", creditBalance=100,
    )
    db.add(user)
    db.commit()
    return user


def test_projects_include_grouped_non_deleted_keyword_counts():
    db = _db()
    user = _user(db)
    first = Project(id="phase-b-project-1", userId=user.id, name="First", domain="first.example")
    second = Project(id="phase-b-project-2", userId=user.id, name="Second", domain="second.example")
    db.add_all([first, second])
    db.add_all([
        Keyword(projectId=first.id, userId=user.id, keyword="active", isActive=True),
        Keyword(projectId=first.id, userId=user.id, keyword="inactive", isActive=False),
        Keyword(projectId=first.id, userId=user.id, keyword="deleted", deletedAt=datetime.now(timezone.utc)),
    ])
    db.commit()

    projects = {project["id"]: project for project in get_projects(db, user.id)}
    assert projects[first.id]["keywordCount"] == 2
    assert projects[second.id]["keywordCount"] == 0


def test_dashboard_overview_is_account_wide_and_excludes_deleted_keywords():
    db = _db()
    user = _user(db)
    project = Project(id="phase-b-dashboard", userId=user.id, name="Dashboard", domain="dashboard.example")
    db.add(project)
    db.add_all([
        Keyword(projectId=project.id, userId=user.id, keyword="active", isActive=True, ai_badge="AIO"),
        Keyword(projectId=project.id, userId=user.id, keyword="inactive", isActive=False),
        Keyword(projectId=project.id, userId=user.id, keyword="deleted", deletedAt=datetime.now(timezone.utc)),
    ])
    db.commit()

    overview = get_dashboard_overview(db, user.id)
    assert overview["projects_count"] == 1
    assert overview["tracked_keywords_count"] == 2
    assert overview["active_keywords_count"] == 1
    assert overview["inactive_keywords_count"] == 1
    assert overview["aio_keywords_count"] == 1


def test_dashboard_empty_keyword_account_keeps_real_project_count():
    db = _db()
    user = _user(db)
    db.add(Project(id="phase-b-empty", userId=user.id, name="Empty", domain="empty.example"))
    db.commit()

    overview = get_dashboard_overview(db, user.id)
    assert overview["projects_count"] == 1
    assert overview["tracked_keywords_count"] == 0
