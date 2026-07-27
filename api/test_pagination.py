import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, "/Users/maheshsharma/development/rankcare-api/api/fastapi_app")

from app.db.models import Base, User, Project, Keyword, RankResult, Backlink
from app.services.keyword_service import get_project_keywords
from app.services.ranking_service import get_project_rankings
from app.services.backlink_service import get_project_backlinks


def make_user(db: Session, user_id="user-1"):
    user = User(
        id=user_id,
        name="Test User",
        email="test@example.com",
        passwordHash="hash",
        selectedPlan="pro",
        creditBalance=0.0,
        subscriptionStatus="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_project(db: Session, user_id="user-1", project_id="proj-1"):
    project = Project(id=project_id, name="Test Project", domain="test.com", userId=user_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


class TestKeywordList:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_returns_all_keywords(self):
        user = make_user(self.db)
        project = make_project(self.db, user_id=user.id, project_id="proj-1")
        for i in range(5):
            kw = Keyword(projectId=project.id, keyword=f"keyword{i}", device="desktop")
            self.db.add(kw)
        self.db.commit()

        result = get_project_keywords(self.db, user.id, project.id)
        assert isinstance(result, list)
        assert len(result) == 5

    def test_empty_results(self):
        user = make_user(self.db, user_id="user-3")
        project = make_project(self.db, user_id=user.id, project_id="proj-3")

        result = get_project_keywords(self.db, user.id, project.id)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_project_not_found(self):
        user = make_user(self.db, user_id="user-4")
        with pytest.raises(Exception) as exc_info:
            get_project_keywords(self.db, user.id, "missing-project")
        assert "Project not found" in str(exc_info.value)


class TestRankingList:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_returns_all_rankings(self):
        user = make_user(self.db, user_id="user-10")
        project = make_project(self.db, user_id=user.id, project_id="proj-10")
        keyword = Keyword(projectId=project.id, keyword="test", device="desktop")
        self.db.add(keyword)
        self.db.commit()
        self.db.refresh(keyword)

        for i in range(5):
            rr = RankResult(
                projectId=project.id,
                keywordId=keyword.id,
                keywordText="test",
                position=i + 1,
                checkedAt=datetime.utcnow() - timedelta(minutes=i),
            )
            self.db.add(rr)
        self.db.commit()

        result = get_project_rankings(self.db, user.id, project.id)
        assert isinstance(result, list)
        assert len(result) == 5

    def test_empty_results(self):
        user = make_user(self.db, user_id="user-12")
        project = make_project(self.db, user_id=user.id, project_id="proj-12")

        result = get_project_rankings(self.db, user.id, project.id)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_project_not_found(self):
        user = make_user(self.db, user_id="user-13")
        with pytest.raises(Exception) as exc_info:
            get_project_rankings(self.db, user.id, "missing-project")
        assert "Project not found" in str(exc_info.value)


class TestBacklinkList:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_returns_all_backlinks(self):
        user = make_user(self.db, user_id="user-20")
        project = make_project(self.db, user_id=user.id, project_id="proj-20")
        for i in range(5):
            bl = Backlink(
                projectId=project.id,
                sourceUrl=f"https://example{i}.com",
                sourceDomain=f"example{i}.com",
                domainRank=50 + i,
            )
            self.db.add(bl)
        self.db.commit()

        result = get_project_backlinks(self.db, user.id, project.id)
        assert "backlinks" in result
        assert len(result["backlinks"]) == 5

    def test_empty_results(self):
        user = make_user(self.db, user_id="user-22")
        project = make_project(self.db, user_id=user.id, project_id="proj-22")

        result = get_project_backlinks(self.db, user.id, project.id)
        assert len(result["backlinks"]) == 0

    def test_project_not_found(self):
        user = make_user(self.db, user_id="user-23")
        with pytest.raises(Exception) as exc_info:
            get_project_backlinks(self.db, user.id, "missing-project")
        assert "Project not found" in str(exc_info.value)
